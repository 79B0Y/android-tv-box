#!/bin/bash
# Android TV Box Integration - 完全重置脚本
# 用于解决重启后 unavailable 的问题

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "    Android TV Box Integration - 完全重置"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "此脚本将："
echo "  1. 删除所有相关配置文件"
echo "  2. 清理实体和设备注册表"
echo "  3. 准备全新安装"
echo ""
read -p "确认要继续吗? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 1
fi

HA_CONFIG="$HOME/.homeassistant"

echo ""
echo "步骤 1: 查找配置入口..."
ENTRY_ID=$(python3 << 'EOF'
import json
with open('$HA_CONFIG/.storage/core.config_entries', 'r') as f:
    data = json.load(f)
for entry in data.get('data', {}).get('entries', []):
    if entry.get('domain') == 'android_tv_box':
        print(entry.get('entry_id'))
        break
EOF
)

if [ -z "$ENTRY_ID" ]; then
    echo "  ❌ 未找到配置入口"
    exit 1
fi

echo "  ✅ 找到: $ENTRY_ID"

echo ""
echo "步骤 2: 备份配置文件..."
BACKUP_DIR="$HA_CONFIG/backups/android_tv_box_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

for file in core.config_entries core.entity_registry core.device_registry; do
    if [ -f "$HA_CONFIG/.storage/$file" ]; then
        cp "$HA_CONFIG/.storage/$file" "$BACKUP_DIR/"
        echo "  ✅ 备份: $file"
    fi
done

echo ""
echo "步骤 3: 停止 Home Assistant..."
echo "  请手动停止 Home Assistant"
read -p "  按 Enter 继续（确认已停止）..." 

echo ""
echo "步骤 4: 清理注册表..."

# 清理实体注册表
python3 << 'EOF'
import json
import sys

file_path = '$HA_CONFIG/.storage/core.entity_registry'
with open(file_path, 'r') as f:
    data = json.load(f)

original_count = len(data['data']['entities'])
data['data']['entities'] = [
    e for e in data['data']['entities']
    if 'android_tv_box' not in e.get('entity_id', '')
]
removed = original_count - len(data['data']['entities'])

with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"  ✅ 删除了 {removed} 个实体")
EOF

# 清理设备注册表
python3 << 'EOF'
import json

file_path = '$HA_CONFIG/.storage/core.device_registry'
with open(file_path, 'r') as f:
    data = json.load(f)

original_count = len(data['data']['devices'])
data['data']['devices'] = [
    d for d in data['data']['devices']
    if '$ENTRY_ID' not in d.get('config_entries', [])
]
removed = original_count - len(data['data']['devices'])

with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"  ✅ 删除了 {removed} 个设备")
EOF

# 清理配置入口
python3 << 'EOF'
import json

file_path = '$HA_CONFIG/.storage/core.config_entries'
with open(file_path, 'r') as f:
    data = json.load(f)

original_count = len(data['data']['entries'])
data['data']['entries'] = [
    e for e in data['data']['entries']
    if e.get('domain') != 'android_tv_box'
]
removed = original_count - len(data['data']['entries'])

with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"  ✅ 删除了 {removed} 个配置入口")
EOF

# 清理 ADB 密钥
if ls $HA_CONFIG/.storage/android_tv_box_*.adb_key* 2>/dev/null; then
    rm -f $HA_CONFIG/.storage/android_tv_box_*.adb_key*
    echo "  ✅ 删除了 ADB 密钥"
fi

echo ""
echo "步骤 5: 清理完成"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ 清理完成！"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""
echo "下一步："
echo "  1. 启动 Home Assistant"
echo "  2. 在 UI 中添加 Android TV Box 集成"
echo "  3. 输入: 10.0.0.206:5555"
echo ""
echo "═══════════════════════════════════════════════════════════════"

