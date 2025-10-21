"""Tests for Android TV Update Coordinator."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from custom_components.android_tv_box.coordinator import (
    AndroidTVState,
    AndroidTVUpdateCoordinator,
)


class TestAndroidTVState:
    """Test AndroidTVState dataclass."""
    
    def test_state_initialization(self):
        """Test state initialization with defaults."""
        state = AndroidTVState()
        assert state.is_connected is False
        assert state.power_state == "off"
        assert state.media_state == "idle"
        assert state.volume_level == 0
        assert state.brightness == 128
    
    def test_update_power_state(self):
        """Test power state update."""
        state = AndroidTVState()
        
        state.update_power_state("Awake", True)
        assert state.wakefulness == "Awake"
        assert state.screen_on is True
        assert state.power_state == "on"
        
        state.update_power_state("Asleep", False)
        assert state.power_state == "off"
    
    def test_update_volume_state(self):
        """Test volume state update."""
        state = AndroidTVState()
        
        state.update_volume_state(8, 15, False)
        assert state.volume_level == 8
        assert state.volume_max == 15
        assert state.is_muted is False
        assert state.volume_percentage == pytest.approx(53.33, rel=0.1)
    
    def test_update_brightness_state(self):
        """Test brightness state update."""
        state = AndroidTVState()
        
        state.update_brightness_state(128)
        assert state.brightness == 128
        assert state.brightness_percentage == pytest.approx(50.2, rel=0.1)
    
    def test_update_wifi_state(self):
        """Test WiFi state update."""
        state = AndroidTVState()
        
        state.update_wifi_state(True, "TestNetwork", "192.168.1.100")
        assert state.wifi_enabled is True
        assert state.wifi_ssid == "TestNetwork"
        assert state.ip_address == "192.168.1.100"


class TestAndroidTVUpdateCoordinator:
    """Test AndroidTVUpdateCoordinator class."""
    
    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, mock_adb_manager):
        """Test coordinator initialization."""
        from homeassistant.core import HomeAssistant
        
        hass = MagicMock(spec=HomeAssistant)
        config = {
            "isg_monitoring": True,
            "isg_auto_restart": True,
            "isg_memory_threshold": 85,
            "isg_cpu_threshold": 95,
        }
        
        coordinator = AndroidTVUpdateCoordinator(hass, mock_adb_manager, config)
        
        assert coordinator.adb_manager == mock_adb_manager
        assert coordinator.config == config
        assert coordinator._isg_monitoring_enabled is True
        assert coordinator._isg_auto_restart_enabled is True
    
    @pytest.mark.asyncio
    async def test_ensure_connection(self, mock_adb_manager):
        """Test connection ensuring."""
        from homeassistant.core import HomeAssistant
        
        hass = MagicMock(spec=HomeAssistant)
        coordinator = AndroidTVUpdateCoordinator(hass, mock_adb_manager, {})
        
        mock_adb_manager.is_connected.return_value = True
        
        connected = await coordinator._ensure_connection()
        assert connected is True
        
        mock_adb_manager.is_connected.return_value = False
        mock_adb_manager.connect.return_value = True
        
        connected = await coordinator._ensure_connection()
        assert connected is True
        mock_adb_manager.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_basic_status(self, mock_adb_manager):
        """Test basic status update."""
        from homeassistant.core import HomeAssistant
        
        hass = MagicMock(spec=HomeAssistant)
        coordinator = AndroidTVUpdateCoordinator(hass, mock_adb_manager, {})
        
        await coordinator._update_basic_status(datetime.now())
        
        assert coordinator.data.power_state == "on"
        assert coordinator.data.media_state == "idle"
        assert coordinator.data.volume_level == 8
        assert coordinator.data.volume_max == 15
    
    @pytest.mark.asyncio
    async def test_should_restart_isg(self, mock_adb_manager):
        """Test ISG restart decision logic."""
        from homeassistant.core import HomeAssistant
        
        hass = MagicMock(spec=HomeAssistant)
        coordinator = AndroidTVUpdateCoordinator(hass, mock_adb_manager, {
            "isg_auto_restart": True,
            "isg_memory_threshold": 80,
            "isg_cpu_threshold": 90,
        })
        
        # Should restart if not running
        coordinator.data.isg_running = False
        assert coordinator._should_restart_isg() is True
        
        # Should not restart if too many attempts
        coordinator.data.isg_running = False
        coordinator.data.isg_restart_count = 5
        assert coordinator._should_restart_isg() is False
        
        # Should restart if unhealthy and high resource usage
        coordinator.data.isg_restart_count = 0
        coordinator.data.isg_running = True
        coordinator.data.isg_health_status = "unhealthy"
        coordinator.data.isg_memory_percentage = 85
        assert coordinator._should_restart_isg() is True
    
    @pytest.mark.asyncio
    async def test_set_volume_with_feedback(self, mock_adb_manager):
        """Test volume setting with feedback."""
        from homeassistant.core import HomeAssistant
        
        hass = MagicMock(spec=HomeAssistant)
        coordinator = AndroidTVUpdateCoordinator(hass, mock_adb_manager, {})
        coordinator.async_update_listeners = MagicMock()
        
        mock_adb_manager.set_volume.return_value = True
        mock_adb_manager.get_volume_state.return_value = (10, 15, False)
        
        success = await coordinator.set_volume_with_feedback(0.67)
        
        assert success is True
        assert coordinator.data.volume_level == 10
        coordinator.async_update_listeners.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

