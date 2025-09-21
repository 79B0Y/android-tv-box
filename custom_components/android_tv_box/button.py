"""Button entities for Android TV Box Integration."""
import logging
from typing import Any, Dict

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AndroidTVUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Android TV Box buttons."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    entities = [
        AndroidTVNavigationButton(coordinator, entry, "up", "Navigate Up", "mdi:arrow-up"),
        AndroidTVNavigationButton(coordinator, entry, "down", "Navigate Down", "mdi:arrow-down"),
        AndroidTVNavigationButton(coordinator, entry, "left", "Navigate Left", "mdi:arrow-left"),
        AndroidTVNavigationButton(coordinator, entry, "right", "Navigate Right", "mdi:arrow-right"),
        AndroidTVNavigationButton(coordinator, entry, "center", "Navigate Center", "mdi:checkbox-blank-circle"),
        AndroidTVNavigationButton(coordinator, entry, "back", "Navigate Back", "mdi:arrow-left-bold"),
        AndroidTVNavigationButton(coordinator, entry, "home", "Navigate Home", "mdi:home"),
        AndroidTVNavigationButton(coordinator, entry, "menu", "Navigate Menu", "mdi:menu"),
        AndroidTVRefreshAppsButton(coordinator, entry),
        AndroidTVRestartISGButton(coordinator, entry),
        AndroidTVClearISGCacheButton(coordinator, entry),
        AndroidTVISGHealthCheckButton(coordinator, entry),
    ]
    
    async_add_entities(entities, True)


class AndroidTVBaseButton(CoordinatorEntity[AndroidTVUpdateCoordinator], ButtonEntity):
    """Base class for Android TV buttons."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
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
            "via_device": (DOMAIN, f"{self.coordinator.adb_manager.host}_{self.coordinator.adb_manager.port}"),
        }
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data.is_connected


class AndroidTVNavigationButton(AndroidTVBaseButton):
    """Button for navigation commands."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry, direction: str, name: str, icon: str) -> None:
        """Initialize the navigation button."""
        super().__init__(coordinator, entry)
        self._direction = direction
        self._attr_unique_id = f"{entry.entry_id}_nav_{direction}"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} {name}"
        self._attr_icon = icon
    
    async def async_press(self) -> None:
        """Handle the button press."""
        method_name = f"nav_{self._direction}"
        if hasattr(self.coordinator.adb_manager, method_name):
            method = getattr(self.coordinator.adb_manager, method_name)
            success = await method()
            if not success:
                _LOGGER.error("Failed to execute navigation command: %s", self._direction)
        else:
            _LOGGER.error("Unknown navigation command: %s", self._direction)


class AndroidTVRefreshAppsButton(AndroidTVBaseButton):
    """Button to refresh installed apps list."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the refresh apps button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_refresh_apps"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Refresh Apps"
        self._attr_icon = "mdi:refresh"
    
    async def async_press(self) -> None:
        """Refresh installed apps list."""
        try:
            installed_apps = await self.coordinator.adb_manager.get_installed_apps()
            self.coordinator.data.installed_apps = installed_apps
            self.coordinator.async_update_listeners()
            _LOGGER.info("Refreshed apps list: %d apps found", len(installed_apps))
        except Exception as e:
            _LOGGER.error("Failed to refresh apps list: %s", e)


class AndroidTVRestartISGButton(AndroidTVBaseButton):
    """Button to restart ISG application."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the restart ISG button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_restart_isg"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Restart ISG"
        self._attr_icon = "mdi:restart"
    
    async def async_press(self) -> None:
        """Restart ISG application."""
        success = await self.coordinator.restart_isg_with_feedback()
        if not success:
            _LOGGER.error("Failed to restart ISG application")


class AndroidTVClearISGCacheButton(AndroidTVBaseButton):
    """Button to clear ISG cache."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the clear ISG cache button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_clear_isg_cache"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Clear ISG Cache"
        self._attr_icon = "mdi:delete"
    
    async def async_press(self) -> None:
        """Clear ISG cache and restart."""
        success = await self.coordinator.clear_isg_cache_with_feedback()
        if not success:
            _LOGGER.error("Failed to clear ISG cache")


class AndroidTVISGHealthCheckButton(AndroidTVBaseButton):
    """Button to perform ISG health check."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the ISG health check button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_isg_health_check"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} ISG Health Check"
        self._attr_icon = "mdi:heart-pulse"
    
    async def async_press(self) -> None:
        """Perform ISG health check."""
        try:
            health_data = await self.coordinator.adb_manager.perform_isg_health_check()
            self.coordinator.data.update_isg_health(health_data)
            self.coordinator.async_update_listeners()
            _LOGGER.info("ISG health check completed: %s", health_data.get("health_status"))
        except Exception as e:
            _LOGGER.error("Failed to perform ISG health check: %s", e)