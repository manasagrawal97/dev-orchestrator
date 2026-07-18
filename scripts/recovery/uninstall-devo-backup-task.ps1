[CmdletBinding()]
param(
    [string]$TaskName = "DevOrchestrator Workspace Backup"
)

$ErrorActionPreference = "Stop"
if (-not (Get-Module -ListAvailable -Name ScheduledTasks)) { throw "ScheduledTasks module is not available." }
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Unregistered scheduled task: $TaskName"
} else {
    Write-Host "Scheduled task does not exist; no action taken: $TaskName"
}
