param(
    [int]$Port = 8765
)

$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $connections) {
    Write-Output "No Bakery Agent API listener found on port $Port."
    exit 0
}

$pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($processId in $pids) {
    Stop-Process -Id $processId -Force
}
Write-Output "Stopped Bakery Agent API listener on port $Port."
