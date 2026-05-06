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
        pause
        exit /b 1
    )
)

if "%STAKE_USDC%"=="" set "STAKE_USDC=10"
set "LIVE_TRADING=false"
set "DRY_RUN=true"
set "BOT_EVENT_LOG=runtime\paper-champion-events.jsonl"

echo.
echo Pornesc CHAMPION BOT in PAPER MODE.
echo Nu foloseste bani reali.
echo Stake simulat: %STAKE_USDC% USDC
echo.
echo Dashboard: ruleaza start_dashboard.bat in alta fereastra.
echo Pentru oprire: CTRL+C
echo.

%PYTHON_CMD% -m polymarket_bot --champion-profile --stake "%STAKE_USDC%" --log-level INFO

echo.
echo Bot oprit.
pause
