@echo off
cd /d "%~dp0"

:: 检查 Node.js 是否可用
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

:: 检查 Python 是否可用
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo Starting Tailwind CSS Watcher...
start "Tailwind Dev" cmd /k "npm run dev"

timeout /t 2 /nobreak >nul

echo Starting MCP Tool Server (port 30000)...
start "MCP Server" cmd /k "python mcp_server.py"

:: 等待 MCP Server 就绪（检查 TCP 端口是否监听）
echo Waiting for MCP Server on port 30000...
powershell -Command "$s=[System.Diagnostics.Stopwatch]::StartNew(); while($s.Elapsed.TotalSeconds -lt 15){ if((Get-NetTCPConnection -LocalPort 30000 -ErrorAction SilentlyContinue)){ break }; Start-Sleep 1 }"

echo Starting Research Assistant AI Server (Uvicorn, port 8000)...
start "Uvicorn Server" cmd /k "python -m uvicorn ui.main:app --reload --port 8000"

:: 等待 Web Server 就绪
echo Waiting for Web UI on http://localhost:8000...
powershell -Command "$s=[System.Diagnostics.Stopwatch]::StartNew(); while($s.Elapsed.TotalSeconds -lt 15){ try{ $r=Invoke-WebRequest 'http://localhost:8000' -TimeoutSec 2; if($r.StatusCode -eq 200){ break } } catch{}; Start-Sleep 1 }"

echo Opening browser...
start "" "http://localhost:8000"

echo.
echo All services started!
echo - Tailwind Dev   : Watching CSS changes
echo - MCP Server     : http://localhost:30000
echo - Web UI         : http://localhost:8000
echo.
echo Keep this window open. Close terminal windows to stop servers.
pause