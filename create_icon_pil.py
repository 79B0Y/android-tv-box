#!/usr/bin/env python3
"""Create a simple PNG icon using PIL."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_icon():
    """Create Android TV Box icon using PIL."""
    base_dir = Path(__file__).parent
    
    # Create icon directories
    icons_dir = base_dir / "custom_components" / "android_tv_box" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    # Output paths
    outputs = [
        (base_dir / "icon.png", 256),
        (base_dir / "custom_components" / "android_tv_box" / "icon.png", 256),
        (icons_dir / "icon.png", 256),
        (icons_dir / "icon@2x.png", 512),
    ]
    
    for output_path, size in outputs:
        # Create image with transparency
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Scale factor
        s = size / 256
        
        # Background circle (light blue)
        draw.ellipse([8*s, 8*s, 248*s, 248*s], fill=(3, 169, 244, 25))
        
        # TV Box body (dark gray)
        draw.rounded_rectangle([60*s, 80*s, 196*s, 176*s], radius=8*s, fill=(66, 66, 66, 255))
        draw.rounded_rectangle([68*s, 88*s, 188*s, 168*s], radius=4*s, fill=(33, 33, 33, 255))
        
        # Screen (blue)
        draw.rounded_rectangle([76*s, 96*s, 180*s, 160*s], radius=2*s, fill=(3, 169, 244, 255))
        
        # Screen glow (lighter blue)
        draw.rounded_rectangle([80*s, 100*s, 176*s, 156*s], radius=2*s, fill=(129, 212, 250, 153))
        
        # Play triangle
        play_points = [(115*s, 118*s), (140*s, 133*s), (115*s, 148*s)]
        draw.polygon(play_points, fill=(255, 255, 255, 230))
        
        # Android antenna (left)
        draw.line([100*s, 75*s, 95*s, 60*s], fill=(76, 175, 80, 255), width=int(4*s))
        
        # Android antenna (right)
        draw.line([156*s, 75*s, 161*s, 60*s], fill=(76, 175, 80, 255), width=int(4*s))
        
        # Power indicator (green dot)
        draw.ellipse([177*s, 92*s, 183*s, 98*s], fill=(76, 175, 80, 255))
        
        # Remote control
        draw.rounded_rectangle([210*s, 130*s, 238*s, 190*s], radius=4*s, fill=(97, 97, 97, 255))
        draw.ellipse([220*s, 141*s, 228*s, 149*s], fill=(189, 189, 189, 255))
        draw.ellipse([218*s, 154*s, 230*s, 166*s], fill=(224, 224, 224, 255))
        draw.rounded_rectangle([218*s, 172*s, 230*s, 175*s], radius=1*s, fill=(189, 189, 189, 255))
        draw.rounded_rectangle([218*s, 178*s, 230*s, 181*s], radius=1*s, fill=(189, 189, 189, 255))
        
        # WiFi indicator (arcs)
        for i, (offset, alpha) in enumerate([(5, 204), (13, 153), (21, 102)]):
            draw.arc([128*s-offset*s, 190*s-offset*s, 128*s+offset*s, 190*s+offset*s], 
                     180, 360, fill=(76, 175, 80, alpha), width=int(2*s))
        
        # Save
        img.save(output_path, 'PNG')
        print(f"✅ Created: {output_path} ({size}x{size})")
    
    print("\n🎉 All icons created successfully!")
    print("\n📁 Icon locations:")
    print("  - /icon.png (HACS store)")
    print("  - /custom_components/android_tv_box/icon.png (integration)")
    print("  - /custom_components/android_tv_box/icons/icon.png (standard)")
    print("  - /custom_components/android_tv_box/icons/icon@2x.png (high-res)")


if __name__ == "__main__":
    create_icon()

