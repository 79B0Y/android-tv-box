# Android TV Box HACS Integration 完整设计文档

## 目录

1. [项目概述](#项目概述)
2. [技术架构](#技术架构)  
3. [核心功能模块](#核心功能模块)
4. [实体定义](#实体定义)
5. [ISG应用监控模块](#isg应用监控模块)
6. [性能优化策略](#性能优化策略)
7. [配置与部署](#配置与部署)
8. [开发指南](#开发指南)
9. [故障排除](#故障排除)
10. [扩展功能规划](#扩展功能规划)

---

## 项目概述

### 项目简介
将Android TV盒子通过ADB连接，在Home Assistant中注册为一个虚拟设备，提供多种实体类型（媒体播放器、摄像头、传感器等）的统一控制接口，并包含专门的ISG应用监控模块。

### 主要特性
- **完整设备控制**: 电源、WiFi、ADB连接管理
- **媒体功能**: 播放、暂停、音量、Google Cast功能
- **系统监控**: CPU、内存、网络、应用状态
- **屏幕管理**: 亮度控制、屏幕截图
- **导航控制**: 方向键、返回、主页等按键
- **ISG专业监控**: 专门的ISG应用健康监控和自动恢复
- **应用管理**: 应用启动、选择、状态监控

### 支持的平台
```python
PLATFORMS = [
    Platform.MEDIA_PLAYER,    # 媒体播放器
    Platform.SWITCH,          # 开关（电源、WiFi、ADB）
    Platform.CAMERA,          # 摄像头（截图）
    Platform.SENSOR,          # 传感器（状态监控）
    Platform.BUTTON,          # 按键（导航、控制）
    Platform.NUMBER,          # 数值（亮度控制）
    Platform.SELECT,          # 选择（应用选择器）
]
```

---

## 技术架构

### 项目结构
```
custom_components/android_tv_box/
├── __init__.py              # 主入口，集成设置和协调器
├── manifest.json            # 集成元数据和依赖
├── config_flow.py           # 配置流程和设备发现
├── const.py                # 常量定义
├── coordinator.py          # 数据更新协调器
├── adb_manager.py          # ADB连接和命令管理
├── device_info.py          # 设备信息管理
├── media_player.py         # 媒体播放器实体
├── switch.py               # 开关实体
├── camera.py               # 摄像头实体
├── sensor.py               # 传感器实体
├── button.py               # 按键实体
├── number.py               # 数值实体
├── select.py               # 选择实体
├── strings.json            # 本地化字符串
└── translations/           # 多语言支持
    ├── en.json
    └── zh.json
```

### 连接方式
- **ADB连接**: `adb connect 127.0.0.1:5555`
- **通信协议**: 通过ADB shell命令执行各种操作
- **设备地址**: 127.0.0.1:5555 (可配置)

### manifest.json
```json
{
  "domain": "android_tv_box",
  "name": "Android TV Box Integration",
  "codeowners": ["@username"],
  "config_flow": true,
  "documentation": "https://github.com/username/android-tv-box-integration",
  "issue_tracker": "https://github.com/username/android-tv-box-integration/issues",
  "requirements": [
    "adb-shell>=0.4.4",
    "pure-python-adb>=0.3.0"
  ],
  "version": "1.0.0",
  "iot_class": "local_polling",
  "integration_type": "device"
}
```

---

## 核心功能模块

### ADB命令映射

#### 媒体播放控制
| 功能 | ADB命令 | 说明 |
|------|---------|------|
| 播放 | `adb -s 127.0.0.1:5555 shell input keyevent 126` | 开始播放 (KEYCODE_MEDIA_PLAY) |
| 暂停 | `adb -s 127.0.0.1:5555 shell input keyevent 127` | 暂停播放 (KEYCODE_MEDIA_PAUSE) |
| 停止 | `adb -s 127.0.0.1:5555 shell input keyevent 86` | 停止播放 (KEYCODE_MEDIA_STOP) |
| 播放/暂停切换 | `adb -s 127.0.0.1:5555 shell input keyevent 85` | 切换播放状态 (KEYCODE_MEDIA_PLAY_PAUSE) |
| 下一首 | `adb -s 127.0.0.1:5555 shell input keyevent 87` | 下一个内容 (KEYCODE_MEDIA_NEXT) |
| 上一首 | `adb -s 127.0.0.1:5555 shell input keyevent 88` | 上一个内容 (KEYCODE_MEDIA_PREVIOUS) |

#### 音量控制
| 功能 | ADB命令 | 说明 |
|------|---------|------|
| 音量增加 | `adb -s 127.0.0.1:5555 shell input keyevent 24` | 音量+1 (KEYCODE_VOLUME_UP) |
| 音量减少 | `adb -s 127.0.0.1:5555 shell input keyevent 25` | 音量-1 (KEYCODE_VOLUME_DOWN) |
| 静音切换 | `adb -s 127.0.0.1:5555 shell input keyevent 164` | 静音开关 (KEYCODE_VOLUME_MUTE) |
| 设置音量 | `adb -s 127.0.0.1:5555 shell service call audio 12 i32 3 i32 [level] i32 0` | 设置指定音量级别 |

#### 音量状态获取
```bash
adb -s 127.0.0.1:5555 shell cmd media_session volume --stream 3 --get
# 输出示例: volume is 8 in range [0..15]
# 音量为0时表示静音状态
# 音量百分比 = (当前音量 - 最小值) / (最大值 - 最小值) * 100
```

#### 电源管理
| 功能 | ADB命令 | 说明 |
|------|---------|------|
| 开机 | `adb -s 127.0.0.1:5555 shell input keyevent 224` | 唤醒设备 (KEYCODE_WAKEUP) |
| 关机 | `adb -s 127.0.0.1:5555 shell input keyevent 26` | 休眠设备 (KEYCODE_POWER) |

#### 电源状态检查
```bash
adb -s 127.0.0.1:5555 shell dumpsys power | grep -E "(mWakefulness|mScreenOn)"
# 输出示例:
# mWakefulness=Awake     # 开机状态 (设备醒着)
# mWakefulness=Asleep    # 关机状态 (设备休眠)
# mWakefulness=Dreaming  # 待机状态 (屏保模式)
# mScreenOn=true         # 屏幕开启
# mScreenOn=false        # 屏幕关闭

# 状态组合说明:
# Awake + mScreenOn=true  → 完全开机状态 (设备醒着且屏幕亮起)
# Awake + mScreenOn=false → 设备醒着但屏幕关闭 (可能是屏幕超时)
# Asleep + mScreenOn=false → 设备完全休眠
# Dreaming + mScreenOn=false → 屏保/待机模式
```

#### 导航控制
| 功能 | ADB命令 | 按键说明 |
|------|---------|----------|
| 上 | `adb -s 127.0.0.1:5555 shell input keyevent 19` | 方向键上 (KEYCODE_DPAD_UP) |
| 下 | `adb -s 127.0.0.1:5555 shell input keyevent 20` | 方向键下 (KEYCODE_DPAD_DOWN) |
| 左 | `adb -s 127.0.0.1:5555 shell input keyevent 21` | 方向键左 (KEYCODE_DPAD_LEFT) |
| 右 | `adb -s 127.0.0.1:5555 shell input keyevent 22` | 方向键右 (KEYCODE_DPAD_RIGHT) |
| 确定 | `adb -s 127.0.0.1:5555 shell input keyevent 23` | 确认键 (KEYCODE_DPAD_CENTER) |
| 返回 | `adb -s 127.0.0.1:5555 shell input keyevent 4` | 返回键 (KEYCODE_BACK) |
| 主页 | `adb -s 127.0.0.1:5555 shell input keyevent 3` | Home键 (KEYCODE_HOME) |
| 菜单 | `adb -s 127.0.0.1:5555 shell input keyevent 82` | Menu键 (KEYCODE_MENU) |

#### 播放状态获取
```bash
adb -s 127.0.0.1:5555 shell dumpsys media_session | awk '
/Sessions Stack/ {inStack=1}
inStack && /package=/ {pkg=$0}
/active=true/ {active=1}
/state=PlaybackState/ && active {
  if (match($0, /state=([A-Z_]+)\([0-9]+\)/, m)) {
    print m[1]; exit
  }
}'
# 输出：PLAYING / PAUSED / STOPPED / BUFFERING
```

#### Google Cast控制
```bash
# YouTube视频投射
adb -s 127.0.0.1:5555 shell am start -a android.intent.action.VIEW \
  -d 'https://www.youtube.com/watch?v={video_id}' \
  -n com.google.android.youtube/.WatchWhileActivity

# Spotify音乐投射
adb -s 127.0.0.1:5555 shell am start -a android.intent.action.VIEW \
  -d 'spotify:track:{track_id}' \
  -n com.spotify.music/.MainActivity

# 通用媒体URL投射
adb -s 127.0.0.1:5555 shell am start -a android.intent.action.VIEW \
  -d '{media_url}' \
  --es android.intent.extra.REFERRER_NAME 'Home Assistant'

# Netflix内容投射
adb -s 127.0.0.1:5555 shell am start -a android.intent.action.VIEW \
  -d 'https://www.netflix.com/watch/{video_id}' \
  -n com.netflix.mediaclient/.ui.launch.UIWebViewActivity
```

### 状态查询命令集合

#### Termux/Ubuntu环境优化命令
```python
STATE_COMMANDS = {
    # 媒体状态 - 完整指定设备
    "media_state": "adb -s {device_id} shell dumpsys media_session | awk '/Sessions Stack/...'",
    "volume_level": "adb -s {device_id} shell cmd media_session volume --stream 3 --get",
    
    # 电源状态 - 完整指定设备
    "power_state": "adb -s {device_id} shell dumpsys power | grep -E '(mWakefulness|mScreenOn)'",
    
    # 网络状态 - 完整指定设备
    "wifi_ssid": "adb -s {device_id} shell dumpsys wifi | grep 'SSID:' | head -1",
    "ip_address": "adb -s {device_id} shell ip addr show wlan0 | grep 'inet '",
    "wifi_state": "adb -s {device_id} shell settings get global wifi_on",
    
    # 应用状态 - 完整指定设备
    "current_app": "adb -s {device_id} shell dumpsys activity activities | grep 'ActivityRecord' | head -1",
    "current_activity": "adb -s {device_id} shell dumpsys activity top | grep ACTIVITY",
    "installed_apps": "adb -s {device_id} shell pm list packages -3",
    
    # 系统性能 - 完整指定设备，减少频率
    "cpu_memory_usage": "adb -s {device_id} shell top -d 1.0 -n 1",  # 降低采样频率
    "brightness_get": "adb -s {device_id} shell settings get system screen_brightness",
    "device_info": "adb -s {device_id} shell getprop",
    
    # Cast状态 - 完整指定设备
    "cast_sessions": "adb -s {device_id} shell dumpsys media_session | grep -A 5 'Sessions Stack'",
    "cast_receiver_status": "adb -s {device_id} shell dumpsys activity activities | grep 'CastReceiver'",
    
    # ISG监控命令 - 完整指定设备，优化性能
    "isg_process_status": "adb -s {device_id} shell ps | grep com.linknlink.app.device.isg",
    "isg_memory_usage": "adb -s {device_id} shell dumpsys meminfo com.linknlink.app.device.isg | head -20",  # 限制输出行数
    "isg_cpu_usage": "adb -s {device_id} shell top -p $(pidof com.linknlink.app.device.isg) -n 1",
    "isg_logcat": "adb -s {device_id} shell logcat -s ISG:* -v time -t 50",  # 减少日志行数
    "isg_crash_log": "adb -s {device_id} shell logcat -b crash -v time -t 25",  # 减少崩溃日志行数
    "isg_anr_log": "adb -s {device_id} shell logcat -s ActivityManager:* -v time -t 10 | grep ANR",
}

# 设置命令 - 完整指定设备
SET_COMMANDS = {
    # 音量控制 - 完整指定设备
    "set_volume": "adb -s {device_id} shell service call audio 12 i32 3 i32 {level} i32 0",
    
    # 亮度控制 - 完整指定设备
    "set_brightness": "adb -s {device_id} shell settings put system screen_brightness {level}",
    
    # 应用启动 - 完整指定设备
    "start_app": "adb -s {device_id} shell am start {package}",
    
    # ISG应用专用控制命令 - 完整指定设备
    "force_start_isg": "adb -s {device_id} shell am start -n com.linknlink.app.device.isg/.MainActivity --activity-clear-top",
    "force_stop_isg": "adb -s {device_id} shell am force-stop com.linknlink.app.device.isg",
    "restart_isg": "adb -s {device_id} shell 'am force-stop com.linknlink.app.device.isg && sleep 2 && am start -n com.linknlink.app.device.isg/.MainActivity'",
    "clear_isg_cache": "adb -s {device_id} shell pm clear com.linknlink.app.device.isg",
    
    # Google Cast控制 - 完整指定设备
    "cast_media": "adb -s {device_id} shell am start -a android.intent.action.VIEW -d '{media_url}' --es android.intent.extra.REFERRER_NAME '{app_name}'",
    "cast_image": "adb -s {device_id} shell am start -a android.intent.action.VIEW -t image/* -d '{image_url}'",
    "cast_video": "adb -s {device_id} shell am start -a android.intent.action.VIEW -t video/* -d '{video_url}'",
    "cast_audio": "adb -s {device_id} shell am start -a android.intent.action.VIEW -t audio/* -d '{audio_url}'",
}
```

---

## 实体定义

### 1. 媒体播放器实体 (Media Player)

**支持功能:**
- 播放控制 (播放/暂停/停止/下一首/上一首)
- 音量控制 (音量调节/静音/精确百分比设置)
- 电源控制 (开机/关机)
- Google Cast功能 (投射URL/YouTube/Netflix/Spotify)
- 媒体浏览 (应用快捷启动)

**状态属性:**
- 播放状态: `playing` / `paused` / `idle` / `off` / `standby`
- 音量级别: 0.0-1.0 (基于设备音量范围精确转换)
- 当前应用: 显示正在运行的媒体应用
- Cast状态: 当前投射会话信息

**立即状态查询实现:**
```python
async def async_set_volume_level(self, volume: float) -> None:
    """设置音量级别 - service call audio，立即查询状态"""
    volume_level = int(volume * self.coordinator.data.volume_max)
    success = await self.coordinator.adb_manager.set_volume(volume_level)
    
    if success:
        # 立即查询音量状态确认变化
        await asyncio.sleep(0.3)  # 短暂等待设置生效
        current_volume, max_volume, is_muted = await self.coordinator.adb_manager.get_volume_state()
        
        if current_volume is not None:
            self.coordinator.data.volume_level = current_volume
            self.coordinator.data.volume_max = max_volume
            self.coordinator.data.is_muted = is_muted
            self.coordinator.data.volume_percentage = (current_volume / max_volume) * 100 if max_volume > 0 else 0
            self.async_write_ha_state()
    
    await self.coordinator.async_request_refresh()
```

### 2. 开关实体 (Switch)

#### 电源开关
- 控制设备唤醒/休眠
- 状态基于 `mWakefulness` 判断

#### WiFi开关
- 控制WiFi开启/关闭
- 显示WiFi网络名称和IP地址

#### ADB连接开关
- 控制ADB连接状态
- 监控连接稳定性

### 3. 摄像头实体 (Camera)

**屏幕截图功能:**
- 实时屏幕截图
- 自动时间戳命名
- 保留最近N张截图 (可配置)
- 自动清理旧截图

### 4. 传感器实体 (Sensor)

#### 系统监控传感器
- **亮度传感器**: 当前屏幕亮度百分比
- **网络传感器**: WiFi连接状态和网络信息
- **应用传感器**: 当前前台应用信息
- **CPU传感器**: 系统CPU使用率
- **内存传感器**: 系统内存使用率

#### ISG专用传感器 (详见ISG监控模块)
- **ISG状态传感器**: ISG应用运行状态
- **ISG内存传感器**: ISG内存使用情况
- **ISG CPU传感器**: ISG CPU使用率
- **ISG运行时间传感器**: ISG连续运行时间
- **ISG崩溃计数传感器**: ISG崩溃次数和历史

### 5. 按键实体 (Button)

#### 导航按键
- 方向键: 上/下/左/右
- 功能键: 确定/返回/主页/菜单

#### 系统控制按键
- **刷新应用**: 获取已安装应用列表并更新配置
- **重启ISG**: 手动重启ISG应用
- **清理ISG缓存**: 清理ISG缓存并重启
- **ISG健康检查**: 执行ISG应用诊断

**立即状态查询实现:**
```python
class AndroidTVClearISGCacheButton(AndroidTVEntity, ButtonEntity):
    """清理ISG缓存按键，立即查询状态"""
    
    async def async_press(self) -> None:
        """清理ISG应用缓存，立即查询状态"""
        success = await self.coordinator.adb_manager.clear_isg_cache()
        if success:
            # 清理缓存后需要重启应用
            await asyncio.sleep(2)
            restart_success = await self.coordinator.adb_manager.force_start_isg()
            
            if restart_success:
                # 等待应用启动并立即检查状态
                await asyncio.sleep(3)
                
                # 立即查询ISG状态
                is_running = await self.coordinator.adb_manager.check_isg_process_status()
                if is_running:
                    self.coordinator.data.isg_running = True
                    self.coordinator.data.isg_health_status = "healthy"
                    self.coordinator.data.isg_last_start_time = datetime.now()
                    
                    # 立即查询内存使用情况
                    memory_mb, memory_pct = await self.coordinator.adb_manager.get_isg_memory_usage()
                    if memory_mb is not None:
                        self.coordinator.data.isg_memory_usage_mb = memory_mb
                        self.coordinator.data.isg_memory_percentage = memory_pct
        
        await self.coordinator.async_request_refresh()
```

### 6. 数值实体 (Number)

**亮度控制:**
- 范围: 0-255
- 模式: 滑动条
- 实时亮度调节

**立即状态查询实现:**
```python
async def async_set_native_value(self, value: float) -> None:
    """设置亮度值 - settings put system screen_brightness，立即查询状态"""
    brightness_level = int(value)
    success = await self.coordinator.adb_manager.set_brightness(brightness_level)
    
    if success:
        # 立即查询亮度状态确认变化
        await asyncio.sleep(0.3)  # 短暂等待设置生效
        current_brightness = await self.coordinator.adb_manager.get_brightness()
        
        if current_brightness is not None:
            self.coordinator.data.brightness = current_brightness
            self.coordinator.data.brightness_percentage = (current_brightness / 255) * 100
            self.async_write_ha_state()
    
    await self.coordinator.async_request_refresh()
```

### 7. 选择实体 (Select)

**应用选择器:**
- 选项来源: configuration.yaml中的apps配置
- 支持应用启动
- 显示当前运行应用

**立即状态查询实现:**
```python
async def async_select_option(self, option: str) -> None:
    """选择应用 - am start package_name，立即查询当前应用状态"""
    package_name = self.coordinator.config.get_app_package(option)
    if package_name:
        success = await self.coordinator.adb_manager.start_app(package_name)
        
        if success:
            # 立即查询当前应用状态
            await asyncio.sleep(2.0)  # 等待应用启动
            current_activity = await self.coordinator.adb_manager.get_current_activity()
            
            if current_activity:
                self.coordinator.data.update_app_from_output(current_activity)
                self.async_write_ha_state()
        
        await self.coordinator.async_request_refresh()
```

---

## ISG应用监控模块

### 监控目标
专门针对 `com.linknlink.app.device.isg` 应用的健康监控和自动维护。

### 核心功能

#### 1. 实时状态监控
```python
# ISG专用ADB命令
ISG_COMMANDS = {
    "process_status": "shell ps | grep com.linknlink.app.device.isg",
    "memory_usage": "shell dumpsys meminfo com.linknlink.app.device.isg", 
    "cpu_usage": "shell top -p $(pidof com.linknlink.app.device.isg) -n 1",
    "app_logs": "shell logcat -s ISG:* -v time -t 100",
    "crash_logs": "shell logcat -b crash -v time -t 50",
    "anr_logs": "shell logcat -s ActivityManager:* -v time | grep ANR",
    "network_status": "shell netstat -an | grep $(pidof com.linknlink.app.device.isg)",
    "storage_usage": "shell du -sh /data/data/com.linknlink.app.device.isg",
}
```

#### 2. 自动故障恢复
**重启条件:**
- ISG应用未运行
- 内存使用超过阈值 (默认80%)
- CPU使用超过阈值 (默认90%)
- 检测到崩溃或ANR事件
- 运行时间异常 (频繁重启检测)

**重启策略:**
```python
# 智能重启逻辑
def should_restart_isg(self) -> bool:
    if not self.isg_auto_restart_enabled:
        return False
    
    # 条件1: ISG未运行
    if not self.isg_running:
        return True
    
    # 条件2: 健康状态不佳且重试次数未超限
    if (self.isg_health_status in ["unhealthy", "crashed"] and 
        self.isg_restart_count < MAX_RESTART_ATTEMPTS):
        return True
    
    # 条件3: 避免频繁重启
    if self.isg_uptime_minutes < 5:
        return False  # 运行时间过短，暂不重启
        
    return False
```

#### 3. 健康状态评估
**状态等级:**
- `healthy`: 正常运行
- `unhealthy`: 性能异常但仍在运行
- `crashed`: 最近有崩溃事件
- `not_running`: 应用未运行
- `unknown`: 状态未知

**评估指标:**
- 进程存在性
- 内存使用率
- CPU使用率
- 崩溃频率
- ANR事件
- 运行稳定性

#### 4. 详细监控数据
```python
@dataclass
class ISGMonitoringData:
    # 运行状态
    isg_running: bool = False
    isg_pid: Optional[int] = None
    isg_uptime_minutes: int = 0
    isg_last_start_time: Optional[datetime] = None
    
    # 性能数据
    isg_memory_usage_mb: float = 0.0
    isg_memory_percentage: float = 0.0
    isg_cpu_usage: float = 0.0
    
    # 稳定性数据
    isg_crash_count: int = 0
    isg_last_crash_time: Optional[datetime] = None
    isg_last_crash_reason: Optional[str] = None
    isg_anr_count: int = 0
    isg_last_anr_time: Optional[datetime] = None
    
    # 维护数据
    isg_restart_count: int = 0
    isg_health_status: str = "unknown"
    isg_last_health_check: Optional[datetime] = None
    
    # 扩展监控
    isg_network_connections: int = 0
    isg_storage_usage_mb: float = 0.0
    isg_permission_issues: List[str] = field(default_factory=list)
```

### ISG监控实体

#### 传感器实体
- **sensor.android_tv_box_isg_status**: ISG应用状态
- **sensor.android_tv_box_isg_memory**: ISG内存使用(MB)
- **sensor.android_tv_box_isg_cpu**: ISG CPU使用率(%)
- **sensor.android_tv_box_isg_uptime**: ISG运行时间(分钟)
- **sensor.android_tv_box_isg_crash_count**: ISG崩溃计数

#### 控制按键
- **button.android_tv_box_restart_isg**: 重启ISG应用
- **button.android_tv_box_clear_isg_cache**: 清理ISG缓存
- **button.android_tv_box_isg_health_check**: ISG健康检查

### 自动化示例
```yaml
# ISG监控自动化
automation:
  # ISG崩溃警报
  - alias: "ISG App Crashed Alert"
    trigger:
      - platform: state
        entity_id: sensor.android_tv_box_isg_status
        to: "crashed"
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ ISG应用崩溃"
          message: "ISG应用已崩溃，正在自动重启..."

  # ISG内存使用过高
  - alias: "ISG High Memory Usage"
    trigger:
      - platform: numeric_state
        entity_id: sensor.android_tv_box_isg_memory
        above: 500  # 超过500MB
        for:
          minutes: 5
    action:
      - service: button.press
        target:
          entity_id: button.android_tv_box_clear_isg_cache

  # 定期健康检查
  - alias: "ISG Periodic Health Check"
    trigger:
      - platform: time_pattern
        hours: "/2"  # 每2小时
    condition:
      - condition: state
        entity_id: switch.android_tv_box_power
        state: "on"
    action:
      - service: button.press
        target:
          entity_id: button.android_tv_box_isg_health_check
```

---

## 性能优化策略

### 针对Termux/Ubuntu环境的优化

#### 1. 分层监控频率
```python
class OptimizedUpdateCoordinator:
    """针对低性能环境优化的协调器"""
    
    def __init__(self, hass, adb_manager, config):
        # 基础状态更新间隔：60秒 (减少频率)
        self.base_update_interval = timedelta(seconds=60)
        
        # 高频监控项目：5分钟 (仅在必要时)
        self.high_frequency_items = ["isg_status", "power_state"]
        self.high_frequency_interval = timedelta(minutes=5)
        
        # 低频监控项目：15分钟 (减少系统负载)
        self.low_frequency_items = ["device_info", "installed_apps", "network_info"]
        self.low_frequency_interval = timedelta(minutes=15)
        
        # 按需监控项目：仅在用户交互时
        self.on_demand_items = ["screenshot", "cast_status"]
    
    async def _smart_update_strategy(self):
        """智能更新策略"""
        current_time = datetime.now()
        
        # 基础状态 (每60秒)
        if self._should_update_basic(current_time):
            await self._update_basic_status()
        
        # 高频项目 (每5分钟)
        if self._should_update_high_frequency(current_time):
            await self._update_high_frequency()
        
        # 低频项目 (每15分钟)
        if self._should_update_low_frequency(current_time):
            await self._update_low_frequency()
```

#### 2. 命令缓存和去重
```python
class ADBCommandCache:
    """ADB命令缓存 - 减少重复执行"""
    
    def __init__(self, ttl_seconds: int = 30):
        self._cache = {}
        self._ttl = ttl_seconds
        self._pending_commands = {}  # 防止重复执行
    
    async def execute_cached(self, command: str, device_id: str) -> Tuple[str, str]:
        """执行缓存的命令"""
        full_command = command.format(device_id=device_id)
        cache_key = f"{device_id}_{hash(full_command)}"
        current_time = time.time()
        
        # 检查缓存
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if current_time - timestamp < self._ttl:
                return result
        
        # 检查是否有相同命令正在执行
        if cache_key in self._pending_commands:
            return await self._pending_commands[cache_key]
        
        # 执行命令
        future = asyncio.create_task(self._execute_command(full_command))
        self._pending_commands[cache_key] = future
        
        try:
            result = await future
            # 缓存结果
            self._cache[cache_key] = (result, current_time)
            return result
        finally:
            # 清理pending
            self._pending_commands.pop(cache_key, None)
```

#### 3. 批量操作优化
```python
class BatchADBOperations:
    """批量ADB操作 - 减少连接开销"""
    
    async def batch_status_check(self, device_id: str) -> Dict[str, Any]:
        """批量状态检查 - 单次连接执行多个命令"""
        
        # 组合多个命令到一次shell会话中
        combined_command = f'''
        adb -s {device_id} shell '
        echo "POWER_STATE:"; dumpsys power | grep -E "(mWakefulness|mScreenOn)";
        echo "VOLUME_STATE:"; cmd media_session volume --stream 3 --get;
        echo "WIFI_STATE:"; settings get global wifi_on;
        echo "BRIGHTNESS:"; settings get system screen_brightness;
        echo "CURRENT_APP:"; dumpsys activity top | grep ACTIVITY | head -1;
        '
        '''
        
        try:
            stdout, stderr = await self._execute_with_timeout(combined_command, timeout=15)
            return self._parse_batch_output(stdout)
        except Exception as e:
            self.logger.error(f"Batch command failed: {e}")
            return {}
```

#### 4. 条件式监控
```python
class ConditionalMonitoring:
    """条件式监控 - 仅在必要时执行"""
    
    async def smart_update(self, coordinator) -> bool:
        """智能更新决策"""
        
        # 如果设备离线，跳过详细检查
        if not await self._quick_connectivity_check(coordinator.device_id):
            self._skip_detailed_check = True
            return False
        
        # 如果设备休眠，减少监控频率
        power_state = await self._get_power_state_quick(coordinator.device_id)
        if power_state == "off":
            # 设备关机时，每5分钟检查一次即可
            if self._should_skip_offline_check():
                return False
        
        return True
```

#### 5. 资源限制和清理
```python
class ResourceManager:
    """资源管理 - 控制系统资源使用"""
    
    def __init__(self):
        self._max_concurrent_commands = 2  # 限制并发ADB命令数
        self._command_semaphore = asyncio.Semaphore(self._max_concurrent_commands)
        self._cleanup_interval = 300  # 5分钟清理一次
        
    async def execute_with_resource_limit(self, command: str) -> Tuple[str, str]:
        """资源限制的命令执行"""
        async with self._command_semaphore:
            return await self._execute_command(command)
    
    async def periodic_cleanup(self):
        """定期清理任务"""
        while True:
            await asyncio.sleep(self._cleanup_interval)
            
            # 清理缓存
            self._cleanup_cache()
            
            # 清理临时文件
            self._cleanup_temp_files()
            
            # 检查内存使用
            await self._check_memory_usage()
```

### 立即状态查询实现策略

#### 核心原则
```python
class ImmediateStateRefresh:
    """立即状态查询策略"""
    
    async def control_with_immediate_feedback(self, control_action, state_query, wait_time=0.5):
        """控制操作 + 立即状态查询的通用模式"""
        
        # 1. 执行控制命令
        success = await control_action()
        
        if success:
            # 2. 短暂等待命令生效
            await asyncio.sleep(wait_time)
            
            # 3. 立即查询对应状态
            new_state = await state_query()
            
            # 4. 更新本地状态并触发UI更新
            if new_state is not None:
                self.update_local_state(new_state)
                self.async_write_ha_state()  # 立即更新UI
        
        # 5. 请求完整刷新 (可选，用于获取其他可能的状态变化)
        await self.coordinator.async_request_refresh()
```

#### 不同操作的等待时间优化
```python
IMMEDIATE_FEEDBACK_TIMINGS = {
    # 音量控制 - 响应快
    "volume": 0.3,      # 300ms
    "mute": 0.3,        # 300ms
    
    # 媒体控制 - 需要等待状态变化
    "media_play": 0.5,  # 500ms
    "media_pause": 0.5, # 500ms
    "media_stop": 0.8,  # 800ms
    
    # 电源控制 - 需要更长时间
    "power_on": 1.0,    # 1秒
    "power_off": 1.0,   # 1秒
    
    # 网络控制 - 状态变化较慢
    "wifi_toggle": 1.0, # 1秒
    "wifi_connect": 2.0, # 2秒 (等待连接建立)
    
    # 应用控制 - 需要启动时间
    "app_start": 2.0,   # 2秒
    "app_switch": 1.0,  # 1秒
    
    # ISG控制 - 应用操作需要时间
    "isg_restart": 3.0, # 3秒
    "isg_start": 3.0,   # 3秒
    "isg_cache_clear": 2.0, # 2秒
    
    # 亮度控制 - 响应快
    "brightness": 0.3,  # 300ms
}
```

---

## 配置与部署

### 安装要求

#### 系统依赖
- Android Debug Bridge (adb) 必须安装且在PATH中可访问
- Python 3.9+ (包含在Home Assistant中)

#### Python依赖
```json
"requirements": [
  "adb-shell>=0.4.4",
  "pure-python-adb>=0.3.0"
]
```

### 配置流程

#### 1. 设备连接配置
- IP地址: Android TV盒子的IP地址
- ADB端口: 通常为5555
- 设备名称: 自定义友好名称

#### 2. 高级选项配置
- 截图路径和保留数量
- 更新间隔设置
- 性能监控阈值
- ISG监控参数

#### 3. 应用配置
```yaml
apps:
  YouTube: com.google.android.youtube
  Netflix: com.netflix.mediaclient
  Spotify: com.spotify.music
  iSG: com.linknlink.app.device.isg
  
visible:
  - YouTube
  - Netflix
  - Spotify
  - iSG
```

### 完整配置示例
```yaml
android_tv_box:
  # 设备连接
  host: "192.168.1.100"
  port: 5555
  device_name: "Living Room TV Box"
  
  # 基础功能
  screenshot_path: "/sdcard/isgbackup/screenshot/"
  screenshot_keep_count: 3
  update_interval: 60  # 针对Termux/Ubuntu优化
  performance_check_interval: 2000  # 性能检查2秒间隔
  adb_timeout: 15  # ADB命令超时15秒
  max_concurrent_commands: 2  # 最大并发命令数
  
  # ISG监控
  isg_monitoring: true
  isg_check_interval: 120  # ISG检查间隔2分钟
  isg_auto_restart: true
  isg_crash_log_lines: 25  # 减少日志行数
  isg_memory_threshold: 85  # 提高内存阈值
  isg_cpu_threshold: 95  # 提高CPU阈值
  isg_restart_attempts: 3
  isg_health_check_timeout: 30
  
  # 缓存配置
  enable_command_cache: true  # 启用命令缓存
  cache_ttl: 30  # 缓存30秒
  enable_batch_operations: true  # 启用批量操作
  
  # 条件监控
  smart_monitoring: true  # 启用智能监控
  skip_when_offline: true  # 离线时跳过检查
  reduce_frequency_when_idle: true  # 空闲时降低频率
  
  # 资源限制
  max_log_size_mb: 1  # 限制日志大小
  enable_periodic_cleanup: true  # 启用定期清理
  memory_usage_threshold: 80  # 内存使用阈值
  
  # 应用配置
  apps:
    YouTube: com.google.android.youtube
    Netflix: com.netflix.mediaclient
    Spotify: com.spotify.music
    iSG: com.linknlink.app.device.isg
    
  visible:
    - YouTube
    - Netflix
    - Spotify
    - iSG
```

### 部署步骤

#### HACS安装
1. **添加自定义仓库**: 在HACS中添加GitHub仓库地址
2. **搜索集成**: 在HACS集成页面搜索"Android TV Box"
3. **安装集成**: 点击安装并重启Home Assistant
4. **配置设备**: 通过集成页面添加Android TV Box设备

#### 手动安装
```bash
# 1. 下载代码到custom_components目录
cd /config/custom_components
git clone https://github.com/username/android-tv-box-integration.git android_tv_box

# 2. 安装依赖 (如果需要)
pip install "adb-shell>=0.4.4" "pure-python-adb>=0.3.0"

# 3. 重启Home Assistant
# 4. 通过UI配置集成
```

---

## 开发指南

### 数据模型
```python
@dataclass
class AndroidTVState:
    """Android TV设备完整状态"""
    # 连接状态
    is_connected: bool = False
    last_seen: Optional[datetime] = None
    
    # 电源状态
    power_state: str = "unknown"  # on, off, standby
    screen_on: bool = False
    wakefulness: Optional[str] = None
    
    # 媒体状态
    media_state: str = "idle"
    volume_level: int = 0
    volume_max: int = 15
    volume_percentage: float = 0.0
    is_muted: bool = False
    
    # Cast状态
    cast_active: bool = False
    cast_app: Optional[str] = None
    cast_media_title: Optional[str] = None
    
    # ISG监控状态
    isg_running: bool = False
    isg_memory_usage_mb: float = 0.0
    isg_cpu_usage: float = 0.0
    isg_uptime_minutes: int = 0
    isg_crash_count: int = 0
    isg_health_status: str = "unknown"
    
    # 应用和网络状态
    current_app_package: Optional[str] = None
    wifi_enabled: bool = True
    ip_address: Optional[str] = None
    
    # 系统性能
    brightness: int = 128
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
```

### ADB管理器接口
```python
class ADBManagerInterface(ABC):
    """ADB管理器统一接口"""
    
    # 连接管理
    @abstractmethod
    async def connect(self) -> bool:
        """连接到设备"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """检查连接状态"""
        pass
    
    # 媒体控制
    @abstractmethod
    async def media_play(self) -> bool:
        """播放媒体"""
        pass
    
    @abstractmethod
    async def set_volume(self, level: int) -> bool:
        """设置音量级别 (0到最大音量级别)"""
        pass
    
    @abstractmethod
    async def get_volume_state(self) -> Tuple[int, int, bool]:
        """获取音量状态 (当前音量, 最大音量, 是否静音)"""
        pass
    
    # 电源管理
    @abstractmethod
    async def power_on(self) -> bool:
        """唤醒设备"""
        pass
    
    @abstractmethod
    async def get_power_state(self) -> Tuple[str, bool]:
        """获取电源状态 (电源状态, 屏幕开关)"""
        pass
    
    # Cast功能
    @abstractmethod
    async def cast_media_url(self, url: str, media_type: str = "video") -> bool:
        """投射媒体URL"""
        pass
    
    @abstractmethod
    async def cast_youtube_video(self, video_id_or_url: str) -> bool:
        """投射YouTube视频"""
        pass
    
    # ISG监控
    @abstractmethod
    async def check_isg_process_status(self) -> bool:
        """检查ISG进程状态"""
        pass
    
    @abstractmethod
    async def force_restart_isg(self) -> bool:
        """强制重启ISG应用"""
        pass
    
    @abstractmethod
    async def perform_isg_health_check(self) -> Dict[str, Any]:
        """执行ISG健康检查"""
        pass
```

### 实体基类
```python
class AndroidTVEntity(CoordinatorEntity[AndroidTVUpdateCoordinator]):
    """Android TV实体基类"""
    
    def __init__(self, coordinator, entity_key: str, entity_name: str):
        super().__init__(coordinator)
        self._entity_key = entity_key
        self._entity_name = entity_name
        
    @property
    def device_info(self) -> Dict[str, Any]:
        """设备信息"""
        return {
            "identifiers": {("android_tv_box", self.coordinator.config.device_address)},
            "name": self.coordinator.config.device_name,
            "manufacturer": "Android TV Box",
            "model": self.coordinator.data.device_model or "Unknown",
            "sw_version": self.coordinator.data.android_version,
        }
    
    @property
    def unique_id(self) -> str:
        """唯一ID"""
        return f"android_tv_box_{self.coordinator.config.device_address}_{self._entity_key}"
    
    @property
    def available(self) -> bool:
        """实体可用性"""
        return self.coordinator.data.is_connected
```

### 错误处理和日志
```python
class AndroidTVError(Exception):
    """Android TV集成基础异常"""
    pass

class ConnectionError(AndroidTVError):
    """连接错误"""
    pass

class CommandError(AndroidTVError):
    """命令执行错误"""
    pass

def handle_adb_errors(default_return: Any = None):
    """ADB错误处理装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except asyncio.TimeoutError:
                _LOGGER.error(f"Timeout executing {func.__name__}")
                return default_return
            except Exception as e:
                _LOGGER.exception(f"Error in {func.__name__}: {e}")
                return default_return
        return wrapper
    return decorator
```

---

## 故障排除

### 常见问题

#### 1. ADB连接失败
**可能原因:**
- Android设备ADB调试未开启
- IP地址或端口错误
- 网络连通性问题
- 防火墙阻止连接

**解决方法:**
```bash
# 检查ADB连接
adb devices
adb connect 192.168.1.100:5555

# 测试设备响应
adb -s 192.168.1.100:5555 shell echo "test"

# 检查网络连通性
ping 192.168.1.100
telnet 192.168.1.100 5555
```

#### 2. ISG应用监控异常
**可能原因:**
- ISG应用未安装
- 应用包名不正确
- 权限设置问题

**解决方法:**
```bash
# 检查ISG应用是否安装
adb shell pm list packages | grep isg

# 检查应用进程
adb shell ps | grep com.linknlink.app.device.isg

# 手动启动应用
adb shell am start -n com.linknlink.app.device.isg/.MainActivity
```

#### 3. 音量控制不响应
**可能原因:**
- 音频流设置错误
- 设备音量范围未正确识别
- 媒体会话状态问题

**解决方法:**
```bash
# 检查音频流状态
adb shell cmd media_session volume --stream 3 --get

# 检查媒体会话
adb shell dumpsys media_session

# 手动设置音量
adb shell service call audio 12 i32 3 i32 8 i32 0
```

### 日志分析
```bash
# 查看Home Assistant日志
tail -f /config/home-assistant.log | grep android_tv_box

# 查看特定组件日志
grep "AndroidTV" /config/home-assistant.log

# 调试模式日志配置
logger:
  default: info
  logs:
    custom_components.android_tv_box: debug
```

### 性能诊断
```python
# 交互式测试脚本
class AndroidTVDebugger:
    """调试工具"""
    
    async def run_diagnostics(self, host: str, port: int):
        """运行诊断"""
        print("🔍 Android TV Box 诊断工具")
        print("=" * 40)
        
        # 连接测试
        adb = ADBManager(host, port)
        connected = await adb.connect()
        print(f"连接状态: {'✅ 成功' if connected else '❌ 失败'}")
        
        if not connected:
            return
        
        # 基础信息
        device_info = await adb.get_device_info()
        print(f"设备型号: {device_info.get('model', 'Unknown')}")
        print(f"Android版本: {device_info.get('android_version', 'Unknown')}")
        
        # 电源状态
        power_state, screen_on = await adb.get_power_state()
        print(f"电源状态: {power_state} (屏幕: {'开' if screen_on else '关'})")
        
        # 音量状态
        volume, max_vol, muted = await adb.get_volume_state()
        volume_pct = (volume / max_vol) * 100 if max_vol > 0 else 0
        print(f"音量: {volume}/{max_vol} ({volume_pct:.0f}%) {'🔇' if muted else '🔊'}")
        
        # ISG状态
        isg_running = await adb.check_isg_process_status()
        print(f"ISG状态: {'✅ 运行中' if isg_running else '❌ 未运行'}")
        
        if isg_running:
            health = await adb.perform_isg_health_check()
            print(f"ISG健康: {health.get('health_status', 'unknown')}")
            print(f"ISG内存: {health.get('memory_usage', 0):.1f}MB")
            print(f"ISG CPU: {health.get('cpu_usage', 0):.1f}%")
```

### 更新和升级
```yaml
# 版本检查自动化
automation:
  - alias: "Check Android TV Box Integration Updates"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: hassio.addon_update
        data:
          addon: android_tv_box
```

---

## 扩展功能规划

### 未来功能规划

#### 1. 高级监控
- **温度监控**: 设备温度过高时自动降频
- **网络质量监控**: 延迟、丢包率监控
- **存储健康**: 磁盘空间和IO性能监控
- **电池状态**: 对于便携式设备的电池监控

#### 2. 智能化功能
- **使用模式学习**: 分析用户使用习惯
- **预测性维护**: 基于历史数据预测故障
- **自适应优化**: 根据设备性能自动调整参数
- **场景模式**: 预设的环境配置（影院、游戏、音乐）

#### 3. 多设备支持
- **设备群组管理**: 统一控制多个Android TV
- **负载均衡**: 智能分配任务到不同设备
- **同步播放**: 多设备同步媒体播放
- **备份设备**: 主设备故障时自动切换

#### 4. 第三方集成
- **Plex服务器集成**: 直接控制Plex播放
- **Kodi集成**: 深度Kodi媒体中心控制
- **智能家居联动**: 与更多智能设备协同
- **云服务集成**: Google Drive、OneDrive等

### 社区贡献指南

#### 开发环境设置
```bash
# 1. Fork项目
git fork https://github.com/username/android-tv-box-integration

# 2. 创建开发分支
git checkout -b feature/new-feature

# 3. 安装开发依赖
pip install -r requirements-dev.txt

# 4. 运行测试
pytest tests/ -v

# 5. 代码质量检查
black src/ tests/
flake8 src/ tests/
mypy src/
```

#### 贡献类型
- **Bug修复**: 修复现有功能问题
- **新功能**: 添加新的设备控制功能
- **文档改进**: 完善使用说明和API文档
- **测试扩展**: 增加测试覆盖率
- **性能优化**: 提升响应速度和稳定性

#### 提交规范
```
类型(范围): 简短描述

详细描述改动内容和原因

修复: #issue_number
```

---

## 使用示例

### 媒体播放控制
```yaml
# 播放YouTube视频
service: media_player.play_media
target:
  entity_id: media_player.android_tv_box_media_player
data:
  media_content_type: "youtube"
  media_content_id: "dQw4w9WgXcQ"

# 设置音量到75%
service: media_player.volume_set
target:
  entity_id: media_player.android_tv_box_media_player
data:
  volume_level: 0.75

# 投射在线视频
service: media_player.play_media
target:
  entity_id: media_player.android_tv_box_media_player
data:
  media_content_type: "video"
  media_content_id: "https://example.com/video.mp4"
```

### 设备控制
```yaml
# 开机并启动应用
script:
  morning_tv_routine:
    sequence:
      - service: media_player.turn_on
        target:
          entity_id: media_player.android_tv_box_media_player
      - delay: "00:00:05"
      - service: select.select_option
        target:
          entity_id: select.android_tv_box_app_selector
        data:
          option: "YouTube"
```

### ISG应用管理
```yaml
# ISG故障诊断
script:
  isg_diagnostic:
    sequence:
      - service: button.press
        target:
          entity_id: button.android_tv_box_isg_health_check
      - delay: "00:00:10"
      - choose:
          - conditions:
              - condition: state
                entity_id: sensor.android_tv_box_isg_status
                state: "not_running"
            sequence:
              - service: button.press
                target:
                  entity_id: button.android_tv_box_restart_isg
          - conditions:
              - condition: state
                entity_id: sensor.android_tv_box_isg_status
                state: "unhealthy"
            sequence:
              - service: button.press
                target:
                  entity_id: button.android_tv_box_clear_isg_cache
```

### 自动化场景
```yaml
automation:
  # 家庭影院模式
  - alias: "Movie Mode"
    trigger:
      - platform: state
        entity_id: media_player.android_tv_box_media_player
        attribute: cast_media_type
        to: "video"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 20
      - service: number.set_value
        target:
          entity_id: number.android_tv_box_brightness_control
        data:
          value: 100

  # 深夜自动关机
  - alias: "Auto Sleep"
    trigger:
      - platform: time
        at: "02:00:00"
    action:
      - service: media_player.turn_off
        target:
          entity_id: media_player.android_tv_box_media_player

  # 智能音量调节
  - alias: "Smart Volume Control"
    trigger:
      - platform: time
        at: "22:00:00"  # 晚上10点
    condition:
      - condition: state
        entity_id: media_player.android_tv_box_media_player
        state: "playing"
    action:
      - service: media_player.volume_set
        target:
          entity_id: media_player.android_tv_box_media_player
        data:
          volume_level: 0.3  # 降低到30%音量
```

---

## 测试和验证

### 单元测试结构
```python
class TestAndroidTVIntegration:
    """集成测试"""
    
    @pytest.fixture
    def mock_adb_manager(self):
        """模拟ADB管理器"""
        manager = Mock(spec=ADBManagerInterface)
        manager.connect = AsyncMock(return_value=True)
        manager.execute_command = AsyncMock(return_value=("success", ""))
        return manager
    
    @pytest.mark.asyncio
    async def test_media_player_volume_control(self, coordinator, mock_adb_manager):
        """测试媒体播放器音量控制"""
        # 设置模拟返回值
        mock_adb_manager.get_volume_state = AsyncMock(return_value=(8, 15, False))
        
        # 创建媒体播放器实体
        media_player = AndroidTVMediaPlayer(coordinator)
        
        # 测试音量设置
        await media_player.async_set_volume_level(0.75)
        
        # 验证ADB命令被正确调用
        expected_level = int(0.75 * 15)  # 11
        mock_adb_manager.set_volume.assert_called_with(expected_level)
    
    @pytest.mark.asyncio
    async def test_isg_monitoring(self, coordinator, mock_adb_manager):
        """测试ISG监控功能"""
        # 模拟ISG进程检查
        mock_adb_manager.check_isg_process_status = AsyncMock(return_value=True)
        
        # 执行监控
        await coordinator._check_isg_status(coordinator.data)
        
        # 验证状态更新
        assert coordinator.data.isg_running is True
```

### 集成测试
```python
class TestRealDevice:
    """真实设备测试 (需要实际Android设备)"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_device_connection(self, real_device_ip):
        """测试真实设备连接"""
        adb = ADBManager(real_device_ip, 5555)
        connected = await adb.connect()
        assert connected is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_volume_control_end_to_end(self, real_device_ip):
        """端到端音量控制测试"""
        adb = ADBManager(real_device_ip, 5555)
        await adb.connect()
        
        # 获取初始音量
        current, max_vol, muted = await adb.get_volume_state()
        
        # 设置新音量
        new_level = max_vol // 2
        success = await adb.set_volume(new_level)
        assert success is True
        
        # 验证音量变化
        new_current, _, _ = await adb.get_volume_state()
        assert abs(new_current - new_level) <= 1  # 允许1级误差
```

---

## 结语

这个Android TV Box HACS Integration设计文档提供了完整的功能规范和实现指南。主要特色包括：

### 核心优势
- **完整的媒体控制**: 播放、音量、Cast功能
- **全面的设备管理**: 电源、网络、应用控制
- **智能监控系统**: 性能监控和健康评估
- **专业ISG监控**: 针对性的应用健康管理
- **立即状态反馈**: 控制操作后立即显示状态变化

### 技术特点
- **模块化设计**: 清晰的代码组织和接口定义
- **异步编程**: 高性能的并发处理
- **错误恢复**: 稳定的连接和故障处理
- **可配置性**: 灵活的参数调整
- **性能优化**: 针对Termux/Ubuntu环境优化

### 用户体验
- **直观界面**: 丰富的实体类型和控制选项
- **自动化友好**: 完善的状态属性和服务接口
- **智能告警**: 主动的异常检测和通知
- **场景联动**: 与智能家居生态深度集成

### 扩展性
- **插件化架构**: 易于添加新功能
- **标准接口**: 符合Home Assistant开发规范
- **社区驱动**: 开放的贡献和合作机制

现在你可以将这个完整的设计文档提供给开发团队，用于实现一个功能完整、架构清晰、代码质量高的HACS Integration项目。

### 环境准备建议

#### Termux/Ubuntu优化部署
```bash
# Termux环境
pkg update && pkg upgrade
pkg install python adb git

# Ubuntu环境  
apt update && apt upgrade
apt install python3 python3-pip adb git

# 安装Home Assistant和依赖
pip install homeassistant adb-shell pure-python-adb

# 优化ADB连接
adb start-server
adb connect 127.0.0.1:5555

# 设置ADB环境变量
export ADB_VENDOR_KEYS=/data/misc/adb/adb_keys
export ANDROID_ADB_SERVER_PORT=5037

# 限制并发进程
ulimit -u 100

# 设置内存限制
ulimit -v 1048576  # 1GB虚拟内存限制
```

这些优化确保在Termux/Ubuntu环境中运行时：

- 所有ADB命令都包含设备指定 (`-s 127.0.0.1:5555`)
- 大幅降低查询频率 (60秒基础间隔，2分钟ISG检查)
- 减少系统资源消耗 (批量操作、命令缓存、资源限制)
- 智能监控策略 (条件式更新、分层频率)
- 弹性错误处理 (降级策略、缓存fallback)
- 优化日志记录 (缓冲写入、减少I/O)

用户现在可以看到：
- 调节音量后立即看到音量条变化
- 开关机后立即看到电源状态更新
- 切换应用后立即看到当前应用变化
- ISG操作后立即看到健康状态更新

这大大提升了用户体验，让控制操作感觉更加响应和可靠。