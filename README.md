# Exhibition Title Overlay

展示会用のタイトルオーバーレイ（常時最前面のフローティングウィンドウ）。
Mac / Linux 両対応の Python tkinter 製。

## 操作

| 操作 | 動作 |
|------|------|
| ドラッグ | ウィンドウ移動 |
| 右下角ドラッグ | リサイズ（フォント自動連動） |
| ダブルクリック | テキスト編集（Enter で確定 / Shift+Enter で改行 / Esc で取消） |
| 右クリック | 設定メニュー（テキスト編集 / フォント変更 / 太字 / 文字色 / 背景色 / 透明度 / 終了） |

macOS の場合は **Control+クリック** または **2 本指タップ** でも右クリックメニューを開けます。

## 動作確認（直接実行）

```bash
python3 overlay.py
```

### Linux で tkinter が無い場合

```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

## ビルド（PyInstaller）

### macOS / Linux

```bash
./build.sh
```

- macOS: `dist/overlay.app` と `dist/overlay`
  - `Info.plist` に `LSUIElement=true` を自動追加（Dock 非表示）
  - 配布時に Gatekeeper で弾かれたら `xattr -cr dist/overlay.app`
- Linux: `dist/overlay`
  - `-topmost` が効かない WM では `wmctrl -r overlay -b add,above` で代替

### Windows

事前に Python 3.10 以降をインストール。

```cmd
build.bat
```

- 出力: `dist\overlay.exe`
- 必要なライブラリ (`pyinstaller`, `qrcode`, `Pillow`) は `build.bat` が自動インストール

アイコンを変えたい場合は先に `python make_icon.py "🚩"` で `icon.ico` を生成してから `build.bat`。

## 状態の永続化

テキスト・フォント・色・サイズ・位置・透明度は自動で保存され、次回起動時に復元されます。

- macOS: `~/Library/Application Support/overlay_app/config.json`
- Linux: `~/.config/overlay_app/config.json`

## アイコンの差し替え（macOS）

```bash
# 任意の絵文字でアイコンを生成
python3 make_icon.py "🚩"
./build.sh
```

## DMG 配布パッケージの作成（macOS）

```bash
./build.sh
./make_dmg.sh
# → dist/overlay.dmg
```

DMG をマウントして `overlay.app` を `Applications` にドラッグでインストールできます。

配布時の注意:
- Apple Silicon Mac でビルドした場合は arm64 専用です
- ad-hoc 署名のため初回起動時は **右クリック → 開く** で許可が必要

## macOS の前提

- Python 3.12 以降（Tk 9.0 以降）が必要です。Apple 同梱の Python 3.9 + Tk 8.5 では borderless ウィンドウが正しく描画されません。

```bash
brew install python@3.12 python-tk@3.12
PYTHON=/opt/homebrew/bin/python3.12 ./build.sh
```

## ファイル構成

```
overlay.py      # ソース本体
build.sh        # Mac/Linux 用ビルドスクリプト
make_icon.py    # 絵文字から .icns を生成（macOS）
make_dmg.sh     # .dmg にパッケージング（macOS）
README.md       # この説明
```
