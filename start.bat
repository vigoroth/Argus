@echo off
REM Argus launcher — double-click from Windows Explorer.
REM Runs the FastAPI server inside WSL (Ubuntu) via conda, then opens the UI.
REM Stale/duplicate instances are handled by _free_port() in app/web/server.py.

title Argus
echo Starting Argus...

REM Background: poll the port until the server answers, then open the browser.
REM Boot takes ~10-15s (conda + heavy imports), so a fixed wait races. curl.exe
REM ships with Windows 10/11.
start "" cmd /c "for /l %%i in (1,1,40) do (curl -s -o nul http://localhost:8000/login && (start http://localhost:8000 & exit) || timeout /t 1 >nul)"

REM login shell (-l) so conda is on PATH; runs in the repo dir
wsl.exe -d Ubuntu -e bash -lc "cd ~/projects/argus && conda run -n claude-desktop --no-capture-output python -m app.web.server"

echo.
echo Argus stopped. Press any key to close.
pause >nul
