[CmdletBinding()]
param(
    [string]$BackupRoot = "G:\My Drive\Projects\Dev Orchestrator",
    [string]$RepoPath = "",
    [string]$Label = "scheduled",
    [int]$RetentionCount = 3,
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

function Test-BackupPathCandidate {
    param([string]$Candidate)
    if (-not $Candidate) { return $null }
    $clean = $Candidate.Trim().Trim('"')
    if (-not $clean) { return $null }
    if (Test-Path -LiteralPath $clean -PathType Container) {
        return (Resolve-Path -LiteralPath $clean).Path
    }
    return $null
}

function Get-CreatedBackupPathFromOutput {
    param([object[]]$OutputLines)
    $lines = @($OutputLines | ForEach-Object { [string]$_ })
    for ($index = 0; $index -lt $lines.Count; $index++) {
        $line = $lines[$index]
        if ($line -match '^\s*Created backup\s*(.*)$') {
            $parts = @()
            if ($Matches[1]) { $parts += $Matches[1].Trim() }
            foreach ($candidate in @($parts -join "", $parts -join " ")) {
                $resolved = Test-BackupPathCandidate -Candidate $candidate
                if ($resolved) { return $resolved }
            }

            for ($next = $index + 1; $next -lt $lines.Count; $next++) {
                $nextLine = $lines[$next].Trim()
                if ($nextLine -match '^(Manifest:|Files:|Total bytes:|Protected:|Warnings:)') { break }
                if (-not $nextLine) { continue }
                $parts += $nextLine
                foreach ($candidate in @($nextLine, ($parts -join ""), ($parts -join " "))) {
                    $resolved = Test-BackupPathCandidate -Candidate $candidate
                    if ($resolved) { return $resolved }
                }
            }
        }
    }
    return $null
}

function Get-CreatedBackupPathFromManifestFallback {
    param(
        [string]$Root,
        [string]$ExpectedLabel,
        [datetime]$StartedAtUtc
    )
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return $null }

    $candidates = @()
    foreach ($folder in Get-ChildItem -LiteralPath $Root -Directory -Filter "devo-workspace-backup-*") {
        $manifestPath = Join-Path $folder.FullName "backup-manifest.json"
        if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { continue }
        try {
            $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
            $createdAt = ([datetime]$manifest.created_at).ToUniversalTime()
            $manifestLabel = [string]$manifest.label
            if ($manifestLabel -ne $ExpectedLabel) { continue }
            if ($createdAt -lt $StartedAtUtc) { continue }
            $candidates += [pscustomobject]@{
                Path = $folder.FullName
                CreatedAt = $createdAt
            }
        } catch {
            continue
        }
    }

    $selected = $candidates | Sort-Object CreatedAt -Descending | Select-Object -First 1
    if ($selected) { return $selected.Path }
    return $null
}

function Write-CapturedOutput {
    param(
        [object[]]$OutputLines,
        [string]$LogFile
    )
    Write-Host "Captured backup create output:"
    Add-Content -LiteralPath $LogFile -Value "Captured backup create output before path detection failure:"
    foreach ($line in $OutputLines) {
        Write-Host $line
        Add-Content -LiteralPath $LogFile -Value $line
    }
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
$scriptStartUtc = (Get-Date).ToUniversalTime()
$createOutput = Invoke-LoggedCommand -FilePath $devoPath -Arguments $createArgs -LogFile $logFile

$createdBackupPath = Get-CreatedBackupPathFromOutput -OutputLines $createOutput
if (-not $createdBackupPath) {
    $createdBackupPath = Get-CreatedBackupPathFromManifestFallback -Root $BackupRoot -ExpectedLabel $Label -StartedAtUtc $scriptStartUtc
}
if (-not $createdBackupPath -or -not (Test-Path -LiteralPath $createdBackupPath -PathType Container)) {
    Write-CapturedOutput -OutputLines $createOutput -LogFile $logFile
    throw "Could not determine created backup path."
}
if ($createdBackupPath.EndsWith(".incomplete")) {
    throw "Backup path is still incomplete, likely because backup creation was interrupted: $createdBackupPath"
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
