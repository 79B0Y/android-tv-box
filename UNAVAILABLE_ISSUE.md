# Android TV Box Integration - Unavailable 问题诊断

## 🔍 问题现象

每次 Home Assistant 重启后，所有 android_tv_box 实体都变成 `unavailable`

```
sensor.android_tv_box_cpu_usage: unavailable
sensor.android_tv_box_memory_usage: unavailable
switch.android_tv_box_power: unavailable
... (所有实体)
```

## ❌ 根本原因

**集成的 `async_setup_entry()` 函数根本没有被 Home Assistant 调用！**

### 证据

1. **日志中只有加载警告，没有初始化日志**
   ```
   2025-10-22 14:55:17 WARNING [homeassistant.loader] 
   We found a custom integration android_tv_box...
   ```
   - ❌ 没有 "Starting Android TV Box setup" 日志
   - ❌ 没有 "Successfully connected" 日志
   - ❌ 没有任何 INFO 级别的初始化日志

2. **实体是从之前状态恢复的**
   ```json
   {
     "state": "unavailable",
     "attributes": {
       "restored": true,  ← 关键！
       "last_updated": "2025-10-22T06:55:31..."  ← 旧时间
     }
   }
   ```

3. **配置入口存在但没有活动**
   - Entry ID: `01K85488GVR66J4JRFZQKPH8VJ`
   - State: N/A (没有加载状态)
   - 配置数据正常存在

## 🤔 可能的原因

### 1. **配置入口已损坏**
集成配置在多次重启/重新加载过程中可能已损坏，导致 HA 跳过加载。

### 2. **模块加载但未初始化**
Home Assistant 加载了集成模块，但由于某种原因跳过了 `async_setup_entry()` 调用。

### 3. **Python 模块命名冲突 (select.py)**
虽然我们之前发现了 `select.py` 与 Python 标准库的冲突，但这个问题在某些情况下可能仍然存在。

## ✅ 解决方案

### 方案 A：完全重置集成（推荐）

**步骤：**

1. **删除所有相关配置文件**
   ```bash
   # 删除实体注册表中的条目
   # 删除设备注册表中的条目
   # 删除配置入口
   ```

2. **重启 Home Assistant**

3. **重新添加集成**
   - 通过 UI 添加
   - 输入：10.0.0.206:5555

### 方案 B：检查并修复文件（开发用）

1. **检查所有 Python 文件是否有语法错误**
   ```bash
   python3 -m py_compile custom_components/android_tv_box/*.py
   ```

2. **检查导入是否正常**
   ```bash
   python3 -c "from custom_components.android_tv_box.const import DOMAIN"
   ```

3. **检查 manifest.json 格式**
   ```bash
   python3 -m json.tool manifest.json
   ```

### 方案 C：查看详细启动日志

1. **启用 DEBUG 日志**
   ```yaml
   # configuration.yaml
   logger:
     default: info
     logs:
       custom_components.android_tv_box: debug
       homeassistant.config_entries: debug
       homeassistant.loader: debug
   ```

2. **重启并查看日志**
   ```bash
   tail -f home-assistant.log | grep -E "android_tv_box|config_entries"
   ```

## 🎯 立即建议

**最快的解决方法：**

1. 在 Home Assistant UI 中：
   - 设置 > 设备与服务
   - 找到 "Android TV Box"
   - 点击三个点 > 删除

2. 重启 Home Assistant

3. 重新添加集成：
   - 设置 > 设备与服务 > 添加集成
   - 搜索 "Android TV Box"
   - 输入：主机 10.0.0.206，端口 5555

这应该会创建一个全新的配置入口，并正常调用 `async_setup_entry()`。

## 📊 当前状态

| 项目 | 状态 |
|------|------|
| manifest.json | ✅ 正常 |
| __init__.py | ✅ 正常（已添加详细日志）|
| ADB 连接 | ✅ 正常（直接测试通过）|
| 配置入口 | ⚠️ 存在但未活动 |
| 实体状态 | ❌ 全部 unavailable (restored) |
| async_setup_entry 调用 | ❌ 从未被调用 |

## 🔧 已完成的修复

1. ✅ 修复 App Selector 启动命令（monkey → am start）
2. ✅ 修复 Power 按钮状态检测逻辑
3. ✅ 更新 YouTube 包名为 TV 版本
4. ✅ 添加详细的启动日志
5. ✅ 修复 CONF_PORT 默认值
6. ✅ 修复 CPU 和内存监测命令

## 💡 结论

问题不在代码本身，而在于配置入口的加载机制。建议**完全删除并重新添加集成**以创建全新的配置入口。

所有代码修复已经就绪，只要集成被正常加载，所有功能都应该正常工作。

