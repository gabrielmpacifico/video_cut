@echo off
cd /d "%~dp0"
py -3 cortar_video.py
if errorlevel 1 python cortar_video.py
if errorlevel 1 pause
