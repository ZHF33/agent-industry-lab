param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing Python runtime: $python"
}

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Output "Bakery Agent API already listening on port $Port."
    Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" | ConvertTo-Json -Compress
    exit 0
}

$logDir = Join-Path $root "runs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$runner = Join-Path $root "scripts\run_agent_http_api.cmd"
cmd.exe /c "start `"Bakery Agent API`" /min `"$runner`""

Start-Sleep -Seconds 2
Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" | ConvertTo-Json -Compress
