"""Switch entities for Android TV Box Integration."""
import asyncio
import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, IMMEDIATE_FEEDBACK_TIMINGS, POWER_STATE_ON
from .coordinator import AndroidTVUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Android TV Box switches."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    entities = [
        AndroidTVPowerSwitch(coordinator, entry),
        AndroidTVWiFiSwitch(coordinator, entry),
        AndroidTVADBSwitch(coordinator, entry),
    ]
    
    async_add_entities(entities, True)


class AndroidTVBaseSwitch(CoordinatorEntity[AndroidTVUpdateCoordinator], SwitchEntity):
    """Base class for Android TV switches."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
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


class AndroidTVPowerSwitch(AndroidTVBaseSwitch):
    """Switch to control Android TV power state."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the power switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_power"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Power"
        self._attr_icon = "mdi:power"
    
    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.coordinator.data.power_state == POWER_STATE_ON
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "wakefulness": self.coordinator.data.wakefulness,
            "screen_on": self.coordinator.data.screen_on,
            "power_state": self.coordinator.data.power_state,
        }
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the device."""
        success = await self.coordinator.power_control_with_feedback(True)
        if not success:
            _LOGGER.error("Failed to turn on device")
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the device."""
        success = await self.coordinator.power_control_with_feedback(False)
        if not success:
            _LOGGER.error("Failed to turn off device")


class AndroidTVWiFiSwitch(AndroidTVBaseSwitch):
    """Switch to control Android TV WiFi state."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the WiFi switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_wifi"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} WiFi"
        self._attr_icon = "mdi:wifi"
    
    @property
    def is_on(self) -> bool:
        """Return True if WiFi is enabled."""
        return self.coordinator.data.wifi_enabled
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "ssid": self.coordinator.data.wifi_ssid,
            "ip_address": self.coordinator.data.ip_address,
        }
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on WiFi."""
        # WiFi control would need additional ADB commands
        _LOGGER.warning("WiFi control not implemented yet")
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off WiFi."""
        # WiFi control would need additional ADB commands
        _LOGGER.warning("WiFi control not implemented yet")


class AndroidTVADBSwitch(AndroidTVBaseSwitch):
    """Switch to show ADB connection state."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the ADB switch."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_adb"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} ADB Connection"
        self._attr_icon = "mdi:console-network"
    
    @property
    def is_on(self) -> bool:
        """Return True if ADB is connected."""
        return self.coordinator.data.is_connected
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "host": self.coordinator.adb_manager.host,
            "port": self.coordinator.adb_manager.port,
            "last_seen": self.coordinator.data.last_seen,
            "connection_error": self.coordinator.data.connection_error,
        }
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Reconnect ADB."""
        success = await self.coordinator.adb_manager.connect()
        if success:
            self.coordinator.data.is_connected = True
            self.coordinator.data.connection_error = None
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to reconnect ADB")
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disconnect ADB."""
        await self.coordinator.adb_manager.disconnect()
        self.coordinator.data.is_connected = False
        self.async_write_ha_state()