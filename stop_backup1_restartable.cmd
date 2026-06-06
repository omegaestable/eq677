@echo off
setlocal
cd /d "%~dp0"

set "STOPDIR=run_logs\colored_magma"
set "STOPFILE=%STOPDIR%\backup1_restartable.stop"

if not exist "%STOPDIR%" mkdir "%STOPDIR%"
> "%STOPFILE%" echo daily graceful stop requested at %DATE% %TIME%

echo Wrote stop file: %STOPFILE%
echo Starting stop monitor...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_backup1_restartable.ps1" %*
set "CODE=%ERRORLEVEL%"

if not "%CODE%"=="0" (
    echo.
    echo Stop monitor failed with exit code %CODE%.
    echo The stop file was still written, so stop-aware solver windows should still wind down.
    echo.
    pause
    exit /b %CODE%
)
