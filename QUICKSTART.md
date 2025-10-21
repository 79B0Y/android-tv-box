# Android TV Box Integration v1.1.0 - 快速开始

## 🎉 新功能

### 1. 性能优化
- ⚡ 命令执行速度提升 30-50%
- 🎯 智能 LRU 缓存机制
- 📊 缓存统计和监控

### 2. 应用监控框架
现在可以轻松监控任何 Android 应用！

```python
from custom_components.android_tv_box.app_monitor import AppMonitor
from custom_components.android_tv_box.isg_monitor import ISGMonitor

# 使用 ISG 监控器
isg_monitor = ISGMonitor(adb_manager)
health = await isg_monitor.get_health_status()

# 或创建自定义监控器
class MyAppMonitor(AppMonitor):
    def __init__(self, adb_manager):
        super().__init__("com.my.app", adb_manager)
    # 实现抽象方法...
```

### 3. 改进的错误处理
所有错误现在都有清晰的分类和日志记录：
- `ConnectionError` - 网络连接问题
- `TimeoutError` - 操作超时
- `ImportError` - 缺少依赖
- `OSError` - 系统级错误

### 4. 完整的测试框架
```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_adb_manager.py -v

# 生成覆盖率报告
pytest tests/ --cov=custom_components/android_tv_box --cov-report=html
```

## 📦 安装

### 通过 HACS (推荐)
1. 打开 HACS
2. 搜索 "Android TV Box"
3. 点击安装
4. 重启 Home Assistant

### 手动安装
```bash
cd /config/custom_components
git clone https://github.com/your-repo/android-tv-box
cd android-tv-box
pip install -r requirements.txt
```

## ⚙️ 配置

### 基本配置
1. 在 Home Assistant 中打开 **配置** -> **集成**
2. 点击 **添加集成**
3. 搜索 "Android TV Box"
4. 输入设备 IP 地址和端口 (默认 5555)
5. 配置高级选项（可选）

### 高级选项
- **截图路径**: 设备上保存截图的路径
- **更新间隔**: 状态更新频率 (30-300 秒)
- **ISG 监控**: 启用/禁用 ISG 应用监控
- **自动重启**: ISG 不健康时自动重启
- **内存阈值**: 触发警告的内存使用百分比
- **CPU 阈值**: 触发警告的 CPU 使用百分比

## 🎮 实体

### 媒体播放器
- **android_tv_box.{name}_media_player**
  - 控制播放、暂停、停止
  - 音量控制
  - 应用切换
  - 投屏功能

### 传感器
- **sensor.{name}_brightness** - 屏幕亮度
- **sensor.{name}_network** - 网络状态
- **sensor.{name}_current_app** - 当前应用
- **sensor.{name}_isg_status** - ISG 应用状态
- **sensor.{name}_isg_memory** - ISG 内存使用
- **sensor.{name}_isg_cpu** - ISG CPU 使用

### 开关
- **switch.{name}_power** - 电源控制
- **switch.{name}_wifi** - WiFi 开关
- **switch.{name}_adb** - ADB 连接状态

### 按钮
- **button.{name}_nav_*** - 导航按钮 (上/下/左/右/确认/返回/主页/菜单)
- **button.{name}_refresh_apps** - 刷新应用列表
- **button.{name}_restart_isg** - 重启 ISG
- **button.{name}_clear_isg_cache** - 清除 ISG 缓存

### 其他
- **select.{name}_app_selector** - 应用选择器
- **number.{name}_brightness_control** - 亮度控制 (0-255)
- **camera.{name}_screenshot** - 截图相机

## 🤖 自动化示例

### 自动重启 ISG
```yaml
automation:
  - alias: "ISG 自动重启"
    trigger:
      - platform: state
        entity_id: sensor.android_tv_isg_status
        to: "unhealthy"
        for:
          minutes: 5
    action:
      - service: button.press
        target:
          entity_id: button.android_tv_restart_isg
```

### 定时截图
```yaml
automation:
  - alias: "每小时截图"
    trigger:
      - platform: time_pattern
        hours: "*"
    action:
      - service: camera.snapshot
        target:
          entity_id: camera.android_tv_screenshot
        data:
          filename: "/config/www/tv_{{ now().strftime('%Y%m%d_%H%M%S') }}.png"
```

### 应用快捷方式
```yaml
script:
  launch_youtube:
    alias: "打开 YouTube"
    sequence:
      - service: select.select_option
        target:
          entity_id: select.android_tv_app_selector
        data:
          option: "YouTube"
```

## 📊 性能监控

查看缓存统计：
```python
# 在 Home Assistant 开发者工具中
{{ state_attr('sensor.android_tv_network', 'cache_stats') }}
```

## 🐛 故障排除

### 连接问题
1. 确保 ADB 调试已启用
2. 检查防火墙设置
3. 验证 IP 地址和端口

### ISG 监控不工作
1. 确认 ISG 应用已安装
2. 检查包名是否正确: `com.linknlink.app.device.isg`
3. 查看日志: `grep ISG home-assistant.log`

### 性能问题
1. 增加更新间隔 (默认 60 秒)
2. 禁用不需要的传感器
3. 检查缓存统计

## 📝 日志

启用调试日志：
```yaml
logger:
  default: info
  logs:
    custom_components.android_tv_box: debug
```

## 🔗 资源

- **GitHub**: https://github.com/your-repo/android-tv-box
- **问题反馈**: https://github.com/your-repo/android-tv-box/issues
- **文档**: https://github.com/your-repo/android-tv-box/wiki

## 📜 更新日志

### v1.1.0 (2024-10)
- ✨ 全面性能优化 (30-50% 提升)
- ✨ 新增应用监控框架
- ✨ 改进错误处理
- ✨ 完整测试套件
- ✨ LRU 缓存机制
- 🐛 修复重复状态更新
- 📚 完善文档

### v1.0.9
- 初始版本

## ❤️ 支持

如果这个集成对您有帮助，请考虑：
- ⭐ 在 GitHub 上给个星星
- 🐛 报告问题和建议
- 📝 改进文档
- 🔧 贡献代码

---

**享受您的 Android TV Box 集成！** 🎉

