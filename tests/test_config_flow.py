"""Tests for Config Flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType

from custom_components.android_tv_box.const import DOMAIN


@pytest.mark.asyncio
async def test_user_form_display():
    """Test that the user form is displayed."""
    from custom_components.android_tv_box.config_flow import AndroidTVBoxConfigFlow
    
    flow = AndroidTVBoxConfigFlow()
    flow.hass = MagicMock()
    
    result = await flow.async_step_user()
    
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_user_form_validation_success():
    """Test successful validation of user input."""
    from custom_components.android_tv_box.config_flow import validate_input
    
    hass = MagicMock()
    data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 5555,
        "device_name": "Test TV",
    }
    
    with patch("custom_components.android_tv_box.config_flow.asyncio.wait_for") as mock_wait, \
         patch("custom_components.android_tv_box.config_flow.asyncio.open_connection") as mock_conn:
        
        mock_conn.return_value = (AsyncMock(), MagicMock())
        
        result = await validate_input(hass, data)
        
        assert result["title"] == "Test TV"
        assert result["host"] == "192.168.1.100"
        assert result["port"] == 5555


@pytest.mark.asyncio
async def test_user_form_validation_timeout():
    """Test timeout during validation."""
    from custom_components.android_tv_box.config_flow import validate_input
    import asyncio
    
    hass = MagicMock()
    data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 5555,
    }
    
    with patch("custom_components.android_tv_box.config_flow.asyncio.wait_for") as mock_wait, \
         patch("custom_components.android_tv_box.config_flow.asyncio.open_connection") as mock_conn:
        
        mock_wait.side_effect = asyncio.TimeoutError()
        
        with pytest.raises(Exception) as exc_info:
            await validate_input(hass, data)
        
        assert str(exc_info.value) == "timeout"


@pytest.mark.asyncio
async def test_user_form_validation_connection_error():
    """Test connection error during validation."""
    from custom_components.android_tv_box.config_flow import validate_input
    
    hass = MagicMock()
    data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 5555,
    }
    
    with patch("custom_components.android_tv_box.config_flow.asyncio.wait_for") as mock_wait, \
         patch("custom_components.android_tv_box.config_flow.asyncio.open_connection") as mock_conn:
        
        mock_conn.side_effect = ConnectionRefusedError()
        
        with pytest.raises(Exception) as exc_info:
            await validate_input(hass, data)
        
        assert str(exc_info.value) == "cannot_connect"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

