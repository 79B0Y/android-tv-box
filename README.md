# Android TV Box HACS Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

A comprehensive Home Assistant Custom Component for controlling Android TV Boxes via ADB, with specialized ISG application monitoring.

## Features

### 🎮 Complete Media Control
- **Media Player Entity**: Play, pause, stop, volume control, and Google Cast functionality
- **Power Management**: Turn device on/off, monitor power states
- **Volume Control**: Precise volume adjustment with immediate feedback
- **Cast Support**: YouTube, Netflix, Spotify, and generic media URL casting

### 📱 Device Management
- **Navigation Controls**: D-pad navigation buttons (up, down, left, right, center, back, home, menu)
- **App Launcher**: Quick access to configured applications
- **Screenshot Camera**: Real-time device screen capture
- **Brightness Control**: Adjustable screen brightness with slider

### 📊 System Monitoring
- **Performance Sensors**: CPU usage, memory usage, brightness levels
- **Network Information**: WiFi status, SSID, IP address
- **Current App Tracking**: Monitor foreground applications

### 🔧 ISG Application Monitoring
Specialized monitoring for `com.linknlink.app.device.isg` application:
- **Health Status**: Real-time application health assessment
- **Performance Metrics**: Memory and CPU usage monitoring
- **Auto-Recovery**: Automatic restart when unhealthy conditions detected
- **Crash Detection**: Monitor and count application crashes
- **Manual Controls**: Restart, cache clearing, and health check buttons

### ⚡ Performance Optimized
- **Smart Monitoring**: Conditional updates based on device state
- **Command Caching**: Reduce duplicate ADB operations
- **Immediate Feedback**: Control actions provide instant state updates
- **Resource Management**: Optimized for low-resource environments (Termux/Ubuntu)

## Installation

### HACS Installation (Recommended)

1. **Add Custom Repository**:
   - Open HACS in Home Assistant
   - Go to "Integrations" 
   - Click the three dots menu → "Custom repositories"
   - Add `https://github.com/your-username/android-tv-box-integration`
   - Category: "Integration"

2. **Install Integration**:
   - Search for "Android TV Box Integration" in HACS
   - Click "Download"
   - Restart Home Assistant

3. **Add Integration**:
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "Android TV Box Integration"

### Manual Installation

1. **Download Files**:
   ```bash
   cd /config/custom_components
   git clone https://github.com/your-username/android-tv-box-integration.git android_tv_box
   ```

2. **Install Dependencies**:
   ```bash
   pip install "adb-shell>=0.4.4" "pure-python-adb>=0.3.0"
   ```

3. **Restart Home Assistant**

## Configuration

### Device Setup

1. **Enable ADB on Android TV**:
   - Go to Settings → About → Build (tap 7 times to enable Developer options)
   - Go to Settings → Developer options → Enable "USB debugging"
   - Enable "Network ADB" if available

2. **Connect via ADB**:
   ```bash
   adb connect <your-device-ip>:5555
   ```

### Integration Setup

1. **Basic Configuration**:
   - **IP Address**: Your Android TV Box IP address
   - **ADB Port**: Usually 5555
   - **Device Name**: Friendly name for your device

2. **Advanced Options**:
   - **Screenshot Path**: Device path for screenshots (`/sdcard/isgbackup/screenshot/`)
   - **Update Interval**: Data refresh interval (60 seconds recommended)
   - **ISG Monitoring**: Enable specialized ISG application monitoring
   - **Performance Thresholds**: Memory (85%) and CPU (95%) thresholds for auto-restart

3. **App Configuration**:
   - Configure package names for installed applications
   - Select which apps appear in the app selector

## Entities Created

### Media Player
- `media_player.android_tv_box_media_player`: Complete media control with Cast support

### Switches
- `switch.android_tv_box_power`: Device power control
- `switch.android_tv_box_wifi`: WiFi status monitoring
- `switch.android_tv_box_adb`: ADB connection management

### Sensors
- `sensor.android_tv_box_brightness`: Screen brightness percentage
- `sensor.android_tv_box_network`: Network connection status
- `sensor.android_tv_box_current_app`: Current foreground application
- `sensor.android_tv_box_cpu`: System CPU usage
- `sensor.android_tv_box_memory`: System memory usage

### ISG Monitoring Sensors
- `sensor.android_tv_box_isg_status`: ISG application health status
- `sensor.android_tv_box_isg_memory`: ISG memory usage (MB)
- `sensor.android_tv_box_isg_cpu`: ISG CPU usage percentage
- `sensor.android_tv_box_isg_uptime`: ISG uptime in minutes
- `sensor.android_tv_box_isg_crash_count`: ISG crash counter

### Controls
- `camera.android_tv_box_screenshot`: Real-time screenshot camera
- `number.android_tv_box_brightness_control`: Brightness adjustment slider
- `select.android_tv_box_app_selector`: Application launcher
- Navigation buttons: Up, Down, Left, Right, Center, Back, Home, Menu
- ISG control buttons: Restart, Clear Cache, Health Check

## Usage Examples

### Automation Examples

```yaml
# Morning TV routine
automation:
  - alias: "Morning TV Startup"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: media_player.turn_on
        target:
          entity_id: media_player.android_tv_box_media_player
      - delay: "00:00:05"
      - service: select.select_option
        target:
          entity_id: select.android_tv_box_app_selector
        data:
          option: "YouTube"

# ISG health monitoring
automation:
  - alias: "ISG Health Alert"
    trigger:
      - platform: state
        entity_id: sensor.android_tv_box_isg_status
        to: "crashed"
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ ISG Application Issue"
          message: "ISG application has crashed and is being restarted automatically."

# Smart volume control for night time
automation:
  - alias: "Night Volume Control"
    trigger:
      - platform: time
        at: "22:00:00"
    condition:
      - condition: state
        entity_id: media_player.android_tv_box_media_player
        state: "playing"
    action:
      - service: media_player.volume_set
        target:
          entity_id: media_player.android_tv_box_media_player
        data:
          volume_level: 0.3
```

### Service Calls

```yaml
# Cast YouTube video
service: media_player.play_media
target:
  entity_id: media_player.android_tv_box_media_player
data:
  media_content_type: "youtube"
  media_content_id: "dQw4w9WgXcQ"

# Cast generic media URL
service: media_player.play_media
target:
  entity_id: media_player.android_tv_box_media_player
data:
  media_content_type: "video"
  media_content_id: "https://example.com/video.mp4"

# Restart ISG application
service: button.press
target:
  entity_id: button.android_tv_box_restart_isg
```

## Performance Optimization

### For Low-Resource Environments

The integration is optimized for environments like Termux and Ubuntu with limited resources:

- **Layered Update Frequencies**: Basic status (60s), detailed monitoring (5min), low-priority items (15min)
- **Command Caching**: 30-second TTL to prevent duplicate ADB calls
- **Resource Limits**: Maximum 2 concurrent ADB commands
- **Smart Monitoring**: Skip detailed checks when device is offline
- **Immediate Feedback**: Control actions provide instant UI updates

### Configuration Recommendations

```yaml
# Optimized configuration for Termux/Ubuntu
android_tv_box:
  update_interval: 60  # Base update interval
  isg_check_interval: 120  # ISG monitoring interval
  max_concurrent_commands: 2
  enable_command_cache: true
  cache_ttl: 30
  smart_monitoring: true
```

## Troubleshooting

### Common Issues

1. **Connection Failed**:
   - Verify ADB debugging is enabled
   - Check IP address and port
   - Ensure device is reachable: `ping <device-ip>`
   - Test ADB connection: `adb connect <device-ip>:5555`

2. **ISG Monitoring Not Working**:
   - Verify ISG application is installed: `adb shell pm list packages | grep isg`
   - Check package name in configuration
   - Ensure application has necessary permissions

3. **Performance Issues**:
   - Increase update intervals
   - Enable smart monitoring
   - Reduce concurrent command limit
   - Check device resources

### Debug Logging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.android_tv_box: debug
```

### Testing ADB Commands

```bash
# Test basic connectivity
adb -s <device-ip>:5555 shell echo "test"

# Test volume control
adb -s <device-ip>:5555 shell cmd media_session volume --stream 3 --get

# Test ISG status
adb -s <device-ip>:5555 shell ps | grep com.linknlink.app.device.isg
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and test thoroughly
4. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-username/android-tv-box-integration.git
cd android-tv-box-integration

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run linting
black custom_components/ tests/
flake8 custom_components/ tests/
mypy custom_components/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/your-username/android-tv-box-integration/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/your-username/android-tv-box-integration/discussions)
- 📖 **Documentation**: [Wiki](https://github.com/your-username/android-tv-box-integration/wiki)

## Acknowledgments

- Home Assistant community for guidance and support
- ADB tools developers for the underlying connectivity
- ISG application developers for the monitoring requirements

---

**⭐ If this integration helps you, please star the repository!**

[commits-shield]: https://img.shields.io/github/commit-activity/y/your-username/android-tv-box-integration.svg?style=for-the-badge
[commits]: https://github.com/your-username/android-tv-box-integration/commits/main
[license-shield]: https://img.shields.io/github/license/your-username/android-tv-box-integration.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/your-username/android-tv-box-integration.svg?style=for-the-badge
[releases]: https://github.com/your-username/android-tv-box-integration/releases