import asyncio
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

DOMAIN = "android_tv_box"
CONF_DEVICE_NAME = "device_name"
CONF_SCREENSHOT_PATH = "screenshot_path"

DEFAULT_PORT = 5555
DEFAULT_DEVICE_NAME = "Android TV Box"
DEFAULT_SCREENSHOT_PATH = "/sdcard/isgbackup/screenshot/"

_LOGGER = logging.getLogger(__name__)
_LOGGER.warning("Android TV Box config_flow loaded: TEST-2025-09-21")

STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): cv.string,
    vol.Optional(CONF_SCREENSHOT_PATH, default=DEFAULT_SCREENSHOT_PATH): cv.string,
})

async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"title": data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)}

class AndroidTVBoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)

        info = await validate_input(self.hass, user_input)
        return self.async_create_entry(title=info["title"], data=user_input)
