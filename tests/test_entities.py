"""Tests for entities."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.media_player import MediaPlayerState


class TestMediaPlayerEntity:
    """Test media player entity."""
    
    @pytest.mark.asyncio
    async def test_media_player_initialization(self, mock_coordinator, mock_config_entry):
        """Test media player initialization."""
        from custom_components.android_tv_box.media_player import AndroidTVMediaPlayer
        
        player = AndroidTVMediaPlayer(mock_coordinator, mock_config_entry)
        
        assert player.coordinator == mock_coordinator
        assert player._entry == mock_config_entry
        assert player.unique_id == f"{mock_config_entry.entry_id}_media_player"
    
    @pytest.mark.asyncio
    async def test_media_player_state(self, mock_coordinator, mock_config_entry):
        """Test media player state property."""
        from custom_components.android_tv_box.media_player import AndroidTVMediaPlayer
        
        player = AndroidTVMediaPlayer(mock_coordinator, mock_config_entry)
        
        # Test idle state
        mock_coordinator.data.is_connected = True
        mock_coordinator.data.power_state = "on"
        mock_coordinator.data.media_state = "idle"
        
        assert player.state == MediaPlayerState.IDLE
        
        # Test playing state
        mock_coordinator.data.media_state = "playing"
        assert player.state == MediaPlayerState.PLAYING
        
        # Test off state
        mock_coordinator.data.power_state = "off"
        assert player.state == MediaPlayerState.OFF
    
    @pytest.mark.asyncio
    async def test_media_player_volume(self, mock_coordinator, mock_config_entry):
        """Test media player volume property."""
        from custom_components.android_tv_box.media_player import AndroidTVMediaPlayer
        
        player = AndroidTVMediaPlayer(mock_coordinator, mock_config_entry)
        
        mock_coordinator.data.volume_level = 8
        mock_coordinator.data.volume_max = 15
        
        assert player.volume_level == pytest.approx(0.533, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_media_player_turn_on(self, mock_coordinator, mock_config_entry):
        """Test turning on the media player."""
        from custom_components.android_tv_box.media_player import AndroidTVMediaPlayer
        
        player = AndroidTVMediaPlayer(mock_coordinator, mock_config_entry)
        mock_coordinator.power_control_with_feedback = AsyncMock(return_value=True)
        
        await player.async_turn_on()
        
        mock_coordinator.power_control_with_feedback.assert_called_once_with(True)


class TestSensorEntity:
    """Test sensor entities."""
    
    @pytest.mark.asyncio
    async def test_brightness_sensor(self, mock_coordinator, mock_config_entry):
        """Test brightness sensor."""
        from custom_components.android_tv_box.sensor import AndroidTVBrightnessSensor
        
        sensor = AndroidTVBrightnessSensor(mock_coordinator, mock_config_entry)
        
        mock_coordinator.data.brightness_percentage = 50.2
        
        assert sensor.native_value == 50.2
    
    @pytest.mark.asyncio
    async def test_network_sensor(self, mock_coordinator, mock_config_entry):
        """Test network sensor."""
        from custom_components.android_tv_box.sensor import AndroidTVNetworkSensor
        
        sensor = AndroidTVNetworkSensor(mock_coordinator, mock_config_entry)
        
        mock_coordinator.data.wifi_enabled = True
        mock_coordinator.data.wifi_ssid = "TestNetwork"
        
        assert sensor.native_value == "Connected"
        
        mock_coordinator.data.wifi_ssid = None
        assert sensor.native_value == "Enabled"


class TestSwitchEntity:
    """Test switch entities."""
    
    @pytest.mark.asyncio
    async def test_power_switch(self, mock_coordinator, mock_config_entry):
        """Test power switch."""
        from custom_components.android_tv_box.switch import AndroidTVPowerSwitch
        
        switch = AndroidTVPowerSwitch(mock_coordinator, mock_config_entry)
        
        mock_coordinator.data.power_state = "on"
        assert switch.is_on is True
        
        mock_coordinator.data.power_state = "off"
        assert switch.is_on is False
    
    @pytest.mark.asyncio
    async def test_power_switch_turn_on(self, mock_coordinator, mock_config_entry):
        """Test turning on power switch."""
        from custom_components.android_tv_box.switch import AndroidTVPowerSwitch
        
        switch = AndroidTVPowerSwitch(mock_coordinator, mock_config_entry)
        mock_coordinator.power_control_with_feedback = AsyncMock(return_value=True)
        
        await switch.async_turn_on()
        
        mock_coordinator.power_control_with_feedback.assert_called_once_with(True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

