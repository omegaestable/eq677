param(
    [int]$ConflictBudget = 2000000,
    [int]$ProgressConflicts = 50000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "run_logs\colored_candidates"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$consoleLog = Join-Path $logDir "colored_candidate_sweep_$stamp.log"

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$candidates = @(
    @{ p = 7;  q = 7; A = 4;  B = 3;  bad = 3;  note = "small top-ranked nondegenerate" },
    @{ p = 7;  q = 7; A = 4;  B = 1;  bad = 0;  note = "small alternate bad slope zero" },
    @{ p = 13; q = 7; A = 9;  B = 11; bad = 9;  note = "first p=13 candidate" },
    @{ p = 19; q = 7; A = 7;  B = 3;  bad = 16; note = "p19 backup-style candidate" },
    @{ p = 19; q = 7; A = 7;  B = 4;  bad = 5;  note = "p19 primary base without primary fixed seed" },
    @{ p = 31; q = 7; A = 5;  B = 9;  bad = 17; note = "p31 backup2-style candidate" },
    @{ p = 37; q = 7; A = 26; B = 24; bad = 29; note = "p37 candidate" },
    @{ p = 37; q = 7; A = 26; B = 2;  bad = 27; note = "p37 alternate" },
    @{ p = 43; q = 7; A = 6;  B = 15; bad = 12; note = "p43 candidate" },
    @{ p = 43; q = 7; A = 36; B = 14; bad = 8;  note = "p43 alternate" }
)

function Write-RunLine {
    param([string]$Message)
    $Message | Tee-Object -FilePath $consoleLog -Append
}

function Invoke-LoggedCommand {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$Arguments
    )
    Write-RunLine ""
    Write-RunLine "===== $Name ====="
    Write-RunLine "Command: $Executable $($Arguments -join ' ')"
    $start = Get-Date
    & $Executable @Arguments 2>&1 | Tee-Object -FilePath $consoleLog -Append
    $exitCode = $LASTEXITCODE
    $elapsed = (Get-Date) - $start
    Write-RunLine "Exit code: $exitCode"
    Write-RunLine ("Elapsed: {0:hh\:mm\:ss}" -f $elapsed)
    return $exitCode
}

Write-RunLine "Starting targeted colored F_p x F_q candidate sweep"
Write-RunLine "Working directory: $root"
Write-RunLine "Console log: $consoleLog"
Write-RunLine "ConflictBudget=$ConflictBudget ProgressConflicts=$ProgressConflicts"

Invoke-LoggedCommand "rank nondegenerate colored candidates" $python @(
    "scripts\e677_construct.py", "colored-candidates", "--max-prime", "200", "--q", "7", "--top", "30", "--show-commands"
) | Out-Null

foreach ($candidate in $candidates) {
    $name = "p$($candidate.p)_q$($candidate.q)_A$($candidate.A)_B$($candidate.B)_bad$($candidate.bad)"
    $jsonLog = Join-Path $logDir "$name`_$stamp.jsonl"
    $solution = Join-Path $logDir "solution_$name`_$stamp.json"
    Write-RunLine ""
    Write-RunLine "##### Candidate $name #####"
    Write-RunLine "Note: $($candidate.note)"

    Invoke-LoggedCommand "stats $name" $python @(
        ".\explore_colored_magma.py",
        "--config", "custom",
        "--p", "$($candidate.p)",
        "--q", "$($candidate.q)",
        "--A", "$($candidate.A)",
        "--B", "$($candidate.B)",
        "--bad-slope", "$($candidate.bad)",
        "--mode", "stats",
        "--quiet"
    ) | Out-Null

    $exitCode = Invoke-LoggedCommand "deep bounded $name" $python @(
        ".\explore_colored_magma.py",
        "--config", "custom",
        "--p", "$($candidate.p)",
        "--q", "$($candidate.q)",
        "--A", "$($candidate.A)",
        "--B", "$($candidate.B)",
        "--bad-slope", "$($candidate.bad)",
        "--mode", "deep",
        "--solver", "cadical",
        "--default-branch", "none",
        "--propagate-branches",
        "--conflicts", "$ConflictBudget",
        "--progress-conflicts", "$ProgressConflicts",
        "--log", $jsonLog,
        "--out", $solution
    )

    if ($exitCode -eq 0) {
        Write-RunLine "Candidate produced a verified result or solution; stopping sweep."
        exit 0
    }
    if ($exitCode -eq 1) {
        Write-RunLine "Candidate killed as UNSAT under current seed/assumptions."
        continue
    }
    if ($exitCode -eq 3) {
        Write-RunLine "Candidate unresolved under conflict budget; continuing."
        continue
    }
    Write-RunLine "Candidate returned exit code $exitCode; stopping for inspection."
    exit $exitCode
}

Write-RunLine ""
Write-RunLine "Targeted colored candidate sweep finished."
Write-RunLine "Console log: $consoleLog"
exit 0