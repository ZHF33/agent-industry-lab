param(
    [switch]$IncludeStaleDryRuns,
    [switch]$DeleteInsteadOfQuarantine
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Assert-UnderRoot {
    param([string]$Path)
    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $resolved) { return $false }
    $rootFull = [System.IO.Path]::GetFullPath($Root.Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $targetFull = [System.IO.Path]::GetFullPath($resolved.Path)
    return $targetFull.Equals($rootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $targetFull.StartsWith($rootFull + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -or
        $targetFull.StartsWith($rootFull + [System.IO.Path]::AltDirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)
}

function Remove-SafePath {
    param([string]$Path)
    if (Assert-UnderRoot $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
        Write-Output "removed $Path"
    }
}

function Move-Or-Delete {
    param([string]$Path, [string]$Quarantine)
    if (-not (Assert-UnderRoot $Path)) { return }
    if ($DeleteInsteadOfQuarantine) {
        Remove-Item -LiteralPath $Path -Recurse -Force
        Write-Output "deleted stale $Path"
        return
    }
    New-Item -ItemType Directory -Force -Path $Quarantine | Out-Null
    Move-Item -LiteralPath $Path -Destination $Quarantine -Force
    Write-Output "quarantined $Path -> $Quarantine"
}

Get-ChildItem -Path $Root -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike "*\.venv\*" } |
    ForEach-Object { Remove-SafePath $_.FullName }

Remove-SafePath (Join-Path $Root ".pytest_cache")
Remove-SafePath (Join-Path $Root ".pytest_tmp")
Get-ChildItem -Path $Root -Directory -Filter ".pytest_tmp*" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-SafePath $_.FullName }
Get-ChildItem -Path (Join-Path $Root "runs") -Directory -Filter "pytest_tmp*" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-SafePath $_.FullName }
Get-ChildItem -Path (Join-Path $Root "runs") -File -Filter "n8n_database_inspect.sqlite*" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-SafePath $_.FullName }

if ($IncludeStaleDryRuns) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $quarantine = Join-Path $Root "runs\_cleanup_quarantine\$stamp"
    $stale = @(
        "runs\operations\task_2716fc9d10c2_dify_output.json",
        "runs\operations\task_81f792045bee_dify_output.json",
        "runs\operations\task_81f792045bee_image_prompt.json",
        "runs\generated_images\chagee_image_20260625_054200.json",
        "runs\approval_queue\run_20260625_054200"
    )
    foreach ($item in $stale) {
        $path = Join-Path $Root $item
        if (Test-Path -LiteralPath $path) {
            Move-Or-Delete $path $quarantine
        }
    }
}
