[CmdletBinding()]
param(
    [string]$BackupRoot = "G:\My Drive\Projects\Dev Orchestrator",
    [string]$RepoPath = "",
    [string]$Label = "scheduled",
    [int]$RetentionCount = 10,
    [bool]$Verify = $true,
    [bool]$Cleanup = $true,
    [switch]$Protect,
    [string]$LogRoot = ""
)

$ErrorActionPreference = "Stop"

function Resolve-RepoPath {
    param([string]$ProvidedPath)
    if ($ProvidedPath) { return (Resolve-Path -LiteralPath $ProvidedPath).Path }
    $scriptRoot = Split-Path -Parent $PSCommandPath
    $repoCandidate = Resolve-Path -LiteralPath (Join-Path $scriptRoot "..\..") -ErrorAction SilentlyContinue
    if ($repoCandidate) { return $repoCandidate.Path }
    return "E:\DevOrchestrator"
}

function Invoke-LoggedCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogFile
    )
    $display = "$FilePath $($Arguments -join ' ')"
    Add-Content -LiteralPath $LogFile -Value "> $display"
    $output = & $FilePath @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $output | ForEach-Object { Add-Content -LiteralPath $LogFile -Value $_ }
    if ($exitCode -ne 0) {
        throw "Command failed with exit code ${exitCode}: $display"
    }
    return $output
}

$RepoPath = Resolve-RepoPath -ProvidedPath $RepoPath
if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) {
    throw "Repo path does not exist: $RepoPath"
}

$venvPath = Join-Path $RepoPath ".venv"
$devoPath = Join-Path $RepoPath ".venv\Scripts\devo.exe"
if (-not (Test-Path -LiteralPath $venvPath -PathType Container)) {
    throw ".venv does not exist: $venvPath"
}
if (-not (Test-Path -LiteralPath $devoPath -PathType Leaf)) {
    $devoPath = Join-Path $RepoPath ".venv\Scripts\devo"
}
if (-not (Test-Path -LiteralPath $devoPath -PathType Leaf)) {
    throw "devo command does not exist under .venv\Scripts: $RepoPath"
}

if (-not $LogRoot) { $LogRoot = Join-Path $BackupRoot "logs" }
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $LogRoot "devo-backup-$timestamp.log"

Set-Location -LiteralPath $RepoPath
Add-Content -LiteralPath $logFile -Value "DevOrchestrator backup started: $(Get-Date -Format o)"
Add-Content -LiteralPath $logFile -Value "RepoPath: $RepoPath"
Add-Content -LiteralPath $logFile -Value "BackupRoot: $BackupRoot"

$createArgs = @("backup", "create", "--dest", $BackupRoot, "--label", $Label)
if ($Protect.IsPresent) { $createArgs += "--protect" }
$createOutput = Invoke-LoggedCommand -FilePath $devoPath -Arguments $createArgs -LogFile $logFile

$createdBackupPath = $null
foreach ($line in $createOutput) {
    if ($line -match "Created backup\s+(.+)$") {
        $createdBackupPath = $Matches[1].Trim()
        break
    }
}
if (-not $createdBackupPath) {
    $createdBackupPath = Get-ChildItem -LiteralPath $BackupRoot -Directory -Filter "devo-workspace-backup-*" |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $createdBackupPath -or -not (Test-Path -LiteralPath $createdBackupPath -PathType Container)) {
    throw "Could not determine created backup path."
}

if ($Verify) {
    Invoke-LoggedCommand -FilePath $devoPath -Arguments @("backup", "verify", "--path", $createdBackupPath) -LogFile $logFile | Out-Null
}

if ($Cleanup -and $Verify) {
    Invoke-LoggedCommand -FilePath $devoPath -Arguments @("backup", "cleanup", "--dest", $BackupRoot, "--keep", [string]$RetentionCount) -LogFile $logFile | Out-Null
}

Add-Content -LiteralPath $logFile -Value "DevOrchestrator backup completed: $(Get-Date -Format o)"
Write-Host "Backup created: $createdBackupPath"
Write-Host "Log: $logFile"
