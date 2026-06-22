@echo off
rem overlay.py を Windows 向けにビルドする
setlocal

cd /d "%~dp0"

set "PY=python"
if defined PYTHON set "PY=%PYTHON%"

%PY% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller が見つかりません。インストールします...
    %PY% -m pip install --user pyinstaller
)

%PY% -c "import qrcode, PIL" >nul 2>&1
if errorlevel 1 (
    echo qrcode / Pillow をインストールします...
    %PY% -m pip install --user qrcode Pillow
)

set "ICON_ARG="
if exist icon.ico set "ICON_ARG=-i icon.ico"

%PY% -m PyInstaller --onefile --windowed --name overlay %ICON_ARG% overlay.py
if errorlevel 1 (
    echo ビルドに失敗しました
    exit /b 1
)

echo.
echo ==^> 完成: dist\overlay.exe
endlocal
