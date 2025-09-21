"""The Android TV Box Integration."""
import asyncio
import logging
import os
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .adb_manager import ADBManager
from .const import DOMAIN, PLATFORMS
from .coordinator import AndroidTVUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_merged_config(entry: ConfigEntry) -> Dict[str, Any]:
    """Get merged configuration from entry data and options."""
    config = dict(entry.data)
    config.update(entry.options)
    return config


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Android TV Box from a config entry."""
    # Prevent double-setup in rare race conditions
    hass.data.setdefault(DOMAIN, {})
    existing = hass.data[DOMAIN].get(entry.entry_id)
    if existing and existing.get("initialized"):
        _LOGGER.debug("Entry %s already initialized; skipping duplicate setup", entry.entry_id)
        return True
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    
    # Prepare ADB authentication key (generate if missing)
    key_dir = hass.config.path(".storage")
    os.makedirs(key_dir, exist_ok=True)
    key_path = os.path.join(key_dir, f"android_tv_box_{entry.entry_id}.adb_key")

    rsa_signers = None
    try:
        from adb_shell.auth.keygen import keygen
        from adb_shell.auth.sign_pythonrsa import PythonRSASigner

        if not os.path.exists(key_path):
            keygen(key_path)
        rsa_signers = [PythonRSASigner.FromRSAKeyPath(key_path)]
    except Exception as e:  # If dependency not available yet during setup, continue without keys
        _LOGGER.debug("ADB key setup skipped: %s", e)

    # Create ADB manager with keys (if available)
    adb_manager = ADBManager(host, port)
    if rsa_signers:
        # Monkey-attach signers for use during connect
        setattr(adb_manager, "_rsa_signers", rsa_signers)
    
    # Get merged configuration from data and options
    merged_config = _get_merged_config(entry)
    
    # Create update coordinator
    coordinator = AndroidTVUpdateCoordinator(
        hass=hass,
        adb_manager=adb_manager,
        config=merged_config,
    )
    
    # Test initial connection
    try:
        await asyncio.wait_for(adb_manager.connect(), timeout=10)
        _LOGGER.info("Successfully connected to Android TV Box at %s:%s", host, port)
    except Exception as e:
        _LOGGER.error("Failed to connect to Android TV Box at %s:%s: %s", host, port, e)
        # Don't fail setup - let coordinator handle reconnection
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator in hass data
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "adb_manager": adb_manager,
        "initialized": True,
    }
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Clean up coordinator and ADB manager
        data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator = data["coordinator"]
        adb_manager = data["adb_manager"]
        
        # Disconnect ADB
        try:
            await adb_manager.disconnect()
        except Exception as e:
            _LOGGER.debug("Error disconnecting ADB: %s", e)
        
        # Stop coordinator
        coordinator.async_stop()
    
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for the entry."""
    # Reload the integration to apply new options
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)
    
    if config_entry.version == 1:
        # No migration needed for version 1
        return True
    
    # Migration logic for future versions would go here
    return False
