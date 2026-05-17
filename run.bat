@echo off
cd /d "%~dp0"
echo.
echo Starting AI Newsletter Generator...
echo.

:: Open browser after 3 seconds
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8080"

:: Start Flask (keep this window open)
python app.py

echo.
echo App stopped. Press any key to close.
pause
