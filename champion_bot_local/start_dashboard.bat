@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=py -3"
    ) else (
        echo ERROR: Python nu a fost gasit.
        echo Instaleaza Python de aici: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo Pornesc dashboard-ul local...
echo Deschide in browser: http://127.0.0.1:8080
echo.

%PYTHON_CMD% -m polymarket_bot --dashboard --dashboard-host 127.0.0.1 --dashboard-port 8080

pause
