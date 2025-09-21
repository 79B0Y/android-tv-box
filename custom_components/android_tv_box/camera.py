"""Camera entity for Android TV Box Integration."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.camera import Camera
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
    """Set up Android TV Box camera."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    # Deduplicate
    er = er_async_get(hass)
    unique_id = f"{entry.entry_id}_screenshot"
    existing = er.async_get_entity_id("camera", DOMAIN, unique_id)
    if existing:
        _LOGGER.debug("Camera already exists: %s - skipping duplicate", existing)
        return

    async_add_entities([AndroidTVScreenshotCamera(coordinator, entry)], True)


class AndroidTVScreenshotCamera(CoordinatorEntity[AndroidTVUpdateCoordinator], Camera):
    """Camera entity for device screenshots."""
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_screenshot"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Screenshot"
        self._attr_icon = "mdi:camera"
    
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
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "screenshot_timestamp": self.coordinator.data.screenshot_timestamp,
            "screenshot_path": self.coordinator.data.screenshot_path,
        }
    
    async def async_camera_image(
        self, width: Optional[int] = None, height: Optional[int] = None
    ) -> Optional[bytes]:
        """Return a still image response from the camera."""
        # Take a new screenshot
        success = await self.coordinator.take_screenshot_with_feedback()
        
        if success and self.coordinator.data.screenshot_data:
            return self.coordinator.data.screenshot_data
        
        _LOGGER.error("Failed to capture screenshot")
        return None
    
    @property
    def motion_detection_enabled(self) -> bool:
        """Return the camera motion detection status."""
        return False
    
    @property
    def brand(self) -> Optional[str]:
        """Return the camera brand."""
        return self.coordinator.data.device_manufacturer
    
    @property
    def model(self) -> Optional[str]:
        """Return the camera model."""
        return self.coordinator.data.device_model
