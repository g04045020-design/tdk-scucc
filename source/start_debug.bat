@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Flask Application Starter - DEBUG MODE
echo ========================================
echo.

echo [1/6] Environment information...
echo Current directory: %CD%
echo System PATH: %PATH%
echo.

echo [2/6] Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python not found in PATH!
    echo Please ensure Python is installed and in PATH
    pause
    exit /b 1
)

echo [3/6] Changing to source directory...
cd /d "C:\Users\User\Documents\GitHub\TDK-source\source"
if errorlevel 1 (
    echo ERROR: Failed to change directory!
    echo Target directory: C:\Users\User\Documents\GitHub\TDK-source\source
    pause
    exit /b 1
)
echo New directory: %CD%

echo [4/6] Checking files...
if not exist "main.py" (
    echo ERROR: main.py not found!
    echo Files in current directory:
    dir /b
    pause
    exit /b 1
)
if not exist "..\venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Expected: ..\venv\Scripts\activate.bat
    pause
    exit /b 1
)
echo All required files found

echo [5/6] Activating virtual environment...
call ..\venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    echo Trying to check virtual environment...
    if exist "..\venv\Scripts\python.exe" (
        echo Virtual environment Python found, trying direct execution...
        set PYTHON_EXEC=..\venv\Scripts\python.exe
    ) else (
        echo Virtual environment Python not found!
        pause
        exit /b 1
    )
) else (
    echo Virtual environment activated successfully
    set PYTHON_EXEC=python
)

echo [6/6] Starting Python application...
echo Command: %PYTHON_EXEC% main.py
echo.
echo ========================================
echo Starting Flask server...
echo ========================================
echo.

%PYTHON_EXEC% main.py

echo.
echo ========================================
echo Application finished
echo ========================================
pause
