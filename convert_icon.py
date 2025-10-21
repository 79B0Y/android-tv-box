#!/usr/bin/env python3
"""Convert SVG icon to PNG format for HACS integration."""
import subprocess
import sys
from pathlib import Path


def convert_svg_to_png():
    """Convert icon.svg to PNG files."""
    base_dir = Path(__file__).parent
    svg_file = base_dir / "icon.svg"
    
    if not svg_file.exists():
        print(f"❌ Error: {svg_file} not found")
        sys.exit(1)
    
    # Output paths
    outputs = [
        (base_dir / "icon.png", 256),
        (base_dir / "custom_components" / "android_tv_box" / "icon.png", 256),
        (base_dir / "custom_components" / "android_tv_box" / "icons" / "icon.png", 256),
        (base_dir / "custom_components" / "android_tv_box" / "icons" / "icon@2x.png", 512),
    ]
    
    # Create directories if needed
    for output_path, _ in outputs:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if cairosvg is available (Python library)
    try:
        import cairosvg
        
        print("✨ Using cairosvg for conversion...")
        for output_path, size in outputs:
            cairosvg.svg2png(
                url=str(svg_file),
                write_to=str(output_path),
                output_width=size,
                output_height=size,
            )
            print(f"✅ Created: {output_path} ({size}x{size})")
        
        print("\n🎉 All icons created successfully!")
        return
    
    except ImportError:
        pass
    
    # Check if ImageMagick convert is available
    try:
        result = subprocess.run(
            ["convert", "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode == 0:
            print("✨ Using ImageMagick for conversion...")
            for output_path, size in outputs:
                subprocess.run(
                    [
                        "convert",
                        "-background", "none",
                        "-density", "300",
                        str(svg_file),
                        "-resize", f"{size}x{size}",
                        str(output_path),
                    ],
                    check=True,
                )
                print(f"✅ Created: {output_path} ({size}x{size})")
            
            print("\n🎉 All icons created successfully!")
            return
    
    except FileNotFoundError:
        pass
    
    # Check if Inkscape is available
    try:
        result = subprocess.run(
            ["inkscape", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode == 0:
            print("✨ Using Inkscape for conversion...")
            for output_path, size in outputs:
                subprocess.run(
                    [
                        "inkscape",
                        str(svg_file),
                        "--export-type=png",
                        f"--export-filename={output_path}",
                        f"--export-width={size}",
                        f"--export-height={size}",
                    ],
                    check=True,
                )
                print(f"✅ Created: {output_path} ({size}x{size})")
            
            print("\n🎉 All icons created successfully!")
            return
    
    except FileNotFoundError:
        pass
    
    # No converter found
    print("\n❌ No SVG converter found!")
    print("\nPlease install one of the following:")
    print("  1. Python cairosvg: pip install cairosvg")
    print("  2. ImageMagick: brew install imagemagick (macOS) or apt-get install imagemagick (Linux)")
    print("  3. Inkscape: https://inkscape.org/")
    print("\nOr use an online converter:")
    print("  - https://cloudconvert.com/svg-to-png")
    print("  - https://convertio.co/svg-png/")
    sys.exit(1)


if __name__ == "__main__":
    convert_svg_to_png()

