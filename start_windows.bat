@echo off
setlocal
cd /d "%~dp0"
title SiteCare - Keep this window open
if not exist ".venv\Scripts\python.exe" goto missing_environment
if not exist "run.py" goto missing_files
echo.
echo Starting SiteCare. Keep this window open while using the application.
echo Default browser address: http://127.0.0.1:8000
echo Press Ctrl+C here to stop. Use synthetic data only.
echo.
".venv\Scripts\python.exe" "run.py" %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo SiteCare exited with an error. Read the message above and README.txt.
echo.
pause
exit /b %RESULT%

:missing_environment
echo Please run setup_windows.bat first, then run this file again.
pause
exit /b 1

:missing_files
echo Required files are missing. Extract the entire ZIP first.
pause
exit /b 1
