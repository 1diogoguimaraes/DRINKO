@echo off
title DRINKO Dev Launcher
echo ========================================
echo   🚀 Starting DRINKO development servers
echo ========================================
echo.

:: --- Start FastAPI backend ---
echo [1/2] Starting FastAPI server...
cd fast_api_vue
call .venv\Scripts\activate
start "FastAPI Server" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug"
deactivate
cd ..

:: --- Start Vue frontend ---
echo [2/2] Starting Vue frontend...
cd vue-sidebar-test
start "Vue Dev Server" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo ✅ Both servers started successfully!
echo Close this window to stop everything.
echo ========================================
echo.

:: --- Wait for user to close ---
pause >nul

echo.
echo 🛑 Stopping servers...

:: Kill all python and node processes (gracefully)
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM uvicorn.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1

echo ✅ All servers stopped.
timeout /t 2 >nul
exit
