param(
    [int]$BranchMod = 8,
    [int]$BranchIndex = 1,
    [int]$ConflictBudget = 5000000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "run_logs\colored_magma"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$prefix = "primary_cadical_o11col0_probe_m${BranchMod}_i${BranchIndex}_$stamp"
$jsonLog = Join-Path $logDir "$prefix.jsonl"
$outLog = Join-Path $logDir "$prefix.out.log"
$solution = Join-Path $logDir "solution_$prefix.json"

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "Starting colored magma deep probe"
Write-Host "Working directory: $root"
Write-Host "Shard: index=$BranchIndex mod=$BranchMod"
Write-Host "Per-branch conflict budget: $ConflictBudget"
Write-Host "JSONL branch log: $jsonLog"
Write-Host "Console log: $outLog"
Write-Host ""

& $python ".\explore_colored_magma.py" `
    --mode deep `
    --config primary `
    --solver cadical `
    --branch-o11-column 0 `
    --primary-o11-symmetry `
    --branch-mod $BranchMod `
    --branch-index $BranchIndex `
    --conflicts $ConflictBudget `
    --progress-every 60 `
    --progress-conflicts 50000 `
    --log $jsonLog `
    --resume `
    --out $solution `
    2>&1 | Tee-Object -FilePath $outLog

$exitCode = $LASTEXITCODE
Write-Host ""
Write-Host "Run finished with exit code $exitCode"
Write-Host "JSONL branch log: $jsonLog"
Write-Host "Console log: $outLog"
exit $exitCode
