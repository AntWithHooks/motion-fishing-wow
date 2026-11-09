@echo off
cd /d "%~dp0"
py -3 motion_fishing_gui.py
if errorlevel 1 (
 echo.
 echo Could not start Motion Fishing. Check Python and Tkinter installation.
 pause
)
