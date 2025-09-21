"""ADB Manager for Android TV Box Integration."""
import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from adb_shell.adb_device import AdbDeviceTcp
    from adb_shell.exceptions import TcpTimeoutException
except ImportError as e:
    raise ImportError(
        "Missing required dependency 'adb-shell'. "
        "Please install it with: pip install adb-shell>=0.4.4"
    ) from e

from .const import (
    ADB_COMMANDS,
    ADB_TIMEOUT,
    COMMAND_CACHE_TTL,
    ERROR_CANNOT_CONNECT,
    ERROR_TIMEOUT,
    ERROR_UNKNOWN,
    IMMEDIATE_FEEDBACK_TIMINGS,
    ISG_COMMANDS,
    ISG_CONTROL_COMMANDS,
    ISG_HEALTH_CRASHED,
    ISG_HEALTH_HEALTHY,
    ISG_HEALTH_NOT_RUNNING,
    ISG_HEALTH_UNHEALTHY,
    ISG_HEALTH_UNKNOWN,
    ISG_PACKAGE_NAME,
    MAX_CONCURRENT_COMMANDS,
    MAX_ISG_RESTART_ATTEMPTS,
    MEDIA_STATE_IDLE,
    MEDIA_STATE_PAUSED,
    MEDIA_STATE_PLAYING,
    SET_COMMANDS,
    STATE_COMMANDS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ADBCommandResult:
    """Result of an ADB command execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None


@dataclass
class CommandCache:
    """Cache for ADB commands."""
    cache: Dict[str, Tuple[ADBCommandResult, float]] = field(default_factory=dict)
    pending: Dict[str, asyncio.Task] = field(default_factory=dict)
    
    def get_cache_key(self, device_id: str, command: str) -> str:
        """Generate cache key."""
        return f"{device_id}_{hash(command)}"
    
    def is_cached(self, cache_key: str) -> bool:
        """Check if command result is cached and valid."""
        if cache_key not in self.cache:
            return False
        
        result, timestamp = self.cache[cache_key]
        return time.time() - timestamp < COMMAND_CACHE_TTL
    
    def get_cached(self, cache_key: str) -> Optional[ADBCommandResult]:
        """Get cached result."""
        if self.is_cached(cache_key):
            result, _ = self.cache[cache_key]
            return result
        return None
    
    def set_cached(self, cache_key: str, result: ADBCommandResult) -> None:
        """Cache command result."""
        self.cache[cache_key] = (result, time.time())
    
    def cleanup_old_entries(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= COMMAND_CACHE_TTL
        ]
        for key in expired_keys:
            del self.cache[key]


class ADBManagerInterface(ABC):
    """Interface for ADB manager implementations."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the device."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the device."""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to device."""
        pass
    
    @abstractmethod
    async def execute_command(self, command: str) -> ADBCommandResult:
        """Execute ADB command."""
        pass


class ADBManager(ADBManagerInterface):
    """Manages ADB connection and commands for Android TV Box."""
    
    def __init__(self, host: str, port: int):
        """Initialize ADB manager."""
        self.host = host
        self.port = port
        self.device_id = f"{host}:{port}"
        self._device: Optional[AdbDeviceTcp] = None
        self._connected = False
        self._command_semaphore = asyncio.Semaphore(MAX_CONCURRENT_COMMANDS)
        self._cache = CommandCache()
        self._logger = _LOGGER.getChild(f"{host}_{port}")
        
    async def connect(self) -> bool:
        """Connect to Android TV device via ADB."""
        try:
            # Connect using adb-shell
            self._device = AdbDeviceTcp(self.host, self.port)
            await asyncio.wait_for(self._device.connect(rsa_keys=None, auth_timeout_s=ADB_TIMEOUT), timeout=ADB_TIMEOUT)
            
            # Test connection with simple command
            result = await self._execute_with_device("shell echo test")
            if result.success and "test" in result.stdout:
                self._connected = True
                self._logger.info("Connected to %s:%s via adb-shell", self.host, self.port)
                return True
                
        except Exception as e:
            self._logger.error("Failed to connect to %s:%s: %s", self.host, self.port, e)
            
        self._connected = False
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from device."""
        try:
            if self._device:
                await self._device.close()
                self._device = None
        except Exception as e:
            self._logger.debug("Error during disconnect: %s", e)
        finally:
            self._connected = False
            
    async def is_connected(self) -> bool:
        """Check if connected to device."""
        if not self._connected:
            return False
            
        try:
            # Quick connectivity test
            result = await asyncio.wait_for(
                self.execute_command("shell echo ping"),
                timeout=5
            )
            return result.success and "ping" in result.stdout
        except Exception:
            self._connected = False
            return False
    
    async def execute_command(self, command: str, use_cache: bool = True) -> ADBCommandResult:
        """Execute ADB command with caching and concurrency control."""
        full_command = f"-s {self.device_id} {command}"
        cache_key = self._cache.get_cache_key(self.device_id, full_command)
        
        # Check cache first
        if use_cache:
            cached_result = self._cache.get_cached(cache_key)
            if cached_result:
                return cached_result
        
        # Check if same command is already running
        if cache_key in self._cache.pending:
            try:
                return await self._cache.pending[cache_key]
            except Exception:
                pass
        
        # Execute command with resource limits
        async with self._command_semaphore:
            task = asyncio.create_task(self._execute_command_internal(full_command))
            if use_cache:
                self._cache.pending[cache_key] = task
            
            try:
                result = await task
                if use_cache and result.success:
                    self._cache.set_cached(cache_key, result)
                return result
            finally:
                if cache_key in self._cache.pending:
                    del self._cache.pending[cache_key]
    
    async def _execute_command_internal(self, command: str) -> ADBCommandResult:
        """Internal command execution."""
        if not self._connected:
            return ADBCommandResult(
                success=False,
                error=ERROR_CANNOT_CONNECT
            )
        
        try:
            if self._device:
                return await self._execute_with_device(command)
            else:
                return ADBCommandResult(
                    success=False,
                    error=ERROR_CANNOT_CONNECT
                )
        except asyncio.TimeoutError:
            self._logger.warning("Command timeout: %s", command)
            return ADBCommandResult(
                success=False,
                error=ERROR_TIMEOUT
            )
        except Exception as e:
            self._logger.error("Command execution failed: %s - %s", command, e)
            return ADBCommandResult(
                success=False,
                error=str(e)
            )
    
    async def _execute_with_device(self, command: str) -> ADBCommandResult:
        """Execute command using adb-shell."""
        try:
            result = await asyncio.wait_for(
                self._device.shell(command),
                timeout=ADB_TIMEOUT
            )
            # adb-shell returns a string, not a tuple
            if isinstance(result, str):
                return ADBCommandResult(
                    success=True,
                    stdout=result.strip() if result else "",
                    stderr=""
                )
            else:
                # Handle case where it might return a tuple
                stdout, stderr = result
                return ADBCommandResult(
                    success=True,
                    stdout=stdout.strip() if stdout else "",
                    stderr=stderr.strip() if stderr else ""
                )
        except Exception as e:
            return ADBCommandResult(
                success=False,
                error=str(e)
            )
    
    
    # Media control methods
    async def media_play(self) -> bool:
        """Send play command."""
        result = await self.execute_command(ADB_COMMANDS["media_play"], use_cache=False)
        return result.success
    
    async def media_pause(self) -> bool:
        """Send pause command."""
        result = await self.execute_command(ADB_COMMANDS["media_pause"], use_cache=False)
        return result.success
    
    async def media_stop(self) -> bool:
        """Send stop command."""
        result = await self.execute_command(ADB_COMMANDS["media_stop"], use_cache=False)
        return result.success
    
    async def media_play_pause(self) -> bool:
        """Toggle play/pause."""
        result = await self.execute_command(ADB_COMMANDS["media_play_pause"], use_cache=False)
        return result.success
    
    async def media_next(self) -> bool:
        """Next track."""
        result = await self.execute_command(ADB_COMMANDS["media_next"], use_cache=False)
        return result.success
    
    async def media_previous(self) -> bool:
        """Previous track."""
        result = await self.execute_command(ADB_COMMANDS["media_previous"], use_cache=False)
        return result.success
    
    async def get_media_state(self) -> str:
        """Get current media playback state."""
        result = await self.execute_command(STATE_COMMANDS["media_state"])
        if result.success and result.stdout:
            state = result.stdout.strip().upper()
            if "PLAYING" in state:
                return MEDIA_STATE_PLAYING
            elif "PAUSED" in state:
                return MEDIA_STATE_PAUSED
            elif "STOPPED" in state:
                return MEDIA_STATE_IDLE
        return MEDIA_STATE_IDLE
    
    # Volume control methods
    async def volume_up(self) -> bool:
        """Increase volume."""
        result = await self.execute_command(ADB_COMMANDS["volume_up"], use_cache=False)
        return result.success
    
    async def volume_down(self) -> bool:
        """Decrease volume."""
        result = await self.execute_command(ADB_COMMANDS["volume_down"], use_cache=False)
        return result.success
    
    async def volume_mute(self) -> bool:
        """Toggle mute."""
        result = await self.execute_command(ADB_COMMANDS["volume_mute"], use_cache=False)
        return result.success
    
    async def set_volume(self, level: int) -> bool:
        """Set volume to specific level."""
        command = SET_COMMANDS["set_volume"].format(level=level)
        result = await self.execute_command(command, use_cache=False)
        return result.success
    
    async def get_volume_state(self) -> Tuple[int, int, bool]:
        """Get volume state (current, max, is_muted)."""
        result = await self.execute_command(STATE_COMMANDS["volume_level"])
        if result.success and result.stdout:
            # Parse: "volume is 8 in range [0..15]"
            match = re.search(r"volume is (\d+) in range \[(\d+)\.\.(\d+)\]", result.stdout)
            if match:
                current = int(match.group(1))
                min_vol = int(match.group(2))
                max_vol = int(match.group(3))
                is_muted = current == min_vol
                return current, max_vol, is_muted
        return 0, 15, False
    
    # Power control methods
    async def power_on(self) -> bool:
        """Wake up device."""
        result = await self.execute_command(ADB_COMMANDS["power_on"], use_cache=False)
        return result.success
    
    async def power_off(self) -> bool:
        """Put device to sleep."""
        result = await self.execute_command(ADB_COMMANDS["power_off"], use_cache=False)
        return result.success
    
    async def get_power_state(self) -> Tuple[str, bool]:
        """Get power state (wakefulness, screen_on)."""
        result = await self.execute_command(STATE_COMMANDS["power_state"])
        if result.success and result.stdout:
            wakefulness = "Unknown"
            screen_on = False
            
            for line in result.stdout.split('\n'):
                if "mWakefulness=" in line:
                    if "Awake" in line:
                        wakefulness = "Awake"
                    elif "Asleep" in line:
                        wakefulness = "Asleep"
                    elif "Dreaming" in line:
                        wakefulness = "Dreaming"
                elif "mScreenOn=" in line:
                    screen_on = "true" in line
            
            return wakefulness, screen_on
        return "Unknown", False
    
    # Navigation methods
    async def nav_up(self) -> bool:
        """Navigate up."""
        result = await self.execute_command(ADB_COMMANDS["nav_up"], use_cache=False)
        return result.success
    
    async def nav_down(self) -> bool:
        """Navigate down."""
        result = await self.execute_command(ADB_COMMANDS["nav_down"], use_cache=False)
        return result.success
    
    async def nav_left(self) -> bool:
        """Navigate left."""
        result = await self.execute_command(ADB_COMMANDS["nav_left"], use_cache=False)
        return result.success
    
    async def nav_right(self) -> bool:
        """Navigate right."""
        result = await self.execute_command(ADB_COMMANDS["nav_right"], use_cache=False)
        return result.success
    
    async def nav_center(self) -> bool:
        """Navigate center/OK."""
        result = await self.execute_command(ADB_COMMANDS["nav_center"], use_cache=False)
        return result.success
    
    async def nav_back(self) -> bool:
        """Navigate back."""
        result = await self.execute_command(ADB_COMMANDS["nav_back"], use_cache=False)
        return result.success
    
    async def nav_home(self) -> bool:
        """Navigate home."""
        result = await self.execute_command(ADB_COMMANDS["nav_home"], use_cache=False)
        return result.success
    
    async def nav_menu(self) -> bool:
        """Navigate menu."""
        result = await self.execute_command(ADB_COMMANDS["nav_menu"], use_cache=False)
        return result.success
    
    # WiFi methods
    async def get_wifi_state(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """Get WiFi state (enabled, SSID, IP)."""
        # Get WiFi enabled state
        result = await self.execute_command(STATE_COMMANDS["wifi_state"])
        wifi_enabled = result.success and result.stdout.strip() == "1"
        
        ssid = None
        ip_address = None
        
        if wifi_enabled:
            # Get SSID
            result = await self.execute_command(STATE_COMMANDS["wifi_ssid"])
            if result.success and result.stdout:
                ssid_match = re.search(r'SSID:\s*"([^"]+)"', result.stdout)
                if ssid_match:
                    ssid = ssid_match.group(1)
            
            # Get IP address
            result = await self.execute_command(STATE_COMMANDS["ip_address"])
            if result.success and result.stdout:
                ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if ip_match:
                    ip_address = ip_match.group(1)
        
        return wifi_enabled, ssid, ip_address
    
    # App control methods
    async def start_app(self, package_name: str) -> bool:
        """Start application."""
        command = SET_COMMANDS["start_app"].format(package=package_name)
        result = await self.execute_command(command, use_cache=False)
        return result.success
    
    async def get_current_activity(self) -> Optional[str]:
        """Get current foreground activity."""
        result = await self.execute_command(STATE_COMMANDS["current_activity"])
        if result.success and result.stdout:
            # Parse activity info
            match = re.search(r'ACTIVITY ([^\s]+)', result.stdout)
            if match:
                return match.group(1)
        return None
    
    async def get_installed_apps(self) -> List[str]:
        """Get list of installed third-party apps."""
        result = await self.execute_command(STATE_COMMANDS["installed_apps"])
        if result.success and result.stdout:
            apps = []
            for line in result.stdout.split('\n'):
                if line.startswith('package:'):
                    package = line.replace('package:', '').strip()
                    apps.append(package)
            return apps
        return []
    
    # Brightness control
    async def set_brightness(self, level: int) -> bool:
        """Set screen brightness (0-255)."""
        command = SET_COMMANDS["set_brightness"].format(level=level)
        result = await self.execute_command(command, use_cache=False)
        return result.success
    
    async def get_brightness(self) -> Optional[int]:
        """Get current brightness level."""
        result = await self.execute_command(STATE_COMMANDS["brightness"])
        if result.success and result.stdout:
            try:
                return int(result.stdout.strip())
            except ValueError:
                pass
        return None
    
    # Screenshot methods
    async def take_screenshot(self, path: str) -> bool:
        """Take screenshot and save to device path."""
        command = STATE_COMMANDS["screenshot"].format(path=path)
        result = await self.execute_command(command, use_cache=False)
        return result.success
    
    async def get_screenshot_data(self, path: str) -> Optional[bytes]:
        """Get screenshot data from device."""
        # First take screenshot
        if not await self.take_screenshot(path):
            return None
        
        # Pull screenshot data using shell command since pull might not be available
        try:
            if self._device:
                # Use base64 encoding to transfer binary data through shell
                command = f"shell base64 {path}"
                result = await self._execute_with_device(command)
                if result.success and result.stdout:
                    import base64
                    return base64.b64decode(result.stdout.strip())
            return None
        except Exception as e:
            self._logger.error("Failed to get screenshot data: %s", e)
            return None
    
    # Cast methods
    async def cast_media_url(self, url: str) -> bool:
        """Cast media URL."""
        command = SET_COMMANDS["cast_media"].format(url=url)
        result = await self.execute_command(command, use_cache=False)
        return result.success
    
    async def cast_youtube_video(self, video_id: str) -> bool:
        """Cast YouTube video."""
        command = SET_COMMANDS["cast_youtube"].format(video_id=video_id)
        result = await self.execute_command(command, use_cache=False)
        return result.success
    
    async def cast_netflix_video(self, video_id: str) -> bool:
        """Cast Netflix video."""
        command = SET_COMMANDS["cast_netflix"].format(video_id=video_id)
        result = await self.execute_command(command, use_cache=False)
        return result.success
    
    async def cast_spotify_track(self, track_id: str) -> bool:
        """Cast Spotify track."""
        command = SET_COMMANDS["cast_spotify"].format(track_id=track_id)
        result = await self.execute_command(command, use_cache=False)
        return result.success
    
    # ISG monitoring methods
    async def check_isg_process_status(self) -> bool:
        """Check if ISG process is running."""
        result = await self.execute_command(ISG_COMMANDS["process_status"])
        return result.success and ISG_PACKAGE_NAME in result.stdout
    
    async def get_isg_memory_usage(self) -> Tuple[Optional[float], Optional[float]]:
        """Get ISG memory usage (MB, percentage)."""
        result = await self.execute_command(ISG_COMMANDS["memory_usage"])
        if result.success and result.stdout:
            # Parse memory info
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line:
                    match = re.search(r'(\d+)', line)
                    if match:
                        memory_kb = int(match.group(1))
                        memory_mb = memory_kb / 1024
                        # Rough percentage calculation (assuming 1GB total memory)
                        memory_pct = (memory_mb / 1024) * 100
                        return memory_mb, memory_pct
        return None, None
    
    async def get_isg_cpu_usage(self) -> Optional[float]:
        """Get ISG CPU usage percentage."""
        result = await self.execute_command(ISG_COMMANDS["cpu_usage"])
        if result.success and result.stdout:
            # Parse top output for CPU usage
            match = re.search(r'(\d+\.?\d*)%', result.stdout)
            if match:
                return float(match.group(1))
        return None
    
    async def force_start_isg(self) -> bool:
        """Force start ISG application."""
        result = await self.execute_command(ISG_CONTROL_COMMANDS["force_start"], use_cache=False)
        return result.success
    
    async def force_stop_isg(self) -> bool:
        """Force stop ISG application."""
        result = await self.execute_command(ISG_CONTROL_COMMANDS["force_stop"], use_cache=False)
        return result.success
    
    async def restart_isg(self) -> bool:
        """Restart ISG application."""
        result = await self.execute_command(ISG_CONTROL_COMMANDS["restart"], use_cache=False)
        return result.success
    
    async def clear_isg_cache(self) -> bool:
        """Clear ISG application cache."""
        result = await self.execute_command(ISG_CONTROL_COMMANDS["clear_cache"], use_cache=False)
        return result.success
    
    async def get_isg_logs(self, lines: int = 50) -> List[str]:
        """Get ISG application logs."""
        result = await self.execute_command(ISG_COMMANDS["app_logs"])
        if result.success and result.stdout:
            return result.stdout.split('\n')[:lines]
        return []
    
    async def get_isg_crash_logs(self) -> List[str]:
        """Get ISG crash logs."""
        result = await self.execute_command(ISG_COMMANDS["crash_logs"])
        if result.success and result.stdout:
            return result.stdout.split('\n')
        return []
    
    async def perform_isg_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive ISG health check."""
        health_data = {
            "health_status": ISG_HEALTH_UNKNOWN,
            "is_running": False,
            "memory_usage": 0.0,
            "cpu_usage": 0.0,
            "crash_detected": False,
            "anr_detected": False,
            "last_check": datetime.now(),
        }
        
        # Check if process is running
        is_running = await self.check_isg_process_status()
        health_data["is_running"] = is_running
        
        if not is_running:
            health_data["health_status"] = ISG_HEALTH_NOT_RUNNING
            return health_data
        
        # Get performance metrics
        memory_mb, memory_pct = await self.get_isg_memory_usage()
        if memory_mb:
            health_data["memory_usage"] = memory_mb
        
        cpu_usage = await self.get_isg_cpu_usage()
        if cpu_usage:
            health_data["cpu_usage"] = cpu_usage
        
        # Check for crashes
        crash_logs = await self.get_isg_crash_logs()
        health_data["crash_detected"] = len(crash_logs) > 0
        
        # Determine health status
        if health_data["crash_detected"]:
            health_data["health_status"] = ISG_HEALTH_CRASHED
        elif (memory_pct and memory_pct > 80) or (cpu_usage and cpu_usage > 90):
            health_data["health_status"] = ISG_HEALTH_UNHEALTHY
        else:
            health_data["health_status"] = ISG_HEALTH_HEALTHY
        
        return health_data
    
    # Device info methods
    async def get_device_info(self) -> Dict[str, Any]:
        """Get device information."""
        result = await self.execute_command(STATE_COMMANDS["device_info"])
        device_info = {}
        
        if result.success and result.stdout:
            for line in result.stdout.split('\n'):
                if '=' in line and line.startswith('['):
                    key_value = line.strip('[]').split('=', 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        key = key.strip()
                        value = value.strip()
                        device_info[key] = value
        
        return {
            "model": device_info.get("ro.product.model", "Unknown"),
            "manufacturer": device_info.get("ro.product.manufacturer", "Unknown"),
            "android_version": device_info.get("ro.build.version.release", "Unknown"),
            "api_level": device_info.get("ro.build.version.sdk", "Unknown"),
            "serial": device_info.get("ro.serialno", "Unknown"),
        }
    
    def cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        self._cache.cleanup_old_entries()