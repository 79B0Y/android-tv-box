# Android TV Box Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

**A comprehensive Home Assistant integration for controlling Android TV Boxes via ADB with specialized ISG application monitoring.**

![Android TV Box Integration](https://github.com/android-tv-box/android-tv-box-integration/raw/main/images/android_tv_box_logo.png)

## Features

🎮 **Complete Media Control**
- Media player with play/pause/stop/volume control
- Google Cast support (YouTube, Netflix, Spotify)
- Power management and navigation controls

📱 **Device Management**  
- D-pad navigation buttons
- App launcher with configured applications
- Real-time screenshot camera
- Adjustable screen brightness

📊 **System Monitoring**
- CPU, memory, and network monitoring
- Current app tracking
- WiFi status and connection info

🔧 **ISG Application Monitoring**
- Specialized monitoring for ISG applications
- Auto-restart and crash detection
- Performance metrics and health status

⚡ **Performance Optimized**
- Smart monitoring with conditional updates
- Command caching and resource management
- Optimized for low-resource environments

## Quick Start

1. **Install via HACS:**
   - Add this repository to HACS
   - Install "Android TV Box Integration"
   - Restart Home Assistant

2. **Enable ADB on your Android TV:**
   - Go to Settings → About → Build (tap 7 times)
   - Enable Developer options → USB debugging
   - Enable Network ADB if available

3. **Add Integration:**
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "Android TV Box Integration"
   - Enter your device IP address and port (usually 5555)

## Configuration

The integration provides a comprehensive setup flow:

- **Device Connection:** IP address and ADB port configuration
- **Advanced Options:** Screenshot settings, update intervals, ISG monitoring
- **App Configuration:** Configure application package names and visibility

## Entities Created

### Media Player
- Complete media control with Cast support

### Sensors  
- Brightness, network status, current app
- System performance (CPU, memory)
- ISG monitoring (status, memory, CPU, uptime, crashes)

### Controls
- Power, WiFi, and ADB connection switches
- Navigation buttons (up/down/left/right/center/back/home/menu)
- Screenshot camera
- Brightness control slider
- App selector dropdown
- ISG control buttons (restart, clear cache, health check)

## ISG Monitoring

Specialized monitoring for `com.linknlink.app.device.isg` applications:

- **Health Assessment:** Real-time application health monitoring
- **Performance Tracking:** Memory and CPU usage monitoring
- **Auto-Recovery:** Automatic restart when unhealthy conditions detected
- **Crash Detection:** Monitor and count application crashes and ANRs
- **Manual Controls:** Restart, cache clearing, and diagnostic tools

## Automation Examples

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
          message: "ISG application crashed and is being restarted."
```

## Performance Optimization

Optimized for environments with limited resources:

- **Layered Update Frequencies:** Basic (60s), detailed (5min), low-priority (15min)
- **Command Caching:** 30-second TTL prevents duplicate operations
- **Resource Limits:** Maximum 2 concurrent ADB commands
- **Smart Monitoring:** Conditional updates based on device state
- **Immediate Feedback:** Control actions provide instant UI updates

## Support

- 📚 [Documentation](https://github.com/android-tv-box/android-tv-box-integration/wiki)
- 🐛 [Issues](https://github.com/android-tv-box/android-tv-box-integration/issues)
- 💬 [Discussions](https://github.com/android-tv-box/android-tv-box-integration/discussions)

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/android-tv-box/android-tv-box-integration.svg?style=for-the-badge
[commits]: https://github.com/android-tv-box/android-tv-box-integration/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/android-tv-box/android-tv-box-integration.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/android-tv-box/android-tv-box-integration.svg?style=for-the-badge
[releases]: https://github.com/android-tv-box/android-tv-box-integration/releases