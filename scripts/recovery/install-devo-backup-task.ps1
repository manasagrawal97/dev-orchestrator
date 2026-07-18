[CmdletBinding()]
param(
    [string]$BackupRoot = "G:\My Drive\Projects\Dev Orchestrator",
    [string]$RepoPath = "E:\DevOrchestrator",
    [string]$TaskName = "DevOrchestrator Workspace Backup",
    [ValidateSet("Every12Hours", "Daily")]
    [string]$Frequency = "Every12Hours",
    [datetime]$StartTime = (Get-Date).Date.AddHours(9),
    [switch]$RunNow,
    [int]$RetentionCount = 10
)

$ErrorActionPreference = "Stop"
if (-not (Get-Module -ListAvailable -Name ScheduledTasks)) { throw "ScheduledTasks module is not available." }
if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) { throw "Repo path does not exist: $RepoPath" }

$scriptPath = Join-Path $RepoPath "scripts\recovery\backup-devo-workspace.ps1"
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "Backup script does not exist: $scriptPath" }

$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -RepoPath `"$RepoPath`" -BackupRoot `"$BackupRoot`" -Label `"scheduled`" -RetentionCount $RetentionCount"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
if ($Frequency -eq "Every12Hours") {
    $trigger = New-ScheduledTaskTrigger -Once -At $StartTime -RepetitionInterval (New-TimeSpan -Hours 12) -RepetitionDuration (New-TimeSpan -Days 3650)
} else {
    $trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
}

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Creates verified DevOrchestrator workspace backups." -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName"
Write-Host "Frequency: $Frequency"
Write-Host "BackupRoot: $BackupRoot"
if ($RunNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Started scheduled task once: $TaskName"
}
