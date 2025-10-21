"""Media Player entity for Android TV Box Integration."""
import asyncio
import logging
import re
from typing import Any, Dict, Optional

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_registry import async_get as er_async_get

from .const import (
    CONF_APPS,
    CONF_VISIBLE_APPS,
    DOMAIN,
    IMMEDIATE_FEEDBACK_TIMINGS,
    MEDIA_STATE_IDLE,
    MEDIA_STATE_PAUSED,
    MEDIA_STATE_PLAYING,
    POWER_STATE_OFF,
    POWER_STATE_ON,
    POWER_STATE_STANDBY,
)
from .coordinator import AndroidTVUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Android TV Box media player."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    # Deduplicate: skip if entity with same unique_id already exists
    er = er_async_get(hass)
    unique_id = f"{entry.entry_id}_media_player"
    existing = er.async_get_entity_id("media_player", DOMAIN, unique_id)
    if existing:
        _LOGGER.debug("Media player already exists: %s - skipping duplicate", existing)
        return

    async_add_entities([AndroidTVMediaPlayer(coordinator, entry)], True)


class AndroidTVMediaPlayer(CoordinatorEntity[AndroidTVUpdateCoordinator], MediaPlayerEntity):
    """Android TV Box Media Player entity."""
    
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.BROWSE_MEDIA
    )
    
    def __init__(self, coordinator: AndroidTVUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_name = f"{entry.data.get('device_name', 'Android TV Box')} Media Player"
        
        # Get configured apps
        self._configured_apps = coordinator.get_config_value(CONF_APPS, {})
        self._visible_apps = coordinator.get_config_value(CONF_VISIBLE_APPS, list(self._configured_apps.keys()))
    
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
    def state(self) -> MediaPlayerState:
        """Return the state of the media player."""
        if not self.coordinator.data.is_connected:
            return MediaPlayerState.OFF
        
        power_state = self.coordinator.data.power_state
        if power_state == POWER_STATE_OFF:
            return MediaPlayerState.OFF
        elif power_state == POWER_STATE_STANDBY:
            return MediaPlayerState.STANDBY
        
        # Map media state to MediaPlayerState
        media_state = self.coordinator.data.media_state
        if media_state == MEDIA_STATE_PLAYING:
            return MediaPlayerState.PLAYING
        elif media_state == MEDIA_STATE_PAUSED:
            return MediaPlayerState.PAUSED
        elif media_state == MEDIA_STATE_IDLE:
            return MediaPlayerState.IDLE
        
        return MediaPlayerState.ON
    
    @property
    def volume_level(self) -> Optional[float]:
        """Volume level of the media player (0..1)."""
        if self.coordinator.data.volume_max > 0:
            return self.coordinator.data.volume_level / self.coordinator.data.volume_max
        return None
    
    @property
    def is_volume_muted(self) -> Optional[bool]:
        """Boolean if volume is currently muted."""
        return self.coordinator.data.is_muted
    
    @property
    def media_title(self) -> Optional[str]:
        """Title of current playing media."""
        if self.coordinator.data.current_app_name:
            return f"Playing on {self.coordinator.data.current_app_name}"
        return None
    
    @property
    def app_name(self) -> Optional[str]:
        """Name of the current running app."""
        return self.coordinator.data.current_app_name
    
    @property
    def source(self) -> Optional[str]:
        """Name of the current input source."""
        return self.coordinator.data.current_app_name
    
    @property
    def source_list(self) -> Optional[list]:
        """List of available input sources."""
        return self._visible_apps
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "device_model": self.coordinator.data.device_model,
            "android_version": self.coordinator.data.android_version,
            "wifi_ssid": self.coordinator.data.wifi_ssid,
            "ip_address": self.coordinator.data.ip_address,
            "current_activity": self.coordinator.data.current_activity,
            "volume_percentage": round(self.coordinator.data.volume_percentage, 1),
            "brightness": self.coordinator.data.brightness,
            "brightness_percentage": round(self.coordinator.data.brightness_percentage, 1),
            "cast_active": self.coordinator.data.cast_active,
            "isg_running": self.coordinator.data.isg_running,
            "isg_health": self.coordinator.data.isg_health_status,
        }
    
    # Control methods
    async def async_turn_on(self) -> None:
        """Turn on the device."""
        success = await self.coordinator.power_control_with_feedback(True)
        if not success:
            _LOGGER.error("Failed to turn on device")
    
    async def async_turn_off(self) -> None:
        """Turn off the device."""
        success = await self.coordinator.power_control_with_feedback(False)
        if not success:
            _LOGGER.error("Failed to turn off device")
    
    async def async_media_play(self) -> None:
        """Send play command."""
        success = await self.coordinator.adb_manager.media_play()
        if success:
            await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["media_play"])
            self.coordinator.data.media_state = await self.coordinator.adb_manager.get_media_state()
            self.async_write_ha_state()
    
    async def async_media_pause(self) -> None:
        """Send pause command."""
        success = await self.coordinator.adb_manager.media_pause()
        if success:
            await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["media_pause"])
            self.coordinator.data.media_state = await self.coordinator.adb_manager.get_media_state()
            self.async_write_ha_state()
    
    async def async_media_stop(self) -> None:
        """Send stop command."""
        success = await self.coordinator.adb_manager.media_stop()
        if success:
            await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["media_stop"])
            self.coordinator.data.media_state = await self.coordinator.adb_manager.get_media_state()
            self.async_write_ha_state()
    
    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        success = await self.coordinator.adb_manager.media_previous()
        if not success:
            _LOGGER.error("Failed to send previous track command")
    
    async def async_media_next_track(self) -> None:
        """Send next track command."""
        success = await self.coordinator.adb_manager.media_next()
        if not success:
            _LOGGER.error("Failed to send next track command")
    
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        success = await self.coordinator.set_volume_with_feedback(volume)
        if not success:
            _LOGGER.error("Failed to set volume to %s", volume)
    
    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        success = await self.coordinator.adb_manager.volume_up()
        if success:
            await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["volume"])
            current, max_vol, is_muted = await self.coordinator.adb_manager.get_volume_state()
            self.coordinator.data.update_volume_state(current, max_vol, is_muted)
            self.async_write_ha_state()
    
    async def async_volume_down(self) -> None:
        """Volume down the media player."""
        success = await self.coordinator.adb_manager.volume_down()
        if success:
            await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["volume"])
            current, max_vol, is_muted = await self.coordinator.adb_manager.get_volume_state()
            self.coordinator.data.update_volume_state(current, max_vol, is_muted)
            self.async_write_ha_state()
    
    async def async_mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        success = await self.coordinator.adb_manager.volume_mute()
        if success:
            await asyncio.sleep(IMMEDIATE_FEEDBACK_TIMINGS["mute"])
            current, max_vol, is_muted = await self.coordinator.adb_manager.get_volume_state()
            self.coordinator.data.update_volume_state(current, max_vol, is_muted)
            self.async_write_ha_state()
    
    async def async_select_source(self, source: str) -> None:
        """Select input source (app)."""
        package_name = self._configured_apps.get(source)
        if package_name:
            success = await self.coordinator.start_app_with_feedback(package_name)
            if not success:
                _LOGGER.error("Failed to start app: %s", source)
        else:
            _LOGGER.error("Unknown app source: %s", source)
    
    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """Play a piece of media."""
        if media_type == "youtube":
            # Handle YouTube video IDs or URLs
            video_id = self._extract_youtube_id(media_id)
            if video_id:
                success = await self.coordinator.adb_manager.cast_youtube_video(video_id)
                if not success:
                    _LOGGER.error("Failed to cast YouTube video: %s", media_id)
            else:
                _LOGGER.error("Invalid YouTube video ID or URL: %s", media_id)
        
        elif media_type == "netflix":
            # Handle Netflix video IDs
            success = await self.coordinator.adb_manager.cast_netflix_video(media_id)
            if not success:
                _LOGGER.error("Failed to cast Netflix video: %s", media_id)
        
        elif media_type == "spotify":
            # Handle Spotify track IDs
            success = await self.coordinator.adb_manager.cast_spotify_track(media_id)
            if not success:
                _LOGGER.error("Failed to cast Spotify track: %s", media_id)
        
        elif media_type in ["video", "audio", "image", "url"]:
            # Handle generic media URLs
            success = await self.coordinator.adb_manager.cast_media_url(media_id)
            if not success:
                _LOGGER.error("Failed to cast media URL: %s", media_id)
        
        elif media_type == "app":
            # Handle app launching
            await self.async_select_source(media_id)
        
        else:
            _LOGGER.error("Unsupported media type: %s", media_type)
    
    def _extract_youtube_id(self, url_or_id: str) -> Optional[str]:
        """Extract YouTube video ID from URL or return ID if already an ID."""
        # If it's already a video ID (11 characters, alphanumeric)
        if len(url_or_id) == 11 and url_or_id.isalnum():
            return url_or_id
        
        # Extract from various YouTube URL formats
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/v/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        return None
    
    async def async_browse_media(self, media_content_type: str = None, media_content_id: str = None):
        """Implement the browse media feature."""
        from homeassistant.components.media_player.browse_media import (
            BrowseMedia,
            MediaClass,
            MediaType,
        )
        
        if media_content_id is None:
            # Root level - show apps
            children = []
            for app_name in self._visible_apps:
                children.append(
                    BrowseMedia(
                        title=app_name,
                        media_class=MediaClass.APP,
                        media_content_type="app",
                        media_content_id=app_name,
                        can_play=True,
                        can_expand=False,
                    )
                )
            
            return BrowseMedia(
                title="Apps",
                media_class=MediaClass.DIRECTORY,
                media_content_type="apps",
                media_content_id="apps",
                can_play=False,
                can_expand=True,
                children=children,
            )
        
        # If specific content requested, return empty (could be expanded for app-specific browsing)
        return None
