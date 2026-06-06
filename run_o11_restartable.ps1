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
& '$Python' 'explore_colored_magma.py' --mode deep --solver cadical --default-branch none --symbreak-o11-00 $Value --branch-o11-column 0 --branch-row 11:0 --propagate-branches --progress-conflicts 50000 --log '$Log' --out '$Out' --resume
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
Write-Host ""
Write-Host "Closing a solver window only loses the current fine cube; completed cubes resume from the JSONL logs."
