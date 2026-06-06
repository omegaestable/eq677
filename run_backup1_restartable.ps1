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
$StopFile = "run_logs\colored_magma\backup1_restartable.stop"
$Solution = "run_logs\colored_magma\backup1_o6_row0_restartable_solution.json"

if (Test-Path $StopFile) {
    if (Test-Path $Solution) {
        Write-Host "Stop file already exists: $StopFile" -ForegroundColor Yellow
        Write-Host "A solution file also exists, so this run appears solved. Remove both only if you intentionally want to launch it again."
        Write-Host "Press Enter to close."
        [void][Console]::ReadLine()
        exit 0
    }
    Write-Host "Removing stale daily stop file: $StopFile"
    Remove-Item -Force $StopFile
}

$Log = "run_logs\colored_magma\backup1_o6_row0_restartable.jsonl"
$Title = "E677 backup1 O6 row0 restartable"
$Command = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
Set-Location '$Root'
& '$Python' 'explore_colored_magma.py' --config backup1 --mode deep --solver cadical --branch-row 6:0 --propagate-branches --progress-conflicts 50000 --heartbeat-every 300 --log '$Log' --out '$Solution' --resume --stop-file '$StopFile' --touch-stop-file-on-sat
Write-Host ''
Write-Host 'Run ended. Completed cubes are saved in $Log.'
Write-Host 'Double-click run_backup1_restartable.cmd to resume.'
"@

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", $Command
)

Write-Host "Started visible backup1 restartable solver window."
Write-Host "Log: $Log"
Write-Host "Stop file: $StopFile"
Write-Host ""
Write-Host "This is the next size-133 colored-slope target after the primary O11 split was exhausted."
Write-Host "Branching: backup1, O_6 row 0, 5040 cubes."
