# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains design documentation for an Android TV Box Home Assistant HACS Integration. The project enables control of Android TV devices through ADB (Android Debug Bridge) connections, providing comprehensive media player, device control, and monitoring capabilities within Home Assistant.

## Architecture & Design

The integration follows Home Assistant's standard structure for custom components with these key modules:

- **ADB Manager** (`adb_manager.py`): Handles all ADB communication and command execution
- **Coordinator** (`coordinator.py`): Manages data updates and state synchronization  
- **Multiple Entity Types**: Media player, switches, sensors, buttons, cameras, number inputs, and selects
- **ISG Monitoring**: Specialized monitoring for `com.linknlink.app.device.isg` application

### Core Components Structure
```
custom_components/android_tv_box/
├── __init__.py              # Main integration setup
├── manifest.json            # Integration metadata  
├── config_flow.py           # Configuration UI
├── const.py                # Constants and command definitions
├── coordinator.py          # Data update coordinator
├── adb_manager.py          # ADB connection and command management
├── device_info.py          # Device information handling
├── media_player.py         # Media player entity
├── switch.py               # Switch entities (power, WiFi, ADB)
├── camera.py               # Camera entity (screenshots)
├── sensor.py               # Sensor entities (monitoring)
├── button.py               # Button entities (navigation, controls)
├── number.py               # Number entity (brightness)
├── select.py               # Select entity (app launcher)
└── translations/           # Localization files
```

## Key Technical Concepts

### ADB Command Integration
- All device control uses ADB shell commands over network connection (127.0.0.1:5555)
- Commands include media keys (KEYCODE_MEDIA_PLAY/PAUSE), volume control, navigation
- State queries use `dumpsys` and system property commands
- Optimized for Termux/Ubuntu environments with full device specification

### Performance Optimization Strategy
- **Layered monitoring frequencies**: 60s base, 5min high-frequency, 15min low-frequency
- **Command caching**: 30-second TTL to reduce duplicate ADB calls
- **Batch operations**: Combined shell sessions for multiple commands
- **Resource limits**: Max 2 concurrent ADB commands, memory usage monitoring

### Immediate State Refresh Pattern
After control operations, the integration immediately queries relevant state:
```python
# Pattern: control action → wait → query state → update UI → full refresh
await control_action()
await asyncio.sleep(wait_time)  # Variable timing per operation type
new_state = await state_query()
self.update_local_state(new_state)
self.async_write_ha_state()  # Immediate UI update
await self.coordinator.async_request_refresh()
```

## Development Commands

Since this is currently a design repository with no code implementation:

### When Implementation Begins
- Use Home Assistant development container or local HA dev environment
- Testing requires actual Android TV device with ADB debugging enabled
- Dependencies: `adb-shell>=0.4.4`, `pure-python-adb>=0.3.0`

### Key ADB Testing Commands
```bash
# Test device connectivity
adb devices
adb connect 127.0.0.1:5555

# Basic functionality tests  
adb -s 127.0.0.1:5555 shell input keyevent 85  # play/pause
adb -s 127.0.0.1:5555 shell dumpsys power | grep mWakefulness
adb -s 127.0.0.1:5555 shell cmd media_session volume --stream 3 --get
```

## Integration-Specific Patterns

### Entity State Management
- Entities inherit from `AndroidTVEntity` base class
- Coordinator pattern for centralized state updates
- Device info provides unified device identification
- Available state tied to ADB connection status

### ISG Application Monitoring
Special monitoring subsystem for ISG application:
- Process status checking (`ps | grep com.linknlink.app.device.isg`)
- Memory/CPU usage monitoring
- Automatic restart logic with crash detection
- Health status evaluation (healthy/unhealthy/crashed/not_running)

### Configuration Architecture
- Config flow for device discovery and setup
- YAML-based app configuration for launchers
- Threshold settings for monitoring alerts
- Performance tuning parameters for low-resource environments

## Error Handling Principles

- Graceful degradation when ADB connection fails
- Timeout handling for all ADB operations (15s default)
- Retry logic with exponential backoff
- Comprehensive logging for debugging
- State fallbacks using cached data when possible

## Optimization Considerations

### For Termux/Ubuntu Environments
- All ADB commands include full device specification (`-s 127.0.0.1:5555`)
- Reduced polling frequencies to minimize resource usage
- Command batching to reduce connection overhead
- Smart monitoring that skips updates when device is offline
- Memory and CPU limits to prevent system overload

### UI Responsiveness
- Immediate state queries after control actions
- Variable wait times based on operation type (300ms for volume, 3s for ISG restart)
- Async operations to prevent UI blocking
- Local state caching for fast responses

## Testing Strategy

When implementing:
- Unit tests for ADB command parsing and entity state logic
- Integration tests with mock ADB responses
- Real device testing for end-to-end validation
- Performance testing in constrained environments
- ISG monitoring reliability testing