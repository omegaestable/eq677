$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Missing Python virtualenv: $Python" -ForegroundColor Red
    Write-Host "Press Enter to close."
    [void][Console]::ReadLine()
    exit 1
}

New-Item -ItemType Directory -Force "run_logs\colored_magma" | Out-Null
$StopFile = "run_logs\colored_magma\primary_o11_restartable.stop"
$Solution0 = "run_logs\colored_magma\primary_o11_00_eq0_restartable_solution.json"
$Solution1 = "run_logs\colored_magma\primary_o11_00_eq1_restartable_solution.json"

if (Test-Path $StopFile) {
    if ((Test-Path $Solution0) -or (Test-Path $Solution1)) {
        Write-Host "Stop file already exists: $StopFile" -ForegroundColor Yellow
        Write-Host "A solution file also exists, so the restartable run appears solved. Remove the stop file and solution JSON only if you intentionally want to launch it again."
        Write-Host "Press Enter to close."
        [void][Console]::ReadLine()
        exit 0
    }
    Write-Host "Removing stale daily stop file: $StopFile"
    Remove-Item -Force $StopFile
}

function Start-O11Run {
    param(
        [Parameter(Mandatory = $true)][ValidateSet(0, 1)][int]$Value
    )

    $Log = "run_logs\colored_magma\primary_o11_00_eq${Value}_restartable.jsonl"
    $Out = "run_logs\colored_magma\primary_o11_00_eq${Value}_restartable_solution.json"
    $Title = "E677 O11(0,0)=$Value fine restartable"
    $Command = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
Set-Location '$Root'
& '$Python' 'explore_colored_magma.py' --mode deep --solver cadical --default-branch none --symbreak-o11-00 $Value --branch-o11-column 0 --branch-row 11:0 --propagate-branches --progress-conflicts 50000 --heartbeat-every 300 --log '$Log' --out '$Out' --resume --stop-file '$StopFile' --touch-stop-file-on-sat
Write-Host ''
Write-Host 'Run ended. Completed cubes are saved in $Log.'
Write-Host 'Double-click run_o11_restartable.cmd to resume.'
"@

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $Command
    )
}

Start-O11Run -Value 0
Start-O11Run -Value 1

Write-Host "Started two visible restartable solver windows."
Write-Host "Logs:"
Write-Host "  run_logs\colored_magma\primary_o11_00_eq0_restartable.jsonl"
Write-Host "  run_logs\colored_magma\primary_o11_00_eq1_restartable.jsonl"
Write-Host "Stop file: $StopFile"
Write-Host ""
Write-Host "Closing a solver window only loses the current fine cube; solver heartbeats are saved every 5 minutes."
