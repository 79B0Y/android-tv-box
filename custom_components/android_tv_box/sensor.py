"""Sensor entities for Android TV Box Integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ISG_HEALTH_HEALTHY, ISG_HEALTH_NOT_RUNNING
from .coordinator import AndroidTVUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Android TV Box sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = [
        AndroidTVBrightnessSensor(coordinator, entry),
        AndroidTVNetworkSensor(coordinator, entry),
        AndroidTVAppSensor(coordinator, entry),
        AndroidTVCPUSensor(coordinator, entry),
        AndroidTVMemorySensor(coordinator, entry),
        AndroidTVISGStatusSensor(coordinator, entry),
        AndroidTVISGMemorySensor(coordinator, entry),
        AndroidTVISGUptimeSensor(coordinator, entry),
        AndroidTVISGCrashCountSensor(coordinator, entry),
    ]

    async_add_entities(entities, True)


class AndroidTVBaseSensor(CoordinatorEntity[AndroidTVUpdateCoordinator], SensorEntity):
    """Base class for Android TV sensors."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
    
    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self.coordinator.adb_manager.host}_{self.coordinator.adb_manager.port}")},
            "name": self._entry.data.get("device_name", "Android TV Box"),
            "manufacturer": self.coordinator.data.device_manufacturer or "Android",
            "model": self.coordinator.data.device_model or "TV Box",
            "sw_version": self.coordinator.data.android_version,
        }
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data.is_connected


class AndroidTVBrightnessSensor(AndroidTVBaseSensor):
    """Sensor for screen brightness."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the brightness sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_brightness"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Brightness"
        self._attr_icon = "mdi:brightness-6"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the brightness percentage."""
        return round(self.coordinator.data.brightness_percentage, 1)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "brightness_raw": self.coordinator.data.brightness,
            "brightness_max": 255,
        }


class AndroidTVNetworkSensor(AndroidTVBaseSensor):
    """Sensor for network information."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the network sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_network"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Network"
        self._attr_icon = "mdi:network"
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the network status."""
        if self.coordinator.data.wifi_enabled:
            return "Connected" if self.coordinator.data.wifi_ssid else "Enabled"
        return "Disabled"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "wifi_enabled": self.coordinator.data.wifi_enabled,
            "ssid": self.coordinator.data.wifi_ssid,
            "ip_address": self.coordinator.data.ip_address,
        }


class AndroidTVAppSensor(AndroidTVBaseSensor):
    """Sensor for current app information."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the app sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_app"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Current App"
        self._attr_icon = "mdi:application"
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the current app name."""
        return self.coordinator.data.current_app_name or "Unknown"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "package_name": self.coordinator.data.current_app_package,
            "activity": self.coordinator.data.current_activity,
            "installed_apps_count": len(self.coordinator.data.installed_apps),
        }


class AndroidTVCPUSensor(AndroidTVBaseSensor):
    """Sensor for system CPU usage."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the CPU sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cpu"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} CPU Usage"
        self._attr_icon = "mdi:cpu-64-bit"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the CPU usage percentage."""
        return round(self.coordinator.data.cpu_usage, 1)


class AndroidTVMemorySensor(AndroidTVBaseSensor):
    """Sensor for system memory usage."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the memory sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_memory_usage"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Memory Usage"
        self._attr_icon = "mdi:memory"
        self._attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Avoid HA auto-converting data_size units; we want to display GB
        self._attr_device_class = None
        self._attr_suggested_display_precision = 2
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the memory usage in MB."""
        # memory_usage is tracked in MB; convert to GB for display
        if self.coordinator.data.memory_usage > 0:
            return round(self.coordinator.data.memory_usage / 1024.0, 2)
        return None


class AndroidTVISGStatusSensor(AndroidTVBaseSensor):
    """Sensor for ISG application status."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the ISG status sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_isg_status"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} ISG Status"
        self._attr_icon = "mdi:application-cog"
    
    @property
    def native_value(self) -> str:
        """Return the ISG status."""
        if not self.coordinator.data.isg_running:
            return ISG_HEALTH_NOT_RUNNING
        return self.coordinator.data.isg_health_status
    
    @property
    def icon(self) -> str:
        """Return icon based on status."""
        if self.coordinator.data.isg_health_status == ISG_HEALTH_HEALTHY:
            return "mdi:check-circle"
        elif self.coordinator.data.isg_health_status == ISG_HEALTH_NOT_RUNNING:
            return "mdi:stop-circle"
        else:
            return "mdi:alert-circle"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "is_running": self.coordinator.data.isg_running,
            "pid": self.coordinator.data.isg_pid,
            "last_start_time": self.coordinator.data.isg_last_start_time,
            "last_health_check": self.coordinator.data.isg_last_health_check,
            "restart_count": self.coordinator.data.isg_restart_count,
        }


class AndroidTVISGMemorySensor(AndroidTVBaseSensor):
    """Sensor for ISG memory usage."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the ISG memory sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_isg_memory"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} ISG Memory"
        self._attr_icon = "mdi:memory"
        self._attr_native_unit_of_measurement = UnitOfInformation.MEGABYTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the ISG memory usage in MB."""
        return round(self.coordinator.data.isg_memory_usage_mb, 1)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "memory_percentage": round(self.coordinator.data.isg_memory_percentage, 1),
        }


# Removed AndroidTVISGCPUSensor per user request


class AndroidTVISGUptimeSensor(AndroidTVBaseSensor):
    """Sensor for ISG uptime."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the ISG uptime sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_isg_uptime"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} ISG Uptime"
        self._attr_icon = "mdi:timer"
        self._attr_native_unit_of_measurement = "minutes"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
    
    @property
    def native_value(self) -> Optional[int]:
        """Return the ISG uptime in minutes."""
        return self.coordinator.data.isg_uptime_minutes


class AndroidTVISGCrashCountSensor(AndroidTVBaseSensor):
    """Sensor for ISG crash count."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the ISG crash count sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_isg_crash_count"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} ISG Crash Count"
        self._attr_icon = "mdi:bug"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
    
    @property
    def native_value(self) -> int:
        """Return the ISG crash count."""
        return self.coordinator.data.isg_crash_count
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "last_crash_time": self.coordinator.data.isg_last_crash_time,
            "last_crash_reason": self.coordinator.data.isg_last_crash_reason,
            "anr_count": self.coordinator.data.isg_anr_count,
            "last_anr_time": self.coordinator.data.isg_last_anr_time,
        }
