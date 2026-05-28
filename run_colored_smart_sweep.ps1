param(
    [int]$P = 7,
    [int]$Q = 7,
    [int]$Alpha = 4,
    [int]$Beta = 3,
    [int]$BadSlope = 3,
    [string]$BranchRow = "1:0",
    [int]$ShardCount = 8,
    [int]$ConflictBudget = 500000,
    [int]$ProgressConflicts = 50000,
    [switch]$NoResume,
    [switch]$NoPopup,
    [switch]$SummaryOnly,
    [switch]$NoCompact
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "run_logs\colored_smart"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$branchParts = $BranchRow.Split(":")
if ($branchParts.Count -ge 2) {
    $branchLabel = "O$($branchParts[0])_row$($branchParts[1])"
} else {
    $branchLabel = $BranchRow -replace "[:=,]", "_"
}
$name = "p$($P)_q$($Q)_A$($Alpha)_B$($Beta)_bad$($BadSlope)_$branchLabel"

function Get-ShardLogPath {
    param([int]$Shard)
    return (Join-Path $logDir "$name`_shard$Shard.jsonl")
}

function Get-ShardSolutionPath {
    param([int]$Shard)
    return (Join-Path $logDir "solution_$name`_shard$Shard.json")
}

function Write-LatestSummary {
    param([bool]$Compact)

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $summaryPath = Join-Path $logDir "$name`_summary_$stamp.json"
    $shards = @()

    for ($shard = 0; $shard -lt $ShardCount; $shard++) {
        $path = Get-ShardLogPath -Shard $shard
        $latest = @{}
        $recordCount = 0

        if (Test-Path $path) {
            Get-Content $path | Where-Object { $_.Trim() } | ForEach-Object {
                $recordCount++
                $record = $_ | ConvertFrom-Json
                $latest[[int]$record.branch_no] = $record
            }

            if ($Compact -and $recordCount -gt $latest.Count) {
                $tmp = "$path.tmp"
                $latest.GetEnumerator() |
                    Sort-Object Name |
                    ForEach-Object { $_.Value | ConvertTo-Json -Compress -Depth 20 } |
                    Set-Content -Path $tmp -Encoding utf8
                Move-Item -Force $tmp $path
                $recordCount = $latest.Count
            }
        }

        $counts = @{}
        foreach ($record in $latest.Values) {
            $counts[$record.status] = 1 + [int]($counts[$record.status])
        }

        $shards += [PSCustomObject]@{
            shard = $shard
            records = $recordCount
            branches = $latest.Count
            unknown = [int]$counts["unknown"]
            unsat_prop = [int]$counts["unsat-prop"]
            unsat = [int]$counts["unsat"]
            sat = [int]$counts["sat"] + [int]$counts["verified-sat"] + [int]$counts["bad-model"]
            log = if (Test-Path $path) { Split-Path -Leaf $path } else { $null }
        }
    }

    $summary = [PSCustomObject]@{
        created_at = (Get-Date).ToString("s")
        candidate = "p=$P q=$Q A=$Alpha B=$Beta bad=$BadSlope"
        branch_row = $BranchRow
        conflict_budget = $ConflictBudget
        resume = -not $NoResume
        total_branches = ($shards | Measure-Object branches -Sum).Sum
        unknown = ($shards | Measure-Object unknown -Sum).Sum
        unsat_prop = ($shards | Measure-Object unsat_prop -Sum).Sum
        unsat = ($shards | Measure-Object unsat -Sum).Sum
        sat = ($shards | Measure-Object sat -Sum).Sum
        shards = $shards
    }

    $summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding utf8
    Write-Host "Summary: $summaryPath"
    $shards | Format-Table shard,branches,unknown,unsat_prop,unsat,sat,log -AutoSize
    Write-Host "Totals: branches=$($summary.total_branches) unknown=$($summary.unknown) unsat-prop=$($summary.unsat_prop) unsat=$($summary.unsat) sat=$($summary.sat)"
}

if (-not $NoCompact) {
    Write-LatestSummary -Compact $true
}

if ($SummaryOnly) {
    exit 0
}

for ($shard = 0; $shard -lt $ShardCount; $shard++) {
    $log = Get-ShardLogPath -Shard $shard
    $solution = Get-ShardSolutionPath -Shard $shard
    $arguments = @(
        ".\explore_colored_magma.py",
        "--config", "custom",
        "--p", "$P",
        "--q", "$Q",
        "--A", "$Alpha",
        "--B", "$Beta",
        "--bad-slope", "$BadSlope",
        "--mode", "deep",
        "--solver", "cadical",
        "--default-branch", "none",
        "--branch-row", $BranchRow,
        "--branch-mod", "$ShardCount",
        "--branch-index", "$shard",
        "--propagate-branches",
        "--conflicts", "$ConflictBudget",
        "--progress-conflicts", "$ProgressConflicts",
        "--log", $log,
        "--out", $solution
    )
    if (-not $NoResume) {
        $arguments += "--resume"
    }

    if ($NoPopup) {
        & $python @arguments
        $exitCode = $LASTEXITCODE
        if ($exitCode -notin @(0, 1, 3)) {
            exit $exitCode
        }
        continue
    }

    $argLine = $arguments -join " "
    $command = "cd '$root'; & '$python' $argLine"
    Start-Process powershell.exe -ArgumentList @("-NoExit", "-Command", $command)
}

if ($NoPopup) {
    Write-LatestSummary -Compact (-not $NoCompact)
} else {
    Write-Host "Launched $ShardCount colored smart shard pop-up terminal(s)."
    Write-Host "Candidate: p=$P q=$Q A=$Alpha B=$Beta bad=$BadSlope"
    Write-Host "Branch row: $BranchRow"
    Write-Host "Conflict budget: $ConflictBudget"
    Write-Host "Logs: $logDir"
}