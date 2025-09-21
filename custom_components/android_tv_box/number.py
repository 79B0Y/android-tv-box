"""Number entities for Android TV Box Integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_registry import async_get as er_async_get

from .const import DOMAIN
from .coordinator import AndroidTVUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Android TV Box number entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    # Deduplicate
    er = er_async_get(hass)
    unique_id = f"{entry.entry_id}_brightness_control"
    existing = er.async_get_entity_id("number", DOMAIN, unique_id)
    if existing:
        _LOGGER.debug("Number already exists: %s - skipping duplicate", existing)
        return

    async_add_entities([AndroidTVBrightnessControl(coordinator, entry)], True)


class AndroidTVBrightnessControl(CoordinatorEntity[AndroidTVUpdateCoordinator], NumberEntity):
    """Number entity for brightness control."""
    
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 255
    _attr_native_step = 1
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the brightness control."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_brightness_control"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Brightness Control"
        self._attr_icon = "mdi:brightness-6"
    
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
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the current brightness value."""
        return float(self.coordinator.data.brightness)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "brightness_percentage": round(self.coordinator.data.brightness_percentage, 1),
        }
    
    async def async_set_native_value(self, value: float) -> None:
        """Set the brightness value."""
        brightness_level = int(value)
        success = await self.coordinator.set_brightness_with_feedback(brightness_level)
        if not success:
            _LOGGER.error("Failed to set brightness to %s", brightness_level)
