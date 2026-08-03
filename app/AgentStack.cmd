@echo off
:: AgentStack Desktop App — one clean system
:: Launch shortcut for the desktop

set "APP_DIR=C:\Users\willi\Documents\ai agents\agent-stack\app"
set "NODE_PATH=%APPDATA%\npm\node_modules"

cd /d "%APP_DIR%"
start "" "%APP_DIR%\node_modules\.bin\electron.cmd" "%APP_DIR%\.."