#!/usr/bin/env python3
"""絵文字から macOS 用 .icns アイコンを生成する。"""
import os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

EMOJI = sys.argv[1] if len(sys.argv) > 1 else "🚩"
OUT_ICNS = "icon.icns"
SIZES = [16, 32, 64, 128, 256, 512, 1024]

# Apple Color Emoji フォントを使う
FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"


def render(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Apple Color Emoji は固定 160pt のみ受け付ける（後でリサイズ）
    font = ImageFont.truetype(FONT_PATH, 160)
    bbox = draw.textbbox((0, 0), EMOJI, font=font, embedded_color=True)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    big = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(big).text((-bbox[0], -bbox[1]), EMOJI, font=font,
                              embedded_color=True)
    # アスペクト比保ったまま size に収める
    scale = min(size / tw, size / th) * 0.9
    new_w = max(1, int(tw * scale))
    new_h = max(1, int(th * scale))
    big = big.resize((new_w, new_h), Image.LANCZOS)
    img.paste(big, ((size - new_w) // 2, (size - new_h) // 2), big)
    return img


def main():
    iconset = "icon.iconset"
    if os.path.isdir(iconset):
        shutil.rmtree(iconset)
    os.makedirs(iconset)

    for s in SIZES:
        img = render(s)
        img.save(f"{iconset}/icon_{s}x{s}.png")
        if s * 2 in SIZES or s == 512:
            img2 = render(s * 2)
            img2.save(f"{iconset}/icon_{s}x{s}@2x.png")

    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", OUT_ICNS],
                   check=True)
    shutil.rmtree(iconset)
    print(f"created: {OUT_ICNS}")


if __name__ == "__main__":
    main()
