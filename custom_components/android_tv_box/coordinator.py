"""Data update coordinator for Android TV Box Integration."""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .adb_manager import ADBManager
from .const import (
    BASE_UPDATE_INTERVAL,
    DEFAULT_APPS,
    DOMAIN,
    HIGH_FREQUENCY_INTERVAL,
    ISG_CHECK_INTERVAL,
    ISG_HEALTH_HEALTHY,
    ISG_HEALTH_NOT_RUNNING,
    ISG_HEALTH_UNKNOWN,
    LOW_FREQUENCY_INTERVAL,
    MAX_ISG_RESTART_ATTEMPTS,
    MEDIA_STATE_IDLE,
    POWER_STATE_OFF,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class AndroidTVState:
    """State data for Android TV device."""
    # Connection state
    is_connected: bool = False
    last_seen: Optional[datetime] = None
    connection_error: Optional[str] = None
    
    # Power state
    power_state: str = POWER_STATE_OFF
    screen_on: bool = False
    wakefulness: Optional[str] = None
    
    # Media state
    media_state: str = MEDIA_STATE_IDLE
    volume_level: int = 0
    volume_max: int = 15
    volume_percentage: float = 0.0
    is_muted: bool = False
    
    # Cast state
    cast_active: bool = False
    cast_app: Optional[str] = None
    cast_media_title: Optional[str] = None
    
    # ISG monitoring state
    isg_running: bool = False
    isg_pid: Optional[int] = None
    isg_uptime_minutes: int = 0
    isg_last_start_time: Optional[datetime] = None
    isg_memory_usage_mb: float = 0.0
    isg_memory_percentage: float = 0.0
    isg_cpu_usage: float = 0.0
    isg_crash_count: int = 0
    isg_last_crash_time: Optional[datetime] = None
    isg_last_crash_reason: Optional[str] = None
    isg_anr_count: int = 0
    isg_last_anr_time: Optional[datetime] = None
    isg_restart_count: int = 0
    isg_health_status: str = ISG_HEALTH_UNKNOWN
    isg_last_health_check: Optional[datetime] = None
    isg_network_connections: int = 0
    isg_storage_usage_mb: float = 0.0
    isg_permission_issues: List[str] = field(default_factory=list)
    
    # App and network state
    current_app_package: Optional[str] = None
    current_app_name: Optional[str] = None
    current_activity: Optional[str] = None
    wifi_enabled: bool = True
    wifi_ssid: Optional[str] = None
    ip_address: Optional[str] = None
    
    # System performance
    brightness: int = 128
    brightness_percentage: float = 50.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    
    # Device information
    device_model: Optional[str] = None
    device_manufacturer: Optional[str] = None
    android_version: Optional[str] = None
    api_level: Optional[str] = None
    device_serial: Optional[str] = None
    
    # Installed apps
    installed_apps: List[str] = field(default_factory=list)
    configured_apps: Dict[str, str] = field(default_factory=lambda: DEFAULT_APPS.copy())
    
    # Screenshot data
    screenshot_path: str = "/sdcard/isgbackup/screenshot/"
    screenshot_data: Optional[bytes] = None
    screenshot_timestamp: Optional[datetime] = None
    
    def update_from_device_info(self, device_info: Dict[str, Any]) -> None:
        """Update state from device info."""
        self.device_model = device_info.get("model")
        self.device_manufacturer = device_info.get("manufacturer")
        self.android_version = device_info.get("android_version")
        self.api_level = device_info.get("api_level")
        self.device_serial = device_info.get("serial")
    
    def update_power_state(self, wakefulness: str, screen_on: bool) -> None:
        """Update power state."""
        self.wakefulness = wakefulness
        self.screen_on = screen_on
        
        if wakefulness == "Awake" and screen_on:
            self.power_state = "on"
        elif wakefulness == "Asleep":
            self.power_state = "off"
        else:
            self.power_state = "standby"
    
    def update_volume_state(self, current: int, max_vol: int, is_muted: bool) -> None:
        """Update volume state."""
        self.volume_level = current
        self.volume_max = max_vol
        self.is_muted = is_muted
        self.volume_percentage = (current / max_vol * 100) if max_vol > 0 else 0
    
    def update_brightness_state(self, brightness: int) -> None:
        """Update brightness state."""
        self.brightness = brightness
        self.brightness_percentage = (brightness / 255 * 100) if brightness > 0 else 0
    
    def update_wifi_state(self, enabled: bool, ssid: Optional[str], ip: Optional[str]) -> None:
        """Update WiFi state."""
        self.wifi_enabled = enabled
        self.wifi_ssid = ssid
        self.ip_address = ip
    
    def update_app_from_output(self, activity_output: str) -> None:
        """Update current app from activity output."""
        if activity_output:
            # Parse activity output to get package name
            parts = activity_output.split('/')
            if len(parts) >= 1:
                package = parts[0].split()[-1] if ' ' in parts[0] else parts[0]
                self.current_app_package = package
                
                # Try to find friendly name
                for name, pkg in self.configured_apps.items():
                    if pkg == package:
                        self.current_app_name = name
                        break
                else:
                    self.current_app_name = package
    
    def update_isg_health(self, health_data: Dict[str, Any]) -> None:
        """Update ISG health status."""
        self.isg_running = health_data.get("is_running", False)
        self.isg_memory_usage_mb = health_data.get("memory_usage", 0.0)
        self.isg_cpu_usage = health_data.get("cpu_usage", 0.0)
        self.isg_health_status = health_data.get("health_status", ISG_HEALTH_UNKNOWN)
        self.isg_last_health_check = health_data.get("last_check")
        
        if health_data.get("crash_detected"):
            self.isg_crash_count += 1
            self.isg_last_crash_time = datetime.now()


class AndroidTVUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for Android TV Box."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        adb_manager: ADBManager,
        config: Dict[str, Any],
    ):
        """Initialize coordinator."""
        self.adb_manager = adb_manager
        self.config = config
        self.data = AndroidTVState()
        
        # Update intervals and timing
        self._last_basic_update = datetime.min
        self._last_high_frequency_update = datetime.min
        self._last_low_frequency_update = datetime.min
        self._last_isg_check = datetime.min
        
        # ISG monitoring configuration
        self._isg_monitoring_enabled = config.get("isg_monitoring", True)
        self._isg_auto_restart_enabled = config.get("isg_auto_restart", True)
        self._isg_memory_threshold = config.get("isg_memory_threshold", 85)
        self._isg_cpu_threshold = config.get("isg_cpu_threshold", 95)
        
        # Performance optimization settings
        self._smart_monitoring = config.get("smart_monitoring", True)
        self._skip_when_offline = config.get("skip_when_offline", True)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=BASE_UPDATE_INTERVAL,
        )
    
    async def _async_update_data(self) -> AndroidTVState:
        """Fetch data from device."""
        try:
            current_time = datetime.now()
            
            # Check connection first
            if not await self._ensure_connection():
                if self.data.is_connected:
                    self.data.is_connected = False
                    self.data.connection_error = "Connection lost"
                raise UpdateFailed("Cannot connect to device")
            
            # Update connection state
            self.data.is_connected = True
            self.data.last_seen = current_time
            self.data.connection_error = None
            
            # Smart monitoring - skip detailed checks if needed
            if self._smart_monitoring and self._should_skip_detailed_check():
                return self.data
            
            # Layered update strategy
            await self._update_basic_status(current_time)
            
            if self._should_update_high_frequency(current_time):
                await self._update_high_frequency_items(current_time)
            
            if self._should_update_low_frequency(current_time):
                await self._update_low_frequency_items(current_time)
            
            if self._isg_monitoring_enabled and self._should_update_isg(current_time):
                await self._update_isg_status(current_time)
            
            # Cleanup
            self.adb_manager.cleanup_cache()
            
            return self.data
            
        except Exception as err:
            self.data.is_connected = False
            self.data.connection_error = str(err)
            raise UpdateFailed(f"Error communicating with device: {err}")
    
    async def _ensure_connection(self) -> bool:
        """Ensure ADB connection is established."""
        if await self.adb_manager.is_connected():
            return True
        
        _LOGGER.info("Attempting to reconnect to device")
        return await self.adb_manager.connect()
    
    def _should_skip_detailed_check(self) -> bool:
        """Determine if detailed checks should be skipped."""
        if not self._skip_when_offline:
            return False
        
        # Skip if device was recently offline
        if (self.data.power_state == POWER_STATE_OFF and 
            self.data.last_seen and 
            datetime.now() - self.data.last_seen < timedelta(minutes=5)):
            return True
        
        return False
    
    def _should_update_basic(self, current_time: datetime) -> bool:
        """Check if basic status should be updated."""
        return current_time - self._last_basic_update >= BASE_UPDATE_INTERVAL
    
    def _should_update_high_frequency(self, current_time: datetime) -> bool:
        """Check if high-frequency items should be updated."""
        return current_time - self._last_high_frequency_update >= HIGH_FREQUENCY_INTERVAL
    
    def _should_update_low_frequency(self, current_time: datetime) -> bool:
        """Check if low-frequency items should be updated."""
        return current_time - self._last_low_frequency_update >= LOW_FREQUENCY_INTERVAL
    
    def _should_update_isg(self, current_time: datetime) -> bool:
        """Check if ISG status should be updated."""
        return current_time - self._last_isg_check >= ISG_CHECK_INTERVAL
    
    async def _update_basic_status(self, current_time: datetime) -> None:
        """Update basic device status."""
        # Power state
        wakefulness, screen_on = await self.adb_manager.get_power_state()
        self.data.update_power_state(wakefulness, screen_on)
        
        # Media state
        self.data.media_state = await self.adb_manager.get_media_state()
        
        # Volume state
        volume_current, volume_max, is_muted = await self.adb_manager.get_volume_state()
        self.data.update_volume_state(volume_current, volume_max, is_muted)
        
        self._last_basic_update = current_time
    
    async def _update_high_frequency_items(self, current_time: datetime) -> None:
        """Update high-frequency monitoring items."""
        # Current activity
        current_activity = await self.adb_manager.get_current_activity()
        if current_activity:
            self.data.update_app_from_output(current_activity)
        
        # Brightness
        brightness = await self.adb_manager.get_brightness()
        if brightness is not None:
            self.data.update_brightness_state(brightness)
        
        self._last_high_frequency_update = current_time
    
    async def _update_low_frequency_items(self, current_time: datetime) -> None:
        """Update low-frequency monitoring items."""
        # Device info (only if not already set)
        if not self.data.device_model:
            device_info = await self.adb_manager.get_device_info()
            self.data.update_from_device_info(device_info)
        
        # WiFi state
        wifi_enabled, wifi_ssid, ip_address = await self.adb_manager.get_wifi_state()
        self.data.update_wifi_state(wifi_enabled, wifi_ssid, ip_address)
        
        # Installed apps (periodically refresh)
        installed_apps = await self.adb_manager.get_installed_apps()
        self.data.installed_apps = installed_apps
        
        self._last_low_frequency_update = current_time
    
    async def _update_isg_status(self, current_time: datetime) -> None:
        """Update ISG application status."""
        try:
            # Perform health check
            health_data = await self.adb_manager.perform_isg_health_check()
            self.data.update_isg_health(health_data)
            
            # Auto-restart logic
            if self._isg_auto_restart_enabled and self._should_restart_isg():
                await self._attempt_isg_restart()
            
            self._last_isg_check = current_time
            
        except Exception as e:
            _LOGGER.error("Failed to update ISG status: %s", e)
            self.data.isg_health_status = ISG_HEALTH_UNKNOWN
    
    def _should_restart_isg(self) -> bool:
        """Determine if ISG should be restarted."""
        if not self._isg_auto_restart_enabled:
            return False
        
        # Don't restart if too many recent attempts
        if self.data.isg_restart_count >= MAX_ISG_RESTART_ATTEMPTS:
            return False
        
        # Restart if not running
        if not self.data.isg_running:
            return True
        
        # Restart if unhealthy and resource usage is high
        if (self.data.isg_health_status in ["unhealthy", "crashed"] and
            (self.data.isg_memory_percentage > self._isg_memory_threshold or
             self.data.isg_cpu_usage > self._isg_cpu_threshold)):
            return True
        
        # Avoid frequent restarts
        if (self.data.isg_last_start_time and 
            datetime.now() - self.data.isg_last_start_time < timedelta(minutes=5)):
            return False
        
        return False
    
    async def _attempt_isg_restart(self) -> bool:
        """Attempt to restart ISG application."""
        try:
            _LOGGER.info("Attempting to restart ISG application")
            
            # Force stop first
            await self.adb_manager.force_stop_isg()
            await asyncio.sleep(2)
            
            # Start application
            success = await self.adb_manager.force_start_isg()
            
            if success:
                self.data.isg_restart_count += 1
                self.data.isg_last_start_time = datetime.now()
                self.data.isg_health_status = ISG_HEALTH_HEALTHY
                _LOGGER.info("ISG application restarted successfully")
            else:
                _LOGGER.error("Failed to restart ISG application")
            
            return success
            
        except Exception as e:
            _LOGGER.error("Error during ISG restart: %s", e)
            return False
    
    # Control methods with immediate feedback
    async def set_volume_with_feedback(self, volume_level: float) -> bool:
        """Set volume with immediate state feedback."""
        try:
            # Convert percentage to device level
            target_level = int(volume_level * self.data.volume_max)
            success = await self.adb_manager.set_volume(target_level)
            
            if success:
                # Wait briefly for command to take effect
                await asyncio.sleep(0.3)
                
                # Query current state immediately
                current, max_vol, is_muted = await self.adb_manager.get_volume_state()
                self.data.update_volume_state(current, max_vol, is_muted)
                
                # Trigger entity state updates
                self.async_update_listeners()
            
            return success
            
        except Exception as e:
            _LOGGER.error("Error setting volume: %s", e)
            return False
    
    async def set_brightness_with_feedback(self, brightness: int) -> bool:
        """Set brightness with immediate state feedback."""
        try:
            success = await self.adb_manager.set_brightness(brightness)
            
            if success:
                await asyncio.sleep(0.3)
                
                # Query current brightness
                current_brightness = await self.adb_manager.get_brightness()
                if current_brightness is not None:
                    self.data.update_brightness_state(current_brightness)
                    self.async_update_listeners()
            
            return success
            
        except Exception as e:
            _LOGGER.error("Error setting brightness: %s", e)
            return False
    
    async def start_app_with_feedback(self, package_name: str) -> bool:
        """Start app with immediate state feedback."""
        try:
            success = await self.adb_manager.start_app(package_name)
            
            if success:
                await asyncio.sleep(2.0)  # Wait for app to start
                
                # Query current activity
                current_activity = await self.adb_manager.get_current_activity()
                if current_activity:
                    self.data.update_app_from_output(current_activity)
                    self.async_update_listeners()
            
            return success
            
        except Exception as e:
            _LOGGER.error("Error starting app: %s", e)
            return False
    
    async def power_control_with_feedback(self, turn_on: bool) -> bool:
        """Control power with immediate state feedback."""
        try:
            if turn_on:
                success = await self.adb_manager.power_on()
            else:
                success = await self.adb_manager.power_off()
            
            if success:
                await asyncio.sleep(1.0)
                
                # Query power state
                wakefulness, screen_on = await self.adb_manager.get_power_state()
                self.data.update_power_state(wakefulness, screen_on)
                self.async_update_listeners()
            
            return success
            
        except Exception as e:
            _LOGGER.error("Error controlling power: %s", e)
            return False
    
    async def restart_isg_with_feedback(self) -> bool:
        """Restart ISG with immediate state feedback."""
        try:
            success = await self.adb_manager.restart_isg()
            
            if success:
                await asyncio.sleep(3.0)  # Wait for restart
                
                # Check ISG status
                health_data = await self.adb_manager.perform_isg_health_check()
                self.data.update_isg_health(health_data)
                
                if health_data.get("is_running"):
                    self.data.isg_last_start_time = datetime.now()
                    self.data.isg_restart_count += 1
                
                self.async_update_listeners()
            
            return success
            
        except Exception as e:
            _LOGGER.error("Error restarting ISG: %s", e)
            return False
    
    async def clear_isg_cache_with_feedback(self) -> bool:
        """Clear ISG cache with immediate state feedback."""
        try:
            success = await self.adb_manager.clear_isg_cache()
            
            if success:
                await asyncio.sleep(2.0)
                
                # Restart ISG after cache clear
                restart_success = await self.adb_manager.force_start_isg()
                
                if restart_success:
                    await asyncio.sleep(3.0)
                    
                    # Check status
                    health_data = await self.adb_manager.perform_isg_health_check()
                    self.data.update_isg_health(health_data)
                    
                    if health_data.get("is_running"):
                        self.data.isg_last_start_time = datetime.now()
                    
                    self.async_update_listeners()
                
                return restart_success
            
            return success
            
        except Exception as e:
            _LOGGER.error("Error clearing ISG cache: %s", e)
            return False
    
    async def take_screenshot_with_feedback(self) -> bool:
        """Take screenshot with immediate data retrieval."""
        try:
            timestamp = datetime.now()
            filename = f"screenshot_{timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            device_path = f"{self.data.screenshot_path}{filename}"
            
            # Take screenshot
            success = await self.adb_manager.take_screenshot(device_path)
            
            if success:
                # Get screenshot data
                screenshot_data = await self.adb_manager.get_screenshot_data(device_path)
                
                if screenshot_data:
                    self.data.screenshot_data = screenshot_data
                    self.data.screenshot_timestamp = timestamp
                    self.async_update_listeners()
                    return True
            
            return False
            
        except Exception as e:
            _LOGGER.error("Error taking screenshot: %s", e)
            return False
    
    def get_app_package(self, app_name: str) -> Optional[str]:
        """Get package name for app."""
        return self.data.configured_apps.get(app_name)
    
    def get_app_name(self, package_name: str) -> Optional[str]:
        """Get friendly name for package."""
        for name, package in self.data.configured_apps.items():
            if package == package_name:
                return name
        return package_name