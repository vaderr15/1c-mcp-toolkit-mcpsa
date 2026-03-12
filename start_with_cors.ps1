# PowerShell script to start the server with CORS enabled
# Usage: .\start_with_cors.ps1

Write-Host "Starting 1C MCP Toolkit Proxy with CORS support..." -ForegroundColor Green

# Set environment variables
$env:CORS_ALLOW_ALL = "true"
$env:LOG_LEVEL = "DEBUG"

Write-Host "Environment variables set:" -ForegroundColor Yellow
Write-Host "  CORS_ALLOW_ALL = $env:CORS_ALLOW_ALL"
Write-Host "  LOG_LEVEL = $env:LOG_LEVEL"
Write-Host ""

# Start the server
python -m onec_mcp_toolkit_proxy
