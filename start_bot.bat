@echo off
setlocal EnableExtensions

REM Windows launcher for the Polymarket BTC 5m champion bot.
REM Keep this file private if you edit it to hard-code secrets.

cd /d "%~dp0"

echo.
echo ============================================================
echo  Polymarket BTC 5m Champion Bot - LIVE MONEY LAUNCHER
echo ============================================================
echo.
echo WARNING: This starts REAL trading if your credentials are valid.
echo Start with a small stake, for example 10 USDC.
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=py -3"
    ) else (
        echo ERROR: Python was not found.
        echo Install Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

if "%POLYMARKET_PRIVATE_KEY%"=="" (
    echo Paste your POLYMARKET PRIVATE KEY below.
    echo It will be visible while typing. Do not share your screen.
    set /p "POLYMARKET_PRIVATE_KEY=Private key: "
)

if "%POLYMARKET_PRIVATE_KEY%"=="" (
    echo ERROR: Private key is empty. Refusing to start.
    pause
    exit /b 1
)

if "%POLYMARKET_FUNDER_ADDRESS%"=="" (
    echo.
    echo Paste your Polymarket FUNDER / PROXY address below.
    set /p "POLYMARKET_FUNDER_ADDRESS=Funder address: "
)

if "%POLYMARKET_FUNDER_ADDRESS%"=="" (
    echo ERROR: Funder address is empty. Refusing to start.
    pause
    exit /b 1
)

if "%STAKE_USDC%"=="" (
    echo.
    set /p "STAKE_USDC=Stake per trade in USDC [default 10]: "
)

if "%STAKE_USDC%"=="" (
    set "STAKE_USDC=10"
)

set "LIVE_TRADING=true"
set "DRY_RUN=false"
set "BOT_EVENT_LOG=runtime\live-bot-events.jsonl"

echo.
echo Checking live trading dependency...
%PYTHON_CMD% -c "import py_clob_client" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing live dependencies...
    %PYTHON_CMD% -m pip install -e ".[live]"
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Could not install live dependencies.
        pause
        exit /b 1
    )
)

echo.
echo Starting dashboard at http://127.0.0.1:8080
start "Polymarket Bot Dashboard" cmd /k "%PYTHON_CMD% -m polymarket_bot --dashboard --dashboard-host 127.0.0.1 --dashboard-port 8080"

echo.
echo Starting LIVE champion bot...
echo Stake: %STAKE_USDC% USDC per trade
echo.
echo To stop the bot, press CTRL+C in this window.
echo.

%PYTHON_CMD% -m polymarket_bot --champion-profile --stake "%STAKE_USDC%" --live --log-level INFO

echo.
echo Bot stopped.
pause
