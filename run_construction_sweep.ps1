param(
    [int]$TimeoutMs = 60000,
    [int]$MaxNodes = 5000000,
    [int]$MaxCandidates = 2000000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "run_logs\construction_sweeps"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $logDir "construction_sweep_$stamp.log"

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

function Write-RunLine {
    param([string]$Message)
    $Message | Tee-Object -FilePath $log -Append
}

function Invoke-ConstructStep {
    param(
        [string]$Name,
        [string[]]$Arguments
    )

    Write-RunLine ""
    Write-RunLine "===== $Name ====="
    Write-RunLine "Command: $python scripts\e677_construct.py $($Arguments -join ' ')"
    $start = Get-Date
    & $python "scripts\e677_construct.py" @Arguments 2>&1 | Tee-Object -FilePath $log -Append
    $exitCode = $LASTEXITCODE
    $elapsed = (Get-Date) - $start
    Write-RunLine "Exit code: $exitCode"
    Write-RunLine ("Elapsed: {0:hh\:mm\:ss}" -f $elapsed)
    if ($exitCode -eq 2) {
        Write-RunLine "A candidate violating E255 was reported; stopping sweep."
        exit 2
    }
    if ($exitCode -ne 0) {
        Write-RunLine "Step failed; stopping sweep."
        exit $exitCode
    }
}

Write-RunLine "Starting longer E677 construction sweep"
Write-RunLine "Working directory: $root"
Write-RunLine "Log: $log"
Write-RunLine "TimeoutMs=$TimeoutMs MaxNodes=$MaxNodes MaxCandidates=$MaxCandidates"

Invoke-ConstructStep "linear bases through 500" @(
    "linear-bases", "--max-prime", "500"
)

Invoke-ConstructStep "affine cyclic laws through order 80" @(
    "affine", "--max-order", "80", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "translation permutations through order 9" @(
    "translation", "--max-order", "9", "--exhaustive-order", "9", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "random translation permutations through order 45" @(
    "translation", "--max-order", "45", "--exhaustive-order", "8", "--samples-per-order", "20000", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "cubic polynomial translations through F_47" @(
    "polynomial-translation", "--max-prime", "47", "--degree", "3", "--zero-value", "0", "--max-candidates", "$MaxCandidates", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "quartic polynomial translations through F_29" @(
    "polynomial-translation", "--max-prime", "29", "--degree", "4", "--zero-value", "0", "--max-candidates", "$MaxCandidates", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "coset translations F31 index 3" @(
    "coset-translation", "--prime", "31", "--index", "3", "--zero-value", "0", "--max-candidates", "$MaxCandidates", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "coset translations F43 index 3" @(
    "coset-translation", "--prime", "43", "--index", "3", "--zero-value", "0", "--max-candidates", "$MaxCandidates", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "coset translations F41 index 4" @(
    "coset-translation", "--prime", "41", "--index", "4", "--zero-value", "0", "--max-candidates", "$MaxCandidates", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "coset translations F61 index 4 bounded" @(
    "coset-translation", "--prime", "61", "--index", "4", "--zero-value", "0", "--max-candidates", "$MaxCandidates", "--max-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "affine colors p5 q5 nonuniform homogeneous" @(
    "affine-colors", "--prime", "5", "--q", "5", "--alpha", "2", "--beta", "4", "--no-uniform-first", "--no-constants", "--max-models", "50", "--max-full-hits", "100", "--timeout-ms", "$TimeoutMs", "--max-nodes", "$MaxNodes", "--stop-on-bad"
)

Invoke-ConstructStep "affine colors p7 q5 nonuniform homogeneous" @(
    "affine-colors", "--prime", "7", "--q", "5", "--alpha", "4", "--beta", "1", "--no-uniform-first", "--no-constants", "--max-models", "50", "--max-full-hits", "100", "--timeout-ms", "$TimeoutMs", "--max-nodes", "$MaxNodes", "--stop-on-bad"
)

Invoke-ConstructStep "affine colors p11 q5 nonuniform homogeneous" @(
    "affine-colors", "--prime", "11", "--q", "5", "--alpha", "4", "--beta", "8", "--no-uniform-first", "--no-constants", "--max-models", "50", "--max-full-hits", "100", "--timeout-ms", "$TimeoutMs", "--max-nodes", "$MaxNodes", "--stop-on-bad"
)

Invoke-ConstructStep "affine colors primary p19 q7 uniform" @(
    "affine-colors", "--prime", "19", "--q", "7", "--alpha", "7", "--beta", "4", "--uniform-only", "--max-models", "100", "--max-full-hits", "200", "--stop-on-bad"
)

Invoke-ConstructStep "affine colors backup p19 q7 uniform" @(
    "affine-colors", "--prime", "19", "--q", "7", "--alpha", "7", "--beta", "3", "--uniform-only", "--max-models", "100", "--max-full-hits", "200", "--stop-on-bad"
)

Write-RunLine ""
Write-RunLine "Construction sweep finished without an E255-violating E677 hit."
Write-RunLine "Log: $log"
exit 0