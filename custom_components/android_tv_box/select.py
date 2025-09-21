"""Select entities for Android TV Box Integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_APPS, CONF_VISIBLE_APPS, DOMAIN
from .coordinator import AndroidTVUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Android TV Box select entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    entities = [
        AndroidTVAppSelector(coordinator, entry),
    ]
    
    async_add_entities(entities, True)


class AndroidTVAppSelector(CoordinatorEntity[AndroidTVUpdateCoordinator], SelectEntity):
    """Select entity for app launcher."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the app selector."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_app_selector"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} App Selector"
        self._attr_icon = "mdi:application"
        
        # Get configured apps
        self._configured_apps = entry.data.get(CONF_APPS, {})
        self._visible_apps = entry.data.get(CONF_VISIBLE_APPS, list(self._configured_apps.keys()))
        self._attr_options = self._visible_apps
    
    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self.coordinator.adb_manager.host}_{self.coordinator.adb_manager.port}")},
            "name": self._entry.data.get("device_name", "Android TV Box"),
            "manufacturer": self.coordinator.data.device_manufacturer or "Android",
            "model": self.coordinator.data.device_model or "TV Box",
            "sw_version": self.coordinator.data.android_version,
            "via_device": (DOMAIN, f"{self.coordinator.adb_manager.host}_{self.coordinator.adb_manager.port}"),
        }
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data.is_connected
    
    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        current_app_name = self.coordinator.data.current_app_name
        if current_app_name and current_app_name in self._visible_apps:
            return current_app_name
        return None
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "current_package": self.coordinator.data.current_app_package,
            "current_activity": self.coordinator.data.current_activity,
            "configured_apps": self._configured_apps,
            "visible_apps": self._visible_apps,
        }
    
    async def async_select_option(self, option: str) -> None:
        """Select an app to launch."""
        package_name = self._configured_apps.get(option)
        if package_name:
            success = await self.coordinator.start_app_with_feedback(package_name)
            if not success:
                _LOGGER.error("Failed to start app: %s", option)
        else:
            _LOGGER.error("Unknown app option: %s", option)