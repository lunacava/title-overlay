#!/usr/bin/env bash
# overlay.py を Mac/Linux 向けにビルドするスクリプト
set -euo pipefail

cd "$(dirname "$0")"

# Python と PyInstaller の確認
PY="${PYTHON:-python3}"

if ! "$PY" -c "import PyInstaller" >/dev/null 2>&1; then
    echo "PyInstaller が見つかりません。インストールします..."
    "$PY" -m pip install --user pyinstaller
fi

# python3 -m PyInstaller で常に呼ぶ（--user 配下にしか入っていなくてもOK）
PYINSTALLER=("$PY" "-m" "PyInstaller")

OS="$(uname -s)"

case "$OS" in
    Darwin)
        echo "==> macOS 向けにビルドします (.app + 単一バイナリ)"
        ICON_ARG=()
        if [ -f icon.icns ]; then
            ICON_ARG=(-i icon.icns)
        fi
        "${PYINSTALLER[@]}" --onefile --windowed --name overlay "${ICON_ARG[@]}" overlay.py

        # Dock に出さない設定 (LSUIElement) を Info.plist に書き込む
        APP="dist/overlay.app"
        if [ -d "$APP" ]; then
            /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" \
                "$APP/Contents/Info.plist" 2>/dev/null \
                || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" \
                    "$APP/Contents/Info.plist"
            echo "==> Info.plist に LSUIElement=true を設定しました（Dock 非表示）"
        fi
        echo "==> 完成: $APP / dist/overlay"
        ;;
    Linux)
        echo "==> Linux 向けにビルドします (単一バイナリ)"
        pyinstaller --onefile --name overlay overlay.py
        echo "==> 完成: dist/overlay"
        ;;
    *)
        echo "未対応の OS: $OS" >&2
        exit 1
        ;;
esac
