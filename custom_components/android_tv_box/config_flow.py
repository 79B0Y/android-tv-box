"""Config flow for Android TV Box Integration."""
import asyncio
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .adb_manager import ADBManager
from .const import (
    CONF_APPS,
    CONF_DEVICE_NAME,
    CONF_ISG_AUTO_RESTART,
    CONF_ISG_CPU_THRESHOLD,
    CONF_ISG_MEMORY_THRESHOLD,
    CONF_ISG_MONITORING,
    CONF_SCREENSHOT_KEEP_COUNT,
    CONF_SCREENSHOT_PATH,
    CONF_UPDATE_INTERVAL,
    CONF_VISIBLE_APPS,
    DEFAULT_APPS,
    DEFAULT_DEVICE_NAME,
    DEFAULT_ISG_CPU_THRESHOLD,
    DEFAULT_ISG_MEMORY_THRESHOLD,
    DEFAULT_PORT,
    DEFAULT_SCREENSHOT_KEEP_COUNT,
    DEFAULT_SCREENSHOT_PATH,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_TIMEOUT,
    ERROR_UNKNOWN,
)

import logging
_LOGGER = logging.getLogger(__name__)
_LOGGER.warning("Android TV Box config_flow loaded: TEST-2025-09-21")

# ---------- Schemas ----------
# Step 1 (Basic)
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): cv.string,
})

# Advanced options schema (we也在第一步接受这些字段)
STEP_OPTIONS_DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_SCREENSHOT_PATH, default=DEFAULT_SCREENSHOT_PATH): cv.string,
    vol.Optional(CONF_SCREENSHOT_KEEP_COUNT, default=DEFAULT_SCREENSHOT_KEEP_COUNT): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
    vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=30, max=300)),
    vol.Optional(CONF_ISG_MONITORING, default=True): cv.boolean,
    vol.Optional(CONF_ISG_AUTO_RESTART, default=True): cv.boolean,
    vol.Optional(CONF_ISG_MEMORY_THRESHOLD, default=DEFAULT_ISG_MEMORY_THRESHOLD): vol.All(vol.Coerce(int), vol.Range(min=50, max=95)),
    vol.Optional(CONF_ISG_CPU_THRESHOLD, default=DEFAULT_ISG_CPU_THRESHOLD): vol.All(vol.Coerce(int), vol.Range(min=50, max=99)),
})

# 为了避免“extra keys not allowed”，在第一步就把两套 schema 合并展示
STEP_USER_WITH_ADVANCED_SCHEMA = vol.Schema({
    **STEP_USER_DATA_SCHEMA.schema,          # host / port / device_name
    **STEP_OPTIONS_DATA_SCHEMA.schema,       # screenshot / isg_* 等
})


# ---------- Validation ----------
async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    port = data[CONF_PORT]

    adb_manager = ADBManager(host, port)

    try:
        connected = await asyncio.wait_for(adb_manager.connect(), timeout=10)
        if not connected:
            raise Exception("Connection failed")

        device_info = await adb_manager.get_device_info()
        await adb_manager.get_power_state()
        await adb_manager.disconnect()

        return {
            "title": data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME),
            "device_info": device_info,
            "host": host,
            "port": port,
        }

    except asyncio.TimeoutError:
        await adb_manager.disconnect()
        raise Exception(ERROR_TIMEOUT)
    except Exception as e:
        await adb_manager.disconnect()
        _LOGGER.error("Validation failed: %s", e)
        raise Exception(ERROR_CANNOT_CONNECT)


# ---------- Config Flow ----------
class AndroidTVBoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Android TV Box Integration."""

    VERSION = 1

    def __init__(self):
        self._host: Optional[str] = None
        self._port: Optional[int] = None
        self._device_name: Optional[str] = None
        self._device_info: Optional[Dict[str, Any]] = None
        self._errors: Dict[str, str] = {}
        self._pending_options: Dict[str, Any] = {}  # 承接第一步的高级字段

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step (basic connection info + advanced options)."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_WITH_ADVANCED_SCHEMA,
                errors=self._errors,
            )

        errors: Dict[str, str] = {}
        try:
            # 拆分：basic & advanced
            basic_keys = set(STEP_USER_DATA_SCHEMA.schema.keys())
            basic_input = {k: v for k, v in user_input.items() if k in basic_keys}
            advanced_input = {k: v for k, v in user_input.items() if k not in basic_keys}

            info = await validate_input(self.hass, basic_input)

            # 保存基本信息
            self._host = info["host"]
            self._port = info["port"]
            self._device_name = info["title"]
            self._device_info = info["device_info"]

            # 保存本次在第一步填写的高级项，待 apps 步写入 entry.options
            self._pending_options = {
                **{
                    CONF_SCREENSHOT_PATH: advanced_input.get(CONF_SCREENSHOT_PATH, DEFAULT_SCREENSHOT_PATH),
                    CONF_SCREENSHOT_KEEP_COUNT: advanced_input.get(CONF_SCREENSHOT_KEEP_COUNT, DEFAULT_SCREENSHOT_KEEP_COUNT),
                    CONF_UPDATE_INTERVAL: advanced_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    CONF_ISG_MONITORING: advanced_input.get(CONF_ISG_MONITORING, True),
                    CONF_ISG_AUTO_RESTART: advanced_input.get(CONF_ISG_AUTO_RESTART, True),
                    CONF_ISG_MEMORY_THRESHOLD: advanced_input.get(CONF_ISG_MEMORY_THRESHOLD, DEFAULT_ISG_MEMORY_THRESHOLD),
                    CONF_ISG_CPU_THRESHOLD: advanced_input.get(CONF_ISG_CPU_THRESHOLD, DEFAULT_ISG_CPU_THRESHOLD),
                }
            }

            await self.async_set_unique_id(f"{self._host}_{self._port}")
            self._abort_if_unique_id_configured()

            # 进入 app 映射/可见性配置
            return await self.async_step_apps()

        except Exception as e:
            error_code = str(e)
            if error_code in [ERROR_CANNOT_CONNECT, ERROR_TIMEOUT]:
                errors["base"] = error_code
            else:
                errors["base"] = ERROR_UNKNOWN

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_WITH_ADVANCED_SCHEMA,
            errors=errors,
        )

    async def async_step_apps(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle app configuration step."""
        if user_input is None:
            # 动态生成 schema：默认显示 DEFAULT_APPS，并让用户选择可见项
            app_schema = vol.Schema({
                vol.Optional(f"app_{name.lower()}", default=package): cv.string
                for name, package in DEFAULT_APPS.items()
            }).extend({
                vol.Optional("visible_apps", default=list(DEFAULT_APPS.keys())): cv.multi_select(DEFAULT_APPS.keys()),
            })
            return self.async_show_form(
                step_id="apps",
                data_schema=app_schema,
                description_placeholders={"device_name": self._device_name},
            )

        # 收集 App 映射与可见性
        apps_config: Dict[str, str] = {}
        visible_apps = user_input.get("visible_apps", list(DEFAULT_APPS.keys()))
        for name in DEFAULT_APPS.keys():
            app_key = f"app_{name.lower()}"
            if app_key in user_input:
                apps_config[name] = user_input[app_key]
        if not apps_config:
            apps_config = DEFAULT_APPS.copy()

        # entry.data：不可变基础信息
        config_data = {
            CONF_HOST: self._host,
            CONF_PORT: self._port,
            CONF_DEVICE_NAME: self._device_name,
        }

        # entry.options：可变高级配置 + apps
        options_data = {
            **self._pending_options,
            CONF_APPS: apps_config,
            CONF_VISIBLE_APPS: visible_apps,
        }

        return self.async_create_entry(
            title=self._device_name,
            data=config_data,
            options=options_data,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return AndroidTVBoxOptionsFlowHandler(config_entry)


# ---------- Options Flow ----------
class AndroidTVBoxOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Android TV Box Integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # 用 options 覆盖 data（让已保存的可变项正确显示默认值）
        current_config = {**self.config_entry.data, **self.config_entry.options}

        options_schema = vol.Schema({
            vol.Optional(CONF_SCREENSHOT_PATH, default=current_config.get(CONF_SCREENSHOT_PATH, DEFAULT_SCREENSHOT_PATH)): cv.string,
            vol.Optional(CONF_SCREENSHOT_KEEP_COUNT, default=current_config.get(CONF_SCREENSHOT_KEEP_COUNT, DEFAULT_SCREENSHOT_KEEP_COUNT)): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
            vol.Optional(CONF_UPDATE_INTERVAL, default=current_config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=30, max=300)),
            vol.Optional(CONF_ISG_MONITORING, default=current_config.get(CONF_ISG_MONITORING, True)): cv.boolean,
            vol.Optional(CONF_ISG_AUTO_RESTART, default=current_config.get(CONF_ISG_AUTO_RESTART, True)): cv.boolean,
            vol.Optional(CONF_ISG_MEMORY_THRESHOLD, default=current_config.get(CONF_ISG_MEMORY_THRESHOLD, DEFAULT_ISG_MEMORY_THRESHOLD)): vol.All(vol.Coerce(int), vol.Range(min=50, max=95)),
            vol.Optional(CONF_ISG_CPU_THRESHOLD, default=current_config.get(CONF_ISG_CPU_THRESHOLD, DEFAULT_ISG_CPU_THRESHOLD)): vol.All(vol.Coerce(int), vol.Range(min=50, max=99)),
        })

        # Apps 与可见性
        current_apps = current_config.get(CONF_APPS, DEFAULT_APPS)
        current_visible = current_config.get(CONF_VISIBLE_APPS, list(current_apps.keys() or DEFAULT_APPS.keys()))

        for name in current_apps.keys():
            options_schema = options_schema.extend({
                vol.Optional(f"app_{name.lower()}", default=current_apps.get(name, "")): cv.string,
            })

        options_schema = options_schema.extend({
            vol.Optional("visible_apps", default=current_visible): cv.multi_select(list(current_apps.keys())),
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)
