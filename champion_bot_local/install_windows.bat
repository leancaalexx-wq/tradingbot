@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

echo.
echo ============================================================
echo  Instalare Champion Bot pentru Windows
echo ============================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=py -3"
    ) else (
        echo ERROR: Python nu a fost gasit.
        echo Instaleaza Python de aici:
        echo https://www.python.org/downloads/
        echo Bifeaza "Add Python to PATH" la instalare.
        pause
        exit /b 1
    )
)

echo Folosesc: %PYTHON_CMD%
echo.
echo Instalez botul si dependentele live...
%PYTHON_CMD% -m pip install -e ".[live]"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Instalarea a esuat.
    pause
    exit /b 1
)

echo.
echo Instalare terminata cu succes.
echo Acum poti porni:
echo  - 02_start_paper_champion.bat
echo  - 03_start_dashboard.bat
echo  - 04_start_live_champion.bat
echo.
pause
