@echo off
setlocal
cd /d "%~dp0"
title SiteCare - First-time setup

echo.
echo SiteCare Prototype - First-time setup
echo This installs packages into this folder's private .venv environment.
echo Internet access is required to download packages.
echo.
if not exist "run.py" goto missing_files
if not exist "requirements.txt" goto missing_files
if exist ".venv\Scripts\python.exe" goto check_environment

set "PYTHON_CMD="
call :try_python py -3.13
if not defined PYTHON_CMD call :try_python py -3.12
if not defined PYTHON_CMD call :try_python py -3.11
if not defined PYTHON_CMD call :try_python py -3
if not defined PYTHON_CMD call :try_python python
if not defined PYTHON_CMD goto missing_python

echo Creating .venv with %PYTHON_CMD% ...
%PYTHON_CMD% -m venv ".venv"
if errorlevel 1 goto environment_error

:check_environment
".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto environment_error
".venv\Scripts\python.exe" --version
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto install_error
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, multipart, PIL"
if errorlevel 1 goto install_error
echo.
echo Setup complete. Double-click start_windows.bat to open SiteCare.
echo Keep the start window open while using the application.
echo.
pause
exit /b 0

:try_python
%* -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=%*"
exit /b 0

:missing_python
echo ERROR: A working Python 3.11 or newer was not found.
echo Install Python 3.13 from https://www.python.org/downloads/.
echo Enable PATH and the Python launcher when offered, then retry.
goto failure

:missing_files
echo ERROR: Required files are missing. Extract the entire ZIP first.
goto failure

:environment_error
echo ERROR: The private Python environment could not be created or used.
echo Check Python installation and folder permissions. Read README.txt.
echo For an old or damaged .venv, stop SiteCare, rename ONLY that folder,
echo then retry. Do NOT delete the data folder.
goto failure

:install_error
echo ERROR: Package installation or import checking failed.
echo Check the error above, your internet connection, and README.txt.
goto failure

:failure
echo.
pause
exit /b 1
