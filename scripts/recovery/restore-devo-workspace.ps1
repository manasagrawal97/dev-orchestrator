[CmdletBinding()]
param(
    [string]$BackupRoot = "G:\My Drive\Projects\Dev Orchestrator",
    [string]$RepoPath = "E:\DevOrchestrator",
    [switch]$InstallSchedule = $true,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Invoke-Devo {
    param([string]$DevoPath, [string[]]$Arguments)
    $output = & $DevoPath @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $output | ForEach-Object { Write-Host $_ }
    if ($exitCode -ne 0) { throw "devo command failed with exit code ${exitCode}: $($Arguments -join ' ')" }
    return $output
}

function Get-LatestValidBackup {
    param([string]$Root)
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw "Backup root does not exist: $Root" }
    $valid = @()
    foreach ($folder in Get-ChildItem -LiteralPath $Root -Directory -Filter "devo-workspace-backup-*") {
        $manifest = Join-Path $folder.FullName "backup-manifest.json"
        if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) { continue }
        try {
            $data = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
            $valid += [pscustomobject]@{ Path = $folder.FullName; CreatedAt = [datetime]$data.created_at }
        } catch {
            continue
        }
    }
    return $valid | Sort-Object CreatedAt -Descending | Select-Object -First 1
}

if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) { throw "Repo path does not exist: $RepoPath" }
Set-Location -LiteralPath $RepoPath

$venvPath = Join-Path $RepoPath ".venv"
if (-not (Test-Path -LiteralPath $venvPath -PathType Container)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Failed to create .venv" }
}

$pythonPath = Join-Path $RepoPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { $pythonPath = Join-Path $RepoPath ".venv\Scripts\python" }
& $pythonPath -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    & $pythonPath -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw "Failed to install DevOrchestrator dependencies." }
}

$devoPath = Join-Path $RepoPath ".venv\Scripts\devo.exe"
if (-not (Test-Path -LiteralPath $devoPath -PathType Leaf)) { $devoPath = Join-Path $RepoPath ".venv\Scripts\devo" }
if (-not (Test-Path -LiteralPath $devoPath -PathType Leaf)) { throw "devo command not found after install." }

$latest = Get-LatestValidBackup -Root $BackupRoot
if (-not $latest) { throw "No valid DevOrchestrator backup found under $BackupRoot" }
Invoke-Devo -DevoPath $devoPath -Arguments @("backup", "verify", "--path", $latest.Path) | Out-Null

$workspacePath = Join-Path $RepoPath "workspace"
if (Test-Path -LiteralPath $workspacePath -PathType Container) {
    $hasContent = @(Get-ChildItem -LiteralPath $workspacePath -Force).Count -gt 0
    if ($hasContent) {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $preRestorePath = Join-Path $RepoPath "workspace.pre-restore-$stamp"
        Move-Item -LiteralPath $workspacePath -Destination $preRestorePath
        Write-Host "Existing workspace moved to: $preRestorePath"
    }
}

Invoke-Devo -DevoPath $devoPath -Arguments @("backup", "restore", "--backup", $latest.Path, "--dest", $workspacePath) | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $workspacePath "projects") -PathType Container)) { throw "Restored workspace is missing projects." }
if (-not (Test-Path -LiteralPath (Join-Path $workspacePath "runs") -PathType Container)) { throw "Restored workspace is missing runs." }
$backupCurrent = Join-Path $latest.Path "workspace\current.json"
if ((Test-Path -LiteralPath $backupCurrent -PathType Leaf) -and -not (Test-Path -LiteralPath (Join-Path $workspacePath "current.json") -PathType Leaf)) {
    throw "Backup included current.json but restored workspace is missing current.json."
}

if ($InstallSchedule) {
    & (Join-Path $RepoPath "scripts\recovery\install-devo-backup-task.ps1") -RepoPath $RepoPath -BackupRoot $BackupRoot
}

Write-Host "Restore complete."
Write-Host "Backup restored: $($latest.Path)"
Write-Host "Workspace: $workspacePath"
