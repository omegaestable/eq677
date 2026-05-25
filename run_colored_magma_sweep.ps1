$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "run_logs\colored_magma"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $logDir "affine_o11_projection_sweep_$stamp.log"

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "Starting colored magma #1 sweep"
Write-Host "Working directory: $root"
Write-Host "Log: $log"
Write-Host ""

& $python ".\explore_colored_magma.py" `
    --config primary `
    --mode affine-o11-projection-sweep `
    --solver cadical `
    --progress-every 60 `
    2>&1 | Tee-Object -FilePath $log

$exitCode = $LASTEXITCODE
Write-Host ""
Write-Host "Run finished with exit code $exitCode"
Write-Host "Log: $log"
exit $exitCode
