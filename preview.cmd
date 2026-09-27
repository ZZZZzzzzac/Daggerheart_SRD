@echo off
setlocal
cd /d "%~dp0"
title Daggerheart SRD - Local Preview
python -u scripts\preview_server.py --open
if errorlevel 1 (
  echo.
  echo Preview could not start. Check the error above.
  echo If port 8765 is already in use, open http://127.0.0.1:8765/SRD/
  pause
)
endlocal
