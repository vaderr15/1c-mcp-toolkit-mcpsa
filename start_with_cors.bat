@echo off
REM Batch script to start the server with CORS enabled
REM Usage: start_with_cors.bat

echo Starting 1C MCP Toolkit Proxy with CORS support...
echo.

REM Set environment variables
set CORS_ALLOW_ALL=true
set LOG_LEVEL=DEBUG

echo Environment variables set:
echo   CORS_ALLOW_ALL = %CORS_ALLOW_ALL%
echo   LOG_LEVEL = %LOG_LEVEL%
echo.

REM Start the server
python -m onec_mcp_toolkit_proxy
