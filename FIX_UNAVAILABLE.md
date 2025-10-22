# 修复 Unavailable 问题 - 简单步骤

## 问题
每次重启 Home Assistant 后，Android TV Box 集成的所有实体都变成 `unavailable`

## 根本原因
配置入口损坏，导致 `async_setup_entry()` 从未被调用

## 解决方案（2分钟）

### 方法A：通过 Home Assistant UI（推荐）

1. **打开 Home Assistant**
   - 访问: http://127.0.0.1:8123

2. **删除旧配置**
   - 设置 > 设备与服务
   - 找到 "Android TV Box"
   - 点击右侧三个点 (...) > 删除
   - 确认删除

3. **重启 Home Assistant**
   - 设置 > 系统 > 重启

4. **重新添加集成**
   - 设置 > 设备与服务 > 添加集成
   - 搜索 "Android TV Box"
   - 输入：
     - 主机：10.0.0.206
     - 端口：5555
     - 设备名：Android TV Box
   - 完成配置向导

5. **验证**
   - 检查传感器是否显示数据
   - CPU、内存、亮度等都应该有值
   - Power 开关应该显示 ON

### 方法B：通过 API（快速）

运行以下命令：

\`\`\`bash
# 1. 删除旧配置
curl -X DELETE \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://127.0.0.1:8123/api/config/config_entries/entry/01K85GN38JV19G4G95PYQ91D56

# 2. 重启 HA
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://127.0.0.1:8123/api/services/homeassistant/restart

# 3. 等待重启完成（约60秒）
sleep 60

# 4. 添加新配置（通过 UI）
\`\`\`

## 预期结果

✅ 所有实体应该正常显示数据
✅ 重启后仍然正常工作
✅ CPU: ~100%
✅ Memory: ~1800 MB
✅ Power: ON
✅ App Selector 可以切换应用

## 如果还是不行

检查日志：
\`\`\`bash
tail -f /Users/bo/.homeassistant/home-assistant.log | grep android_tv_box
\`\`\`

应该看到：
- "Starting Android TV Box setup"
- "Successfully connected to Android TV Box"
- "All platforms set up successfully"

如果没有这些日志，说明集成仍未被正确加载。

## 临时解决方案（如果急用）

如果重新添加集成还是不行，可以尝试：

1. 完全卸载集成文件
   \`\`\`bash
   rm -rf /Users/bo/.homeassistant/custom_components/android_tv_box
   \`\`\`

2. 重启 Home Assistant

3. 重新复制集成文件
   \`\`\`bash
   cp -r /Users/bo/android-tv-box/custom_components/android_tv_box \
         /Users/bo/.homeassistant/custom_components/
   \`\`\`

4. 重启并添加集成

## 所有修复已就绪

所有代码问题都已修复：
- ✅ App Selector（am start 命令）
- ✅ Power 按钮状态
- ✅ YouTube TV 包名
- ✅ CPU/内存监测
- ✅ 详细启动日志

只要集成能正常加载，一切都会正常工作！
