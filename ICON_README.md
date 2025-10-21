# Android TV Box 集成图标

## 📦 已创建的图标

所有图标都已自动放置在正确的位置：

### 1. HACS 商店图标
```
/icon.png (256x256)
```
这个图标会显示在 HACS 商店的集成列表中。

### 2. 集成图标
```
/custom_components/android_tv_box/icon.png (256x256)
```
Home Assistant 使用这个图标在集成页面显示。

### 3. 品牌图标
```
/custom_components/android_tv_box/icons/icon.png (256x256)
/custom_components/android_tv_box/icons/icon@2x.png (512x512)
```
用于高分辨率显示设备的图标。

## 🎨 图标设计

当前图标包含以下元素：
- 📺 **电视屏幕**: 蓝色屏幕代表 TV Box
- ▶️ **播放按钮**: 表示媒体播放功能
- 🤖 **Android 天线**: 绿色天线代表 Android 系统
- 🔌 **电源指示器**: 绿色圆点表示设备状态
- 📱 **遥控器**: 右侧简化的遥控器图标
- 📶 **WiFi 信号**: 底部的连接指示器

## 🔄 如何重新生成图标

### 方法 1: 使用 PIL (推荐)
```bash
python3 create_icon_pil.py
```

### 方法 2: 从 SVG 转换
如果需要编辑图标：
1. 编辑 `icon.svg` 文件
2. 安装转换工具:
   ```bash
   # 选项 A: Python
   pip3 install cairosvg
   brew install cairo  # macOS
   
   # 选项 B: ImageMagick
   brew install imagemagick
   
   # 选项 C: Inkscape
   # 从 https://inkscape.org/ 下载
   ```
3. 运行转换脚本:
   ```bash
   python3 convert_icon.py
   ```

## 🎨 自定义图标

如果您想使用自定义图标：

1. **替换现有图标**:
   ```bash
   cp your_icon.png icon.png
   cp your_icon.png custom_components/android_tv_box/icon.png
   ```

2. **创建不同尺寸**:
   ```bash
   # 256x256
   convert your_icon.png -resize 256x256 icon.png
   
   # 512x512 (高分辨率)
   convert your_icon.png -resize 512x512 icon@2x.png
   ```

3. **确保图标满足要求**:
   - ✅ PNG 格式
   - ✅ 透明背景
   - ✅ 256x256 像素 (标准)
   - ✅ 512x512 像素 (高分辨率，可选)
   - ✅ 在小尺寸下清晰可见

## 📐 图标设计建议

### 推荐的设计原则
- **简洁**: 避免过多细节
- **识别性**: 一眼能认出是 TV Box
- **对比度**: 使用高对比度颜色
- **可缩放**: 在小尺寸下也要清晰
- **品牌**: 体现 Android TV 的特点

### 颜色方案
当前图标使用的颜色：
- 主色调: `#03A9F4` (蓝色 - 代表技术/媒体)
- 强调色: `#4CAF50` (绿色 - Android 绿)
- 背景: `#424242` (深灰 - TV Box 外观)
- 对比色: `#FFFFFF` (白色 - 高对比度)

## 🔍 验证图标

检查图标是否正确放置：
```bash
ls -lh icon.png
ls -lh custom_components/android_tv_box/icon.png
ls -lh custom_components/android_tv_box/icons/
```

预览图标：
```bash
# macOS
open icon.png

# Linux
xdg-open icon.png
```

## 📚 参考资源

- [Home Assistant 品牌指南](https://developers.home-assistant.io/docs/creating_integration_manifest#icon)
- [HACS 文档](https://hacs.xyz/docs/publish/integration)
- [Material Design Icons](https://materialdesignicons.com/)

## ✨ 图标版本

- **当前版本**: v1.0 (占位符)
- **尺寸**: 256x256 (标准), 512x512 (高分辨率)
- **格式**: PNG with transparency
- **创建日期**: 2024-10

---

**需要帮助？** 如果您需要专业的图标设计或有任何问题，请在 GitHub 上提出 issue。

