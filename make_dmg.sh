#!/usr/bin/env bash
# overlay.app を DMG にパッケージングする
set -euo pipefail
cd "$(dirname "$0")"

APP="dist/overlay.app"
DMG="dist/overlay.dmg"
VOLUME_NAME="Overlay"
STAGING="dist/dmg_staging"

if [ ! -d "$APP" ]; then
    echo "==> .app が見つかりません。先に build.sh を実行してください。" >&2
    exit 1
fi

rm -rf "$STAGING" "$DMG"
mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$STAGING" \
    -ov -format UDZO \
    "$DMG"

rm -rf "$STAGING"
echo "==> 完成: $DMG"
