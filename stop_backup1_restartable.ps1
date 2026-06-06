param(
    [int]$PollSeconds = 5,
    [int]$MaxWaitMinutes = 0,
    [switch]$Once,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

New-Item -ItemType Directory -Force "run_logs\colored_magma" | Out-Null

$StopFile = "run_logs\colored_magma\backup1_restartable.stop"
$Worker = [PSCustomObject]@{
    Name = "backup1 O6 row0"
    Log = "run_logs\colored_magma\backup1_o6_row0_restartable.jsonl"
}

function Write-StopFile {
    $payload = [PSCustomObject]@{
        event_time = (Get-Date).ToString("s")
        reason = "daily graceful stop requested"
    }
    $payload | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 $StopFile
}

function Get-LastJsonRecord {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return $null
    }

    $lines = @(Get-Content -Tail 200 -Path $Path)
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        $line = $lines[$i].Trim()
        if (-not $line) {
            continue
        }
        try {
            return ($line | ConvertFrom-Json)
        } catch {
            continue
        }
    }
    return $null
}

function Get-WorkerProcess {
    param([string]$LogPath)

    $logLeaf = Split-Path -Leaf $LogPath
    try {
        $processes = Get-CimInstance Win32_Process
    } catch {
        $processes = Get-WmiObject Win32_Process
    }

    $processes |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -like "*explore_colored_magma.py*" -and
        $_.CommandLine -like "*$logLeaf*"
    } |
    Select-Object -First 1
}

function Format-Duration {
    param([double]$Seconds)

    if ($Seconds -lt 0) {
        $Seconds = 0
    }
    $span = [TimeSpan]::FromSeconds($Seconds)
    if ($span.TotalHours -ge 1) {
        return ("{0}h{1:00}m{2:00}s" -f [int]$span.TotalHours, $span.Minutes, $span.Seconds)
    }
    if ($span.TotalMinutes -ge 1) {
        return ("{0}m{1:00}s" -f $span.Minutes, $span.Seconds)
    }
    return ("{0:0}s" -f $span.TotalSeconds)
}

function Get-BranchEtaText {
    param($Record)

    if ($null -eq $Record) {
        return "eta unknown"
    }
    if ($Record.event -in @("run-finished", "branch-finished", "solution-verified")) {
        return "done"
    }
    if ($Record.event -eq "solver-heartbeat" -and $Record.chunks -and $Record.elapsed_seconds) {
        $secondsPerChunk = [double]$Record.elapsed_seconds / [double]$Record.chunks
        return "next stop check <= " + (Format-Duration $secondsPerChunk)
    }
    if ($Record.event -eq "branch-start") {
        return "waiting for first 50k-conflict check"
    }
    if ($Record.event -eq "solver-stop") {
        return "stop seen; closing"
    }
    return "eta unknown"
}

function Show-Monitor {
    param(
        [datetime]$StartTime,
        [object]$Row,
        [bool]$Running,
        [bool]$OldLaunch
    )

    Clear-Host
    $elapsed = (Get-Date) - $StartTime
    Write-Host "E677 backup1 graceful stop monitor"
    Write-Host "Stop file: $StopFile"
    Write-Host ("Elapsed: {0}" -f (Format-Duration $elapsed.TotalSeconds))
    Write-Host ""
    Write-Host ("Worker: {0}" -f $(if ($Running) { "running" } else { "stopped" }))
    Write-Progress -Activity "Stopping backup1 search" -Status $(if ($Running) { "waiting for worker to stop" } else { "worker stopped" }) -PercentComplete $(if ($Running) { 20 } else { 100 })
    Write-Host ""
    @($Row) | Format-Table Name, State, Pid, StopAware, Latest, Branch, Eta -AutoSize
    Write-Host ""
    if ($OldLaunch) {
        Write-Host "The running solver was started without --stop-file." -ForegroundColor Yellow
        Write-Host "Close that solver window manually when you are ready."
    } elseif ($Running) {
        Write-Host "Waiting. Stop is checked between 50k-conflict SAT chunks."
    } else {
        Write-Host "No matching Python solver worker is running."
    }
}

Write-StopFile

$start = Get-Date
$deadline = $null
if ($MaxWaitMinutes -gt 0) {
    $deadline = $start.AddMinutes($MaxWaitMinutes)
}

while ($true) {
    $proc = Get-WorkerProcess -LogPath $Worker.Log
    $record = Get-LastJsonRecord -Path $Worker.Log
    $latest = if ($record -and $record.event) { [string]$record.event } elseif ($record -and $record.status) { [string]$record.status } else { "none" }
    $branch = if ($record -and $record.branch) { [string]$record.branch } else { "" }
    if ($branch.Length -gt 44) {
        $branch = $branch.Substring(0, 41) + "..."
    }
    $eta = Get-BranchEtaText -Record $record
    $running = $null -ne $proc
    $stopAware = $running -and $proc.CommandLine -like "*--stop-file*"
    $oldLaunch = $running -and -not $stopAware

    $row = [PSCustomObject]@{
        Name = $Worker.Name
        State = if ($running) { "running" } else { "stopped" }
        Pid = if ($running) { $proc.ProcessId } else { "" }
        StopAware = if ($running) { if ($stopAware) { "yes" } else { "no" } } else { "" }
        Latest = $latest
        Branch = $branch
        Eta = if ($oldLaunch) { "manual close needed" } else { $eta }
    }

    Show-Monitor -StartTime $start -Row $row -Running $running -OldLaunch $oldLaunch

    if ($Once) {
        break
    }
    if (-not $running -or $oldLaunch) {
        break
    }
    if ($deadline -and (Get-Date) -ge $deadline) {
        Write-Host "Max wait reached."
        break
    }
    Start-Sleep -Seconds $PollSeconds
}

Write-Progress -Activity "Stopping backup1 search" -Completed
Write-Host ""
Write-Host "You can start again tomorrow with run_backup1_restartable.cmd."
if (-not $NoPause) {
    Write-Host "Press Enter to close."
    [void][Console]::ReadLine()
}
