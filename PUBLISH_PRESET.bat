@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
    py -3 publish_preset.py
) else (
    python publish_preset.py
)
echo.
echo Commit profiles\default.json to GitHub to give new users your samples.
pause
