@echo off
echo Mario Kart Time Trial Tracker - Queue Processor
echo =============================================
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0process_queue.ps1"

echo.
echo Press any key to exit...
pause >nul
