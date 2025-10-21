"""Pytest fixtures for Android TV Box Integration tests."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest.fixture
def mock_adb_device():
    """Mock ADB device."""
    device = MagicMock()
    device.connect = MagicMock(return_value=True)
    device.shell = MagicMock(return_value="test output")
    device.close = MagicMock()
    return device


@pytest.fixture
def mock_adb_manager():
    """Mock ADB Manager."""
    manager = AsyncMock()
    manager.host = "192.168.1.100"
    manager.port = 5555
    manager.connect = AsyncMock(return_value=True)
    manager.disconnect = AsyncMock()
    manager.is_connected = AsyncMock(return_value=True)
    manager.execute_command = AsyncMock()
    manager.get_device_info = AsyncMock(return_value={
        "model": "Test Device",
        "manufacturer": "Test Manufacturer",
        "android_version": "11",
        "api_level": "30",
        "serial": "test123",
    })
    manager.get_power_state = AsyncMock(return_value=("Awake", True))
    manager.get_media_state = AsyncMock(return_value="idle")
    manager.get_volume_state = AsyncMock(return_value=(8, 15, False))
    manager.get_brightness = AsyncMock(return_value=128)
    manager.get_wifi_state = AsyncMock(return_value=(True, "TestSSID", "192.168.1.100"))
    manager.get_current_activity = AsyncMock(return_value="com.test.app/.MainActivity")
    manager.get_installed_apps = AsyncMock(return_value=["com.test.app1", "com.test.app2"])
    
    # ISG monitoring methods
    manager.check_isg_process_status = AsyncMock(return_value=True)
    manager.get_isg_memory_usage = AsyncMock(return_value=(256.0, 25.0))
    manager.get_isg_cpu_usage = AsyncMock(return_value=15.0)
    manager.perform_isg_health_check = AsyncMock(return_value={
        "health_status": "healthy",
        "is_running": True,
        "memory_usage": 256.0,
        "cpu_usage": 15.0,
        "crash_detected": False,
        "anr_detected": False,
    })
    
    # Control methods
    manager.power_on = AsyncMock(return_value=True)
    manager.power_off = AsyncMock(return_value=True)
    manager.media_play = AsyncMock(return_value=True)
    manager.media_pause = AsyncMock(return_value=True)
    manager.media_stop = AsyncMock(return_value=True)
    manager.volume_up = AsyncMock(return_value=True)
    manager.volume_down = AsyncMock(return_value=True)
    manager.volume_mute = AsyncMock(return_value=True)
    manager.set_volume = AsyncMock(return_value=True)
    manager.set_brightness = AsyncMock(return_value=True)
    manager.start_app = AsyncMock(return_value=True)
    
    return manager


@pytest.fixture
async def hass_instance():
    """Create a Home Assistant instance for testing."""
    hass = HomeAssistant()
    await hass.async_start()
    yield hass
    await hass.async_stop()


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    from homeassistant.config_entries import ConfigEntry
    
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "host": "192.168.1.100",
        "port": 5555,
        "device_name": "Test Android TV",
    }
    entry.options = {
        "screenshot_path": "/sdcard/isgbackup/screenshot/",
        "screenshot_keep_count": 3,
        "update_interval": 60,
        "isg_monitoring": True,
        "isg_auto_restart": True,
        "isg_memory_threshold": 80,
        "isg_cpu_threshold": 90,
        "apps": {
            "YouTube": "com.google.android.youtube",
            "Netflix": "com.netflix.mediaclient",
        },
        "visible_apps": ["YouTube", "Netflix"],
    }
    entry.version = 1
    return entry


@pytest.fixture
def mock_coordinator(mock_adb_manager):
    """Create a mock coordinator."""
    from custom_components.android_tv_box.coordinator import AndroidTVState
    
    coordinator = MagicMock()
    coordinator.adb_manager = mock_adb_manager
    coordinator.data = AndroidTVState()
    coordinator.data.is_connected = True
    coordinator.data.power_state = "on"
    coordinator.data.screen_on = True
    coordinator.data.media_state = "idle"
    coordinator.data.volume_level = 8
    coordinator.data.volume_max = 15
    coordinator.data.is_muted = False
    coordinator.data.brightness = 128
    coordinator.data.wifi_enabled = True
    coordinator.data.wifi_ssid = "TestSSID"
    coordinator.data.ip_address = "192.168.1.100"
    coordinator.data.device_model = "Test Device"
    coordinator.data.device_manufacturer = "Test Manufacturer"
    coordinator.data.android_version = "11"
    
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_update_listeners = MagicMock()
    coordinator.get_config_value = MagicMock(side_effect=lambda key, default=None: {
        "apps": {"YouTube": "com.google.android.youtube", "Netflix": "com.netflix.mediaclient"},
        "visible_apps": ["YouTube", "Netflix"],
    }.get(key, default))
    
    return coordinator

