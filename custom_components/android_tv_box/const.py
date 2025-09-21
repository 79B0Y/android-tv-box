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
CONF_HOST = "host"
CONF_PORT = "port"
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
DEFAULT_ISG_MEMORY_THRESHOLD = 85
DEFAULT_ISG_CPU_THRESHOLD = 95

# Update intervals
BASE_UPDATE_INTERVAL = timedelta(seconds=60)
HIGH_FREQUENCY_INTERVAL = timedelta(minutes=5)
LOW_FREQUENCY_INTERVAL = timedelta(minutes=15)
ISG_CHECK_INTERVAL = timedelta(minutes=2)

# ADB timeouts and limits
ADB_TIMEOUT = 15
MAX_CONCURRENT_COMMANDS = 2
COMMAND_CACHE_TTL = 30

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
    "media_play": "shell input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_PLAY),
    "media_pause": "shell input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_PAUSE),
    "media_stop": "shell input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_STOP),
    "media_play_pause": "shell input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_PLAY_PAUSE),
    "media_next": "shell input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_NEXT),
    "media_previous": "shell input keyevent {keycode}".format(keycode=KEYCODE_MEDIA_PREVIOUS),
    
    # Volume control
    "volume_up": "shell input keyevent {keycode}".format(keycode=KEYCODE_VOLUME_UP),
    "volume_down": "shell input keyevent {keycode}".format(keycode=KEYCODE_VOLUME_DOWN),
    "volume_mute": "shell input keyevent {keycode}".format(keycode=KEYCODE_VOLUME_MUTE),
    
    # Power control
    "power_on": "shell input keyevent {keycode}".format(keycode=KEYCODE_WAKEUP),
    "power_off": "shell input keyevent {keycode}".format(keycode=KEYCODE_POWER),
    
    # Navigation
    "nav_up": "shell input keyevent {keycode}".format(keycode=KEYCODE_DPAD_UP),
    "nav_down": "shell input keyevent {keycode}".format(keycode=KEYCODE_DPAD_DOWN),
    "nav_left": "shell input keyevent {keycode}".format(keycode=KEYCODE_DPAD_LEFT),
    "nav_right": "shell input keyevent {keycode}".format(keycode=KEYCODE_DPAD_RIGHT),
    "nav_center": "shell input keyevent {keycode}".format(keycode=KEYCODE_DPAD_CENTER),
    "nav_back": "shell input keyevent {keycode}".format(keycode=KEYCODE_BACK),
    "nav_home": "shell input keyevent {keycode}".format(keycode=KEYCODE_HOME),
    "nav_menu": "shell input keyevent {keycode}".format(keycode=KEYCODE_MENU),
}

# State query commands
STATE_COMMANDS = {
    "media_state": "shell dumpsys media_session | awk '/Sessions Stack/ {inStack=1} inStack && /package=/ {pkg=$0} /active=true/ {active=1} /state=PlaybackState/ && active { if (match($0, /state=([A-Z_]+)\\([0-9]+\\)/, m)) { print m[1]; exit } }'",
    "volume_level": "shell cmd media_session volume --stream 3 --get",
    "power_state": "shell dumpsys power | grep -E '(mWakefulness|mScreenOn)'",
    "wifi_state": "shell settings get global wifi_on",
    "wifi_ssid": "shell dumpsys wifi | grep 'SSID:' | head -1",
    "ip_address": "shell ip addr show wlan0 | grep 'inet '",
    "current_app": "shell dumpsys activity activities | grep 'ActivityRecord' | head -1",
    "current_activity": "shell dumpsys activity top | grep ACTIVITY",
    "installed_apps": "shell pm list packages -3",
    "brightness": "shell settings get system screen_brightness",
    "device_info": "shell getprop",
    "screenshot": "shell screencap -p {path}",
}

# ISG monitoring commands
ISG_COMMANDS = {
    "process_status": "shell ps | grep com.linknlink.app.device.isg",
    "memory_usage": "shell dumpsys meminfo com.linknlink.app.device.isg | head -20",
    "cpu_usage": "shell top -p $(pidof com.linknlink.app.device.isg) -n 1",
    "app_logs": "shell logcat -s ISG:* -v time -t 50",
    "crash_logs": "shell logcat -b crash -v time -t 25",
    "anr_logs": "shell logcat -s ActivityManager:* -v time -t 10 | grep ANR",
}

# ISG control commands  
ISG_CONTROL_COMMANDS = {
    "force_start": "shell am start -n com.linknlink.app.device.isg/.MainActivity --activity-clear-top",
    "force_stop": "shell am force-stop com.linknlink.app.device.isg",
    "restart": "shell 'am force-stop com.linknlink.app.device.isg && sleep 2 && am start -n com.linknlink.app.device.isg/.MainActivity'",
    "clear_cache": "shell pm clear com.linknlink.app.device.isg",
}

# Set commands
SET_COMMANDS = {
    "set_volume": "shell service call audio 12 i32 3 i32 {level} i32 0",
    "set_brightness": "shell settings put system screen_brightness {level}",
    "start_app": "shell am start {package}",
    "cast_media": "shell am start -a android.intent.action.VIEW -d '{url}' --es android.intent.extra.REFERRER_NAME 'Home Assistant'",
    "cast_youtube": "shell am start -a android.intent.action.VIEW -d 'https://www.youtube.com/watch?v={video_id}' -n com.google.android.youtube/.WatchWhileActivity",
    "cast_netflix": "shell am start -a android.intent.action.VIEW -d 'https://www.netflix.com/watch/{video_id}' -n com.netflix.mediaclient/.ui.launch.UIWebViewActivity",
    "cast_spotify": "shell am start -a android.intent.action.VIEW -d 'spotify:track:{track_id}' -n com.spotify.music/.MainActivity",
}

# Wait times for immediate feedback (in seconds)
IMMEDIATE_FEEDBACK_TIMINGS = {
    "volume": 0.3,
    "mute": 0.3,
    "media_play": 0.5,
    "media_pause": 0.5,
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
    "YouTube": "com.google.android.youtube",
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