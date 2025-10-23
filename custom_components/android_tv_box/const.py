"""Constants for Android TV Box Integration."""
from datetime import timedelta
from homeassistant.const import Platform

DOMAIN = "android_tv_box"

# Supported platforms
PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.SWITCH,
    Platform.CAMERA,
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
]

# Configuration keys
# CONF_HOST and CONF_PORT are imported from homeassistant.const
CONF_DEVICE_NAME = "device_name"
CONF_SCREENSHOT_PATH = "screenshot_path"
CONF_SCREENSHOT_KEEP_COUNT = "screenshot_keep_count"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ISG_MONITORING = "isg_monitoring"
CONF_ISG_AUTO_RESTART = "isg_auto_restart"
CONF_ISG_MEMORY_THRESHOLD = "isg_memory_threshold"
CONF_ISG_CPU_THRESHOLD = "isg_cpu_threshold"
CONF_APPS = "apps"
CONF_VISIBLE_APPS = "visible"

# Default values
DEFAULT_PORT = 5555
DEFAULT_DEVICE_NAME = "Android TV Box"
DEFAULT_SCREENSHOT_PATH = "/sdcard/isgbackup/screenshot/"
DEFAULT_SCREENSHOT_KEEP_COUNT = 3
DEFAULT_UPDATE_INTERVAL = 60
DEFAULT_ISG_MEMORY_THRESHOLD = 80
DEFAULT_ISG_CPU_THRESHOLD = 90

# Update intervals
BASE_UPDATE_INTERVAL = timedelta(seconds=60)
HIGH_FREQUENCY_INTERVAL = timedelta(seconds=30)  # CPU, memory, brightness, current app - 30 seconds
LOW_FREQUENCY_INTERVAL = timedelta(minutes=15)
ISG_CHECK_INTERVAL = timedelta(minutes=2)

# ADB timeouts and limits
ADB_TIMEOUT = 15
MAX_CONCURRENT_COMMANDS = 2
COMMAND_CACHE_TTL = 30
CACHE_MAX_SIZE = 100

# Monitoring thresholds and intervals
OFFLINE_SKIP_THRESHOLD_MINUTES = 5
ISG_MIN_RESTART_INTERVAL_MINUTES = 5
ECHO_TEST_TIMEOUT = 5
CONNECTION_TIMEOUT = 10

# Media keycodes
KEYCODE_MEDIA_PLAY = 126
KEYCODE_MEDIA_PAUSE = 127
KEYCODE_MEDIA_STOP = 86
KEYCODE_MEDIA_PLAY_PAUSE = 85
KEYCODE_MEDIA_NEXT = 87
KEYCODE_MEDIA_PREVIOUS = 88

# Volume keycodes
KEYCODE_VOLUME_UP = 24
KEYCODE_VOLUME_DOWN = 25
KEYCODE_VOLUME_MUTE = 164

# Power keycodes
KEYCODE_POWER = 26
KEYCODE_WAKEUP = 224
KEYCODE_SLEEP = 223

# Navigation keycodes
KEYCODE_DPAD_UP = 19
KEYCODE_DPAD_DOWN = 20
KEYCODE_DPAD_LEFT = 21
KEYCODE_DPAD_RIGHT = 22
KEYCODE_DPAD_CENTER = 23
KEYCODE_BACK = 4
KEYCODE_HOME = 3
KEYCODE_MENU = 82

# ADB commands
ADB_COMMANDS = {
    # Media control
    "media_play": "input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_PLAY),
    "media_pause": "input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_PAUSE),
    "media_stop": "input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_STOP),
    "media_play_pause": "input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_PLAY_PAUSE),
    "media_next": "input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_NEXT),
    "media_previous": "input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_PREVIOUS),

    # Volume control
    "volume_up": "input keyevent {keycode}".format(keycode=KEYCODE_VOLUME_UP),
    "volume_down": "input keyevent {keycode}".format(keycode=KEYCODE_VOLUME_DOWN),
    "volume_mute": "input keyevent {keycode}".format(keycode=KEYCODE_VOLUME_MUTE),

    # Power control
    "power_on": "input keyevent {keycode}".format(keycode=KEYCODE_WAKEUP),
    "power_off": "input keyevent {keycode}".format(keycode=KEYCODE_SLEEP),
    "power_toggle": "input keyevent {keycode}".format(keycode=KEYCODE_POWER),

    # Navigation
    "nav_up": "input keyevent {keycode}".format(keycode=KEYCODE_DPAD_UP),
    "nav_down": "input keyevent {keycode}".format(keycode=KEYCODE_DPAD_DOWN),
    "nav_left": "input keyevent {keycode}".format(keycode=KEYCODE_DPAD_LEFT),
    "nav_right": "input keyevent {keycode}".format(keycode=KEYCODE_DPAD_RIGHT),
    "nav_center": "input keyevent {keycode}".format(keycode=KEYCODE_DPAD_CENTER),
    "nav_back": "input keyevent {keycode}".format(keycode=KEYCODE_BACK),
    "nav_home": "input keyevent {keycode}".format(keycode=KEYCODE_HOME),
    "nav_menu": "input keyevent {keycode}".format(keycode=KEYCODE_MENU),
}

# State query commands
STATE_COMMANDS = {
    # Raw output; parse in Python for better compatibility across ROMs
    "media_state": "dumpsys media_session",
    "volume_level": "cmd media_session volume --stream 3 --get",
    # Read full power dump for robust parsing across ROMs
    "power_state": "dumpsys power",
    "wifi_state": "settings get global wifi_on",
    "wifi_ssid": "dumpsys wifi | grep 'SSID:' | head -1",
    "ip_address": "ip addr show wlan0 | grep 'inet '",
    "current_app": "dumpsys activity activities | grep 'ActivityRecord' | head -1",
    "current_activity": "dumpsys activity activities | grep topResumedActivity",
    "installed_apps": "pm list packages -3",
    "brightness": "settings get system screen_brightness",
    "device_info": "getprop",
    "screenshot": "screencap -p {path}",
    # Audio info for accurate mute detection
    "audio_info": "dumpsys audio",
}

# ISG monitoring commands
ISG_COMMANDS = {
    # Use pidof to reliably detect process on modern Android
    "process_status": "pidof com.linknlink.app.device.isg",
    "memory_usage": "dumpsys meminfo com.linknlink.app.device.isg | head -50",
    "cpu_usage": "PID=$(pidof com.linknlink.app.device.isg); if [ -n \"$PID\" ]; then top -n 1 -p $PID; else echo 'NO_PID'; fi",
    "app_logs": "logcat -s ISG:* -v time -t 50",
    "crash_logs": "logcat -b crash -v time -t 50",
    "anr_logs": "logcat -s ActivityManager:* -v time -t 10 | grep ANR",
}

# ISG control commands  
ISG_CONTROL_COMMANDS = {
    "force_start": "am start -n com.linknlink.app.device.isg/.MainActivity --activity-clear-top",
    "force_stop": "am force-stop com.linknlink.app.device.isg",
    "restart": "am force-stop com.linknlink.app.device.isg && sleep 2 && am start -n com.linknlink.app.device.isg/.MainActivity",
    "clear_cache": "pm clear com.linknlink.app.device.isg",
}

# Set commands
SET_COMMANDS = {
    # Prefer cmd media_session for modern Android
    "set_volume": "cmd media_session volume --stream 3 --set {level}",
    # Fallback for some ROMs
    "set_volume_alt": "media volume --stream 3 --set {level}",
    "set_brightness": "settings put system screen_brightness {level}",
    # Use MAIN/LAUNCHER with flags; caller passes package as '-p <pkg>' or full component
    "start_app": "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -f 0x10200000 -p {package}",
    # Generic URL cast as a fallback
    "cast_media": "am start -a android.intent.action.VIEW -d '{url}' --es android.intent.extra.REFERRER_NAME 'Home Assistant'",
}

# TV-first cast intent templates (tried in order). We use '-p <package>' so we don't need exact Activity.
CAST_INTENTS = {
    "youtube": [
        # YouTube TV preferred
        "am start -a android.intent.action.VIEW -d 'https://www.youtube.com/watch?v={video_id}' -p com.google.android.youtube.tv",
        "am start -a android.intent.action.VIEW -d 'vnd.youtube:{video_id}' -p com.google.android.youtube.tv",
        # Fallback to phone/tablet YouTube if TV not present
        "am start -a android.intent.action.VIEW -d 'https://www.youtube.com/watch?v={video_id}' -p com.google.android.youtube",
    ],
    "netflix": [
        # Netflix for Android TV package
        "am start -a android.intent.action.VIEW -d 'nflx://www.netflix.com/watch/{video_id}' -p com.netflix.ninja",
        "am start -a android.intent.action.VIEW -d 'https://www.netflix.com/watch/{video_id}' -p com.netflix.ninja",
        # Fallback to mobile package
        "am start -a android.intent.action.VIEW -d 'https://www.netflix.com/watch/{video_id}' -p com.netflix.mediaclient",
    ],
    "spotify": [
        # Spotify Android TV
        "am start -a android.intent.action.VIEW -d 'spotify:track:{track_id}' -p com.spotify.tv.android",
        # Fallback to mobile
        "am start -a android.intent.action.VIEW -d 'spotify:track:{track_id}' -p com.spotify.music",
    ],
    "url": [
        # Let system choose capable app
        "am start -a android.intent.action.VIEW -d '{url}'",
    ],
}

# Expected packages for cast verification
CAST_EXPECTED_PACKAGES = {
    "youtube": ["com.google.android.youtube.tv", "com.google.android.youtube"],
    "netflix": ["com.netflix.ninja", "com.netflix.mediaclient"],
    "spotify": ["com.spotify.tv.android", "com.spotify.music"],
}

# Wait times for immediate feedback (in seconds)
IMMEDIATE_FEEDBACK_TIMINGS = {
    "volume": 0.3,
    "mute": 0.3,
    "media_play": 1.8,
    "media_pause": 0.8,
    "media_stop": 0.8,
    "power_on": 1.0,
    "power_off": 1.0,
    "wifi_toggle": 1.0,
    "wifi_connect": 2.0,
    "app_start": 2.0,
    "app_switch": 1.0,
    "isg_restart": 3.0,
    "isg_start": 3.0,
    "isg_cache_clear": 2.0,
    "brightness": 0.3,
}

# Default apps configuration
DEFAULT_APPS = {
    "YouTube": "com.google.android.youtube.tv",  # TV version
    "Netflix": "com.netflix.mediaclient",
    "Spotify": "com.spotify.music",
    "iSG": "com.linknlink.app.device.isg",
}

# Error messages
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_UNKNOWN = "unknown"
ERROR_TIMEOUT = "timeout"

# ISG monitoring constants
ISG_PACKAGE_NAME = "com.linknlink.app.device.isg"
ISG_MAIN_ACTIVITY = "com.linknlink.app.device.isg/.MainActivity"
MAX_ISG_RESTART_ATTEMPTS = 3
ISG_HEALTH_CHECK_TIMEOUT = 30

# Media states
MEDIA_STATE_PLAYING = "playing"
MEDIA_STATE_PAUSED = "paused"
MEDIA_STATE_IDLE = "idle"
MEDIA_STATE_OFF = "off"
MEDIA_STATE_STANDBY = "standby"

# Power states
POWER_STATE_ON = "on"
POWER_STATE_OFF = "off"
POWER_STATE_STANDBY = "standby"

# ISG health states
ISG_HEALTH_HEALTHY = "healthy"
ISG_HEALTH_UNHEALTHY = "unhealthy"
ISG_HEALTH_CRASHED = "crashed"
ISG_HEALTH_NOT_RUNNING = "not_running"
ISG_HEALTH_UNKNOWN = "unknown"
