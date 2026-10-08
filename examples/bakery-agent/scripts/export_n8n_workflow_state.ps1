param(
    [string]$Container = "bakery-ai-agent-n8n",
    [string]$OutDir = "runs",
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Assert-UnderRoot {
    param([string]$Path)
    $rootFull = [System.IO.Path]::GetFullPath($Root.Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $targetFull = [System.IO.Path]::GetFullPath($Path)
    return $targetFull.Equals($rootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $targetFull.StartsWith($rootFull + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -or
        $targetFull.StartsWith($rootFull + [System.IO.Path]::AltDirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)
}

$ResolvedOutDir = Resolve-Path $OutDir -ErrorAction SilentlyContinue
if (-not $ResolvedOutDir) {
    $ResolvedOutDir = New-Item -ItemType Directory -Path $OutDir -Force
}
if (-not (Assert-UnderRoot $ResolvedOutDir.Path)) {
    throw "OutDir must stay under workspace root: $($Root.Path)"
}

$base = Join-Path $ResolvedOutDir.Path "n8n_database_inspect.sqlite"
$targets = @($base, "$base-wal", "$base-shm")
foreach ($target in $targets) {
    if ((Test-Path -LiteralPath $target) -and (Assert-UnderRoot $target)) {
        Remove-Item -LiteralPath $target -Force
    }
}

docker cp "$Container`:/home/node/.n8n/database.sqlite" $base | Out-Null
docker cp "$Container`:/home/node/.n8n/database.sqlite-wal" "$base-wal" | Out-Null
docker cp "$Container`:/home/node/.n8n/database.sqlite-shm" "$base-shm" | Out-Null

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

$args = @("scripts\inspect_n8n_workflows.py", "--db", $base)
if ($Json) {
    $args += "--json"
}
& $python @args
