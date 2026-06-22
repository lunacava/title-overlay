#!/usr/bin/env python3
"""絵文字から macOS 用 .icns / Windows 用 .ico アイコンを生成する。"""
import os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

EMOJI = sys.argv[1] if len(sys.argv) > 1 else "🚩"
OUT_ICNS = "icon.icns"
OUT_ICO  = "icon.ico"
SIZES = [16, 32, 64, 128, 256, 512, 1024]

# 絵文字を表示できるフォントを探す（macOS / Windows / Linux）
FONT_CANDIDATES = [
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    r"C:\Windows\Fonts\seguiemj.ttf",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if os.path.exists(p)),
                 FONT_CANDIDATES[0])


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


def make_icns():
    """macOS 用 .icns を生成（iconutil を使う）。"""
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


def make_ico():
    """Windows 用 .ico を生成（Pillow で複数サイズを束ねる）。"""
    ico_sizes = [16, 32, 48, 64, 128, 256]
    images = [render(s) for s in ico_sizes]
    images[0].save(OUT_ICO, sizes=[(s, s) for s in ico_sizes])
    print(f"created: {OUT_ICO}")


def main():
    if sys.platform == "darwin":
        make_icns()
    else:
        make_ico()


if __name__ == "__main__":
    main()
