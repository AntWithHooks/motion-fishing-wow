@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Motion Fishing - Windows EXE Builder

echo ===========================================
echo       MOTION FISHING - EXE BUILDER
echo ===========================================
echo.
echo [1/4] Checking Python...
where py >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 goto no_python
    set "PY=python"
)
%PY% --version || goto error

echo.
echo [2/4] Creating isolated build environment...
if not exist ".build_env\Scripts\python.exe" (
    %PY% -m venv .build_env || goto error
)
set "BUILDPY=%CD%\.build_env\Scripts\python.exe"
"%BUILDPY%" -m pip install --disable-pip-version-check "pyinstaller>=6.14,<7" || goto error

echo.
echo [3/4] Testing Motion Fishing...
"%BUILDPY%" -m unittest discover -s tests -v || goto error

echo.
echo [4/4] Creating a standalone Windows executable...
echo NOTE: to include your current gestures in the shared preset,
echo       click Publish Preset in the app or run PUBLISH_PRESET.bat first.
"%BUILDPY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name MotionFishing ^
    --icon "assets\motion_fishing.ico" ^
    --add-data "assets\motion_fishing.ico;assets" ^
    --add-data "profiles\default.json;profiles" ^
    --distpath "dist" ^
    motion_fishing_gui.py || goto error
if not exist "dist\MotionFishing.exe" goto error
if not exist "dist\profiles" mkdir "dist\profiles" || goto error
copy /Y "profiles\default.json" "dist\profiles\default.json" >nul || goto error
if exist "profiles\settings.json" copy /Y "profiles\settings.json" "dist\profiles\settings.json" >nul || goto error
if exist "MotionFishing-Guide-RU.pdf" copy /Y "MotionFishing-Guide-RU.pdf" "dist\MotionFishing-Guide-RU.pdf" >nul
if exist "MotionFishing-Guide-EN.pdf" copy /Y "MotionFishing-Guide-EN.pdf" "dist\MotionFishing-Guide-EN.pdf" >nul

echo.
echo [5/5] Packaging a clean portable release (without personal data)...
if exist "release" rmdir /S /Q "release"
mkdir "release" || goto error
mkdir "release\profiles" || goto error
copy /Y "dist\MotionFishing.exe" "release\MotionFishing.exe" >nul || goto error
copy /Y "profiles\default.json" "release\profiles\default.json" >nul || goto error
if exist "MotionFishing-Guide-RU.pdf" copy /Y "MotionFishing-Guide-RU.pdf" "release\MotionFishing-Guide-RU.pdf" >nul
if exist "MotionFishing-Guide-EN.pdf" copy /Y "MotionFishing-Guide-EN.pdf" "release\MotionFishing-Guide-EN.pdf" >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'release\*' -DestinationPath 'MotionFishing-Windows-Portable.zip' -Force" || goto error

echo.
echo ===========================================
echo SUCCESS! Your executable is here:
echo %CD%\dist\MotionFishing.exe
echo SHARE THIS CLEAN ZIP: %CD%\MotionFishing-Windows-Portable.zip
echo ===========================================
echo.
echo Share MotionFishing-Windows-Portable.zip, not the working dist folder.
echo This release has only the shared default preset (no local settings.json).
echo Each user gets their own writable profiles\settings.json.
echo The EXE can run on other Windows PCs without Python.
echo English/Russian language selection is visible in the app header.
echo Both language guides are included in the release ZIP.
echo Phone phyphox + local Wi-Fi network is required. Bluetooth is NOT required.
explorer "%CD%"
pause
exit /b 0

:no_python
echo ERROR: Python is not installed or not on PATH.
echo Install Python 3.13 from https://www.python.org/downloads/windows/
echo Then reopen this script.
pause
exit /b 1

:error
echo.
echo ERROR: The build failed. See error messages above.
echo Please send a screenshot of this window if you need help.
pause
exit /b 1
