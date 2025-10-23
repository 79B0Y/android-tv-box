"""ADB Manager for Android TV Box Integration."""
import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
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
    CACHE_MAX_SIZE,
    COMMAND_CACHE_TTL,
    CONNECTION_TIMEOUT,
    ECHO_TEST_TIMEOUT,
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
    CAST_INTENTS,
    CAST_EXPECTED_PACKAGES,
    STATE_COMMANDS,
)

_LOGGER = logging.getLogger(__name__)

# Pre-compiled regex patterns for performance
VOLUME_PATTERN = re.compile(r"volume is (\d+) in range \[(\d+)\.\.(\d+)\]")
SSID_PATTERN = re.compile(r'SSID:\s*"([^"]+)"')
IP_PATTERN = re.compile(r'inet (\d+\.\d+\.\d+\.\d+)')
CPU_PATTERN = re.compile(r'(\d+\.?\d*)%')
# Match topResumedActivity format: topResumedActivity=ActivityRecord{... u0 com.package/activity ...}
ACTIVITY_PATTERN = re.compile(r'topResumedActivity=ActivityRecord\{[^\}]+\s+u\d+\s+([^\s]+)\s')
MEMORY_TOTAL_PATTERN = re.compile(r'TOTAL.*?(\d+)')


@dataclass
class ADBCommandResult:
    """Result of an ADB command execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None


@dataclass
class CommandCache:
    """Cache for ADB commands with LRU eviction."""
    cache: OrderedDict = field(default_factory=OrderedDict)
    pending: Dict[str, asyncio.Task] = field(default_factory=dict)
    max_size: int = CACHE_MAX_SIZE
    hits: int = 0
    misses: int = 0
    
    def get_cache_key(self, device_id: str, command: str) -> str:
        """Generate cache key."""
        return f"{device_id}_{hash(command)}"
    
    def is_cached(self, cache_key: str) -> bool:
        """Check if command result is cached and valid."""
        if cache_key not in self.cache:
            return False
        
        result, timestamp = self.cache[cache_key]
        if time.time() - timestamp >= COMMAND_CACHE_TTL:
            # Expired entry
            del self.cache[cache_key]
            return False
        
        # Move to end (most recently used)
        self.cache.move_to_end(cache_key)
        return True
    
    def get_cached(self, cache_key: str) -> Optional[ADBCommandResult]:
        """Get cached result."""
        if self.is_cached(cache_key):
            result, _ = self.cache[cache_key]
            self.hits += 1
            return result
        self.misses += 1
        return None
    
    def set_cached(self, cache_key: str, result: ADBCommandResult) -> None:
        """Cache command result with LRU eviction."""
        # Remove oldest entry if cache is full
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            self.cache.popitem(last=False)
        
        self.cache[cache_key] = (result, time.time())
        self.cache.move_to_end(cache_key)
    
    def cleanup_old_entries(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= COMMAND_CACHE_TTL
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
        }


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
        self._screenshot_lock = asyncio.Lock()  # Prevent concurrent screenshot requests
        self._cache = CommandCache()
        self._logger = _LOGGER.getChild(f"{host}_{port}")
        
    async def connect(self) -> bool:
        """Connect to Android TV device via ADB."""
        try:
            self._logger.info("Attempting to connect to %s:%s", self.host, self.port)
            
            # Connect using adb-shell
            self._device = AdbDeviceTcp(self.host, self.port)
            
            # The connect method might be sync, so run it in executor
            def _connect():
                self._logger.debug("Executing ADB connect for %s:%s", self.host, self.port)
                rsa_keys = getattr(self, "_rsa_signers", None)
                return self._device.connect(rsa_keys=rsa_keys, auth_timeout_s=ADB_TIMEOUT)
            
            # Run the potentially blocking connect in an executor
            loop = asyncio.get_event_loop()
            connect_result = await loop.run_in_executor(None, _connect)
            
            self._logger.debug("ADB connect result: %s", connect_result)
            
            if connect_result:
                # Test connection with simple command
                self._logger.debug("Testing connection with echo command")
                result = await self._execute_with_device("echo test")
                self._logger.debug("Echo test result: success=%s, stdout='%s'", result.success, result.stdout)
                
                if result.success and "test" in result.stdout:
                    self._connected = True
                    self._logger.info("Successfully connected to %s:%s via adb-shell", self.host, self.port)
                    return True
                else:
                    self._logger.warning("Connection test failed for %s:%s", self.host, self.port)
            else:
                self._logger.warning("ADB connect returned False for %s:%s", self.host, self.port)
                
        except (TcpTimeoutException, ConnectionError, OSError) as e:
            self._logger.error("Connection error for %s:%s: %s", self.host, self.port, e)
        except ImportError as e:
            self._logger.error("Missing dependency for ADB connection: %s", e)
        except Exception as e:
            self._logger.error("Unexpected error connecting to %s:%s: %s", self.host, self.port, e)
            import traceback
            self._logger.debug("Connection traceback: %s", traceback.format_exc())
            
        self._connected = False
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from device."""
        try:
            if self._device:
                # The close method might also be sync
                def _close():
                    return self._device.close()
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, _close)
                self._device = None
        except (OSError, ConnectionError) as e:
            self._logger.debug("Error during disconnect: %s", e)
        except Exception as e:
            self._logger.warning("Unexpected error during disconnect: %s", e)
        finally:
            self._connected = False
            
    async def is_connected(self) -> bool:
        """Check if connected to device."""
        if not self._connected:
            return False
            
        try:
            # Quick connectivity test
            result = await asyncio.wait_for(
                self.execute_command("echo ping"), 
                timeout=ECHO_TEST_TIMEOUT
            )
            return result.success and "ping" in result.stdout
        except asyncio.TimeoutError:
            self._logger.debug("Connection check timed out")
            self._connected = False
            return False
        except Exception as e:
            self._logger.debug("Connection check failed: %s", e)
            self._connected = False
            return False
    
    async def execute_command(self, command: str, use_cache: bool = True) -> ADBCommandResult:
        """Execute a shell command on the connected device with caching and concurrency control.

        Note: With adb-shell, we do not prefix commands with 'shell' or '-s'.
        Commands should be raw device shell commands like 'input keyevent 26'.
        """
        full_command = command
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
            # The shell method might be sync, so run it in executor
            def _shell():
                return self._device.shell(command)
            
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _shell),
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
        # If media session is BUFFERING or PAUSED, send PLAY; otherwise toggle PLAY_PAUSE as fallback
        pre = await self.execute_command(STATE_COMMANDS["media_state"], use_cache=False)
        pre_state = pre.stdout if (pre.success and pre.stdout) else ""
        prefer_play = ("PAUSED" in pre_state) or ("BUFFERING" in pre_state) or ("STOPPED" in pre_state)
        cmd = ADB_COMMANDS["media_play"] if prefer_play else ADB_COMMANDS["media_play_pause"]
        result = await self.execute_command(cmd, use_cache=False)
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
        """Get current media playback state.

        Parse dumpsys media_session output to find the active session's PlaybackState.
        Avoid shell-side awk/grep to maximize compatibility.
        """
        result = await self.execute_command(STATE_COMMANDS["media_state"], use_cache=False)
        if not (result.success and result.stdout):
            return MEDIA_STATE_IDLE

        text = result.stdout
        # Prefer the first occurrence of PlaybackState with 'state='<STATE>
        # Example: state=PlaybackState {state=PLAYING(3), ...}
        try:
            match = re.search(r"state=PlaybackState\s*\{?state=([A-Z_]+)\(", text)
            if match:
                st = match.group(1)
                if st == "PLAYING":
                    return MEDIA_STATE_PLAYING
                if st in ("PAUSED", "PAUSE"):
                    return MEDIA_STATE_PAUSED
                if st in ("STOPPED", "STOP"):
                    return MEDIA_STATE_IDLE
        except Exception:
            pass
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
        # Try primary command
        cmd = SET_COMMANDS["set_volume"].format(level=level)
        res = await self.execute_command(cmd, use_cache=False)
        if not res.success:
            # Fallback to alt command
            alt = SET_COMMANDS.get("set_volume_alt")
            if alt:
                res = await self.execute_command(alt.format(level=level), use_cache=False)
        return res.success
    
    async def get_volume_state(self) -> Tuple[int, int, bool]:
        """Get volume state (current, max, is_muted) with accurate mute detection."""
        # 1) Exact volume level
        result = await self.execute_command(STATE_COMMANDS["volume_level"], use_cache=False)
        current = 0
        max_vol = 15
        if result.success and result.stdout:
            m = VOLUME_PATTERN.search(result.stdout)
            if m:
                current = int(m.group(1))
                min_vol = int(m.group(2))
                max_vol = int(m.group(3))
        
        # 2) Accurate mute via dumpsys audio STREAM_MUSIC section
        muted = False
        audio = await self.execute_command(STATE_COMMANDS["audio_info"], use_cache=False)
        if audio.success and audio.stdout:
            try:
                # Narrow to STREAM_MUSIC block then search Muted: true/false
                # Split by lines; scan when encountering '- STREAM_MUSIC' header
                lines = audio.stdout.splitlines()
                in_music = False
                for line in lines:
                    if "- STREAM_MUSIC" in line:
                        in_music = True
                        continue
                    if in_music and line.startswith('- '):
                        # Reached next stream block
                        break
                    if in_music and 'Muted:' in line:
                        muted = 'true' in line.lower()
                        break
            except Exception:
                pass
        
        return current, max_vol, muted
    
    # Power control methods
    async def power_on(self) -> bool:
        """Wake up device."""
        # Send WAKEUP first
        await self.execute_command(ADB_COMMANDS["power_on"], use_cache=False)
        # Poll and fallback to POWER toggle if still not awake
        for _ in range(4):
            await asyncio.sleep(0.7)
            wakefulness, _ = await self.get_power_state()
            if wakefulness == "Awake":
                return True
            # Try power toggle to wake some ROMs
            await self.execute_command(ADB_COMMANDS.get("power_toggle", ""), use_cache=False)
        return False
    
    async def power_off(self) -> bool:
        """Put device to sleep."""
        res = await self.execute_command(ADB_COMMANDS["power_off"], use_cache=False)
        if not res.success:
            await asyncio.sleep(0.3)
            res = await self.execute_command(ADB_COMMANDS.get("power_toggle", ""), use_cache=False)
        return res.success
    
    async def get_power_state(self) -> Tuple[str, bool]:
        """Get power state (wakefulness, screen_on)."""
        # Disable cache to avoid stale power state right after toggling
        result = await self.execute_command(STATE_COMMANDS["power_state"], use_cache=False)
        if result.success and result.stdout:
            txt = result.stdout
            # Normalize and search
            wakefulness = "Unknown"
            screen_on = False
            # Common patterns across ROMs
            if "mWakefulness=Awake" in txt or "mWakefulness= WAKING" in txt or "mWakefulness= AWAKE" in txt:
                wakefulness = "Awake"
            elif "mWakefulness=Asleep" in txt or "mWakefulness= SLEEP" in txt:
                wakefulness = "Asleep"
            elif "mWakefulness=Dreaming" in txt:
                wakefulness = "Dreaming"
            # Screen state variants
            if "mScreenOn=true" in txt or "mScreenState=ON" in txt or "mDisplayPowerState=ON" in txt:
                screen_on = True
            elif "mScreenOn=false" in txt or "mScreenState=OFF" in txt:
                screen_on = False
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
                ssid_match = SSID_PATTERN.search(result.stdout)
                if ssid_match:
                    ssid = ssid_match.group(1)
            
            # Get IP address
            result = await self.execute_command(STATE_COMMANDS["ip_address"])
            if result.success and result.stdout:
                ip_match = IP_PATTERN.search(result.stdout)
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
            match = ACTIVITY_PATTERN.search(result.stdout)
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
        """Get screenshot data from device.

        This method:
        1. Takes a screenshot and saves it to /sdcard/isgbackup/screenshot/latest.png
        2. Reads the file using adb pull
        3. Uses a lock to prevent concurrent screenshot requests from interfering

        Note: This method uses a lock to ensure only one screenshot operation
        happens at a time, preventing race conditions.
        """
        async with self._screenshot_lock:
            try:
                screenshot_path = "/sdcard/isgbackup/screenshot/latest.png"

                # Step 1: Ensure screenshot directory exists
                mkdir_cmd = "mkdir -p /sdcard/isgbackup/screenshot"
                mkdir_result = await self.execute_command(mkdir_cmd, use_cache=False)

                if not mkdir_result.success:
                    self._logger.warning("Failed to create screenshot directory")

                # Step 2: Take screenshot and save to device (use background execution)
                # Note: We don't delete the old file first - screencap will overwrite it
                # This avoids race conditions where pull happens before screencap completes
                # screencap can take a long time and may timeout, so we run it in background
                # and then verify the file exists
                screencap_cmd = f"screencap {screenshot_path} &"
                await self.execute_command(screencap_cmd, use_cache=False)

                # Wait for screenshot to complete (typically takes 1-3 seconds)
                await asyncio.sleep(2.0)

                # Step 3: Verify file was created and has content (retry a few times)
                max_retries = 3
                screenshot_found = False
                verify_result = None

                for retry in range(max_retries):
                    verify_cmd = f"ls -l {screenshot_path}"
                    verify_result = await self.execute_command(verify_cmd, use_cache=False)

                    if verify_result.success and verify_result.stdout.strip() != "":
                        # Check if file has non-zero size
                        if " 0 " not in verify_result.stdout:
                            screenshot_found = True
                            self._logger.debug("Screenshot file verified on retry %d", retry + 1)
                            break

                    # Wait before retry
                    if retry < max_retries - 1:
                        await asyncio.sleep(1.0)

                if not screenshot_found:
                    self._logger.error("Screenshot file not found or empty after %d retries", max_retries)
                    return None

                # Step 4: Use _device.pull() to read the file into BytesIO
                bytes_buffer = BytesIO()
                self._device.pull(screenshot_path, bytes_buffer)
                screenshot_data = bytes_buffer.getvalue()

                if screenshot_data and len(screenshot_data) > 0:
                    # Verify it's a valid PNG file
                    if screenshot_data[:8] == b'\x89PNG\r\n\x1a\n':
                        self._logger.info("Screenshot captured successfully, size: %d bytes", len(screenshot_data))
                        return screenshot_data
                    else:
                        self._logger.error("Screenshot file is not a valid PNG")
                        return None
                else:
                    self._logger.error("Screenshot file is empty")
                    return None

            except Exception as e:
                self._logger.error("Failed to capture screenshot: %s", e)
                return None
    
    # Cast methods
    async def cast_media_url(self, url: str) -> bool:
        """Cast a generic media URL using system VIEW intent."""
        command = SET_COMMANDS["cast_media"].format(url=url)
        result = await self.execute_command(command, use_cache=False)
        return result.success

    async def _try_intents(self, commands: list[str]) -> bool:
        """Try a list of am start commands until one succeeds."""
        for cmd in commands:
            self._logger.debug("Trying cast intent: %s", cmd)
            res = await self.execute_command(cmd, use_cache=False)
            if res.success:
                return True
        return False

    async def _verify_current_package(self, expected_packages: list[str]) -> bool:
        """Verify that one of expected packages is now the foreground app."""
        try:
            activity = await self.get_current_activity()
            if not activity:
                return False
            pkg = activity.split('/')[0]
            return pkg in expected_packages
        except Exception:
            return False

    async def cast_youtube_video(self, video_id: str) -> bool:
        """Cast YouTube video (TV-first)."""
        ok = await self._try_intents([c.format(video_id=video_id) for c in CAST_INTENTS["youtube"]])
        if not ok:
            return False
        await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["app_start"])  # give it time
        return await self._verify_current_package(CAST_EXPECTED_PACKAGES["youtube"]) or ok

    async def cast_netflix_video(self, video_id: str) -> bool:
        """Cast Netflix video (TV-first)."""
        ok = await self._try_intents([c.format(video_id=video_id) for c in CAST_INTENTS["netflix"]])
        if not ok:
            return False
        await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["app_start"])  # give it time
        return await self._verify_current_package(CAST_EXPECTED_PACKAGES["netflix"]) or ok

    async def cast_spotify_track(self, track_id: str) -> bool:
        """Cast Spotify track (TV-first)."""
        ok = await self._try_intents([c.format(track_id=track_id) for c in CAST_INTENTS["spotify"]])
        if not ok:
            return False
        await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["app_start"])  # give it time
        return await self._verify_current_package(CAST_EXPECTED_PACKAGES["spotify"]) or ok
    
    # ISG monitoring methods (backward compatibility - delegate to ISGMonitor)
    async def check_isg_process_status(self) -> bool:
        """Check if ISG process is running using pidof."""
        result = await self.execute_command(ISG_COMMANDS["process_status"], use_cache=False)
        if result.success and result.stdout:
            pid = result.stdout.strip()
            return pid.isdigit()
        return False
    
    async def get_isg_memory_usage(self) -> Tuple[Optional[float], Optional[float]]:
        """Get ISG memory usage (MB, percentage) from dumpsys meminfo."""
        result = await self.execute_command(ISG_COMMANDS["memory_usage"], use_cache=False)
        if not (result.success and result.stdout):
            return None, None
        mem_mb = None
        total_pct = None
        for line in result.stdout.split('\n'):
            # Typical line: TOTAL  123456   7890   ... (kB)
            if 'TOTAL' in line:
                m = MEMORY_TOTAL_PATTERN.search(line)
                if m:
                    mem_kb = int(m.group(1))
                    mem_mb = mem_kb / 1024.0
                    break
        # Percentage unknown without system total; leave None
        return mem_mb, total_pct
    
    async def get_isg_cpu_usage(self) -> Optional[float]:
        """Get ISG CPU usage percentage from top for specific PID."""
        result = await self.execute_command(ISG_COMMANDS["cpu_usage"], use_cache=False)
        if not (result.success and result.stdout):
            return None
        text = result.stdout
        if 'NO_PID' in text:
            return None
        # Find a line containing the package and capture CPU column
        for line in text.strip().split('\n'):
            if 'com.linknlink.app.device.isg' in line:
                parts = line.split()
                # Heuristic: after state letter comes %CPU then %MEM
                for i, tok in enumerate(parts):
                    if tok in ('S','R','D','T','Z') and i + 2 < len(parts):
                        try:
                            cpu = float(parts[i+1])
                            return cpu
                        except Exception:
                            continue
        return None
    
    async def force_start_isg(self) -> bool:
        """Force start ISG application.
        
        Note: This method is kept for backward compatibility.
        Consider using ISGMonitor directly for new code.
        """
        result = await self.execute_command(ISG_CONTROL_COMMANDS["force_start"], use_cache=False)
        return result.success
    
    async def force_stop_isg(self) -> bool:
        """Force stop ISG application.
        
        Note: This method is kept for backward compatibility.
        Consider using ISGMonitor directly for new code.
        """
        result = await self.execute_command(ISG_CONTROL_COMMANDS["force_stop"], use_cache=False)
        return result.success
    
    async def restart_isg(self) -> bool:
        """Restart ISG application.
        
        Note: This method is kept for backward compatibility.
        Consider using ISGMonitor directly for new code.
        """
        result = await self.execute_command(ISG_CONTROL_COMMANDS["restart"], use_cache=False)
        return result.success
    
    async def clear_isg_cache(self) -> bool:
        """Clear ISG application cache.
        
        Note: This method is kept for backward compatibility.
        Consider using ISGMonitor directly for new code.
        """
        result = await self.execute_command(ISG_CONTROL_COMMANDS["clear_cache"], use_cache=False)
        return result.success
    
    async def get_isg_logs(self, lines: int = 50) -> List[str]:
        """Get ISG application logs.
        
        Note: This method is kept for backward compatibility.
        Consider using ISGMonitor directly for new code.
        """
        result = await self.execute_command(ISG_COMMANDS["app_logs"])
        if result.success and result.stdout:
            return result.stdout.split('\n')[:lines]
        return []
    
    async def get_isg_crash_logs(self) -> List[str]:
        """Get ISG crash logs.
        
        Note: This method is kept for backward compatibility.
        Consider using ISGMonitor directly for new code.
        """
        result = await self.execute_command(ISG_COMMANDS["crash_logs"])
        if result.success and result.stdout:
            return result.stdout.split('\n')
        return []
    
    async def perform_isg_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive ISG health check.
        
        Note: This method is kept for backward compatibility.
        Consider using ISGMonitor directly for new code.
        """
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
