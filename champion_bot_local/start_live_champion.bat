@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

echo.
echo ============================================================
echo  CHAMPION BOT - LIVE TRADING / BANI REALI
echo ============================================================
echo.
echo ATENTIE: Acest mod poate pierde bani reali.
echo Recomandare: incepe cu 10 USDC per trade.
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=py -3"
    ) else (
        echo ERROR: Python nu este instalat.
        echo Instaleaza Python de aici: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

if "%POLYMARKET_PRIVATE_KEY%"=="" (
    echo Pune private key de la wallet.
    echo ATENTIE: se vede cand tastezi. Nu arata ecranul nimanui.
    set /p "POLYMARKET_PRIVATE_KEY=Private key: "
)

if "%POLYMARKET_PRIVATE_KEY%"=="" (
    echo ERROR: Private key este gol. Nu pornesc live.
    pause
    exit /b 1
)

if "%POLYMARKET_FUNDER_ADDRESS%"=="" (
    echo.
    echo Pune Polymarket funder/proxy address.
    set /p "POLYMARKET_FUNDER_ADDRESS=Funder address: "
)

if "%POLYMARKET_FUNDER_ADDRESS%"=="" (
    echo ERROR: Funder address este gol. Nu pornesc live.
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
set "BOT_EVENT_LOG=runtime\live-champion-events.jsonl"

echo.
echo Instalez/verific dependente live...
%PYTHON_CMD% -m pip install -e ".[live]"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Nu am putut instala dependentele live.
    pause
    exit /b 1
)

echo.
echo Pornesc dashboard-ul: http://127.0.0.1:8080
start "Champion Dashboard" cmd /k "champion_bot_local\start_dashboard.bat live"

echo.
echo Pornesc botul LIVE champion...
echo Stake: %STAKE_USDC% USDC per trade
echo Pentru oprire: CTRL+C in aceasta fereastra.
echo.

%PYTHON_CMD% -m polymarket_bot --champion-profile --stake "%STAKE_USDC%" --live --log-level INFO

echo.
echo Botul live s-a oprit.
pause
