@echo off
title Minecraft Mod Menu Launcher
cd /d "%~dp0"

if exist "Minecraft_Mod_Menu.exe" (
    start "" "Minecraft_Mod_Menu.exe"
    exit /b
)

if exist "dist\Minecraft_Mod_Menu.exe" (
    start "" "dist\Minecraft_Mod_Menu.exe"
    exit /b
)

where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pythonw app_gui.py
    exit /b
)

python app_gui.py
