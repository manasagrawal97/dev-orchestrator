[CmdletBinding()]
param(
    [string]$BackupRoot = "G:\My Drive\Projects\Dev Orchestrator",
    [string]$RepoPath = "E:\DevOrchestrator",
    [string]$TaskName = "DevOrchestrator Workspace Backup"
)

$ErrorActionPreference = "Continue"
$failures = 0
$warnings = 0

function Write-Check {
    param([string]$Status, [string]$Message)
    Write-Host "[$Status] $Message"
    if ($Status -eq "FAIL") { $script:failures++ }
    if ($Status -eq "WARN") { $script:warnings++ }
}

function Get-LatestValidBackup {
    param([string]$Root)
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return $null }
    $valid = @()
    foreach ($folder in Get-ChildItem -LiteralPath $Root -Directory -Filter "devo-workspace-backup-*") {
        $manifest = Join-Path $folder.FullName "backup-manifest.json"
        if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) { continue }
        try {
            $data = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
            $valid += [pscustomobject]@{ Path = $folder.FullName; CreatedAt = [datetime]$data.created_at; Protected = [bool]$data.protected; Label = $data.label }
        } catch {
            continue
        }
    }
    return $valid | Sort-Object CreatedAt -Descending
}

if (Test-Path -LiteralPath (Join-Path $RepoPath ".git") -PathType Container) {
    Write-Check "PASS" "Git repo exists: $RepoPath"
    Push-Location $RepoPath
    $branch = git branch --show-current 2>$null
    $commit = git rev-parse HEAD 2>$null
    Pop-Location
    Write-Check "PASS" "Git branch/commit: $branch $commit"
} else {
    Write-Check "FAIL" "Git repo missing: $RepoPath"
}

$devoPath = Join-Path $RepoPath ".venv\Scripts\devo.exe"
if (-not (Test-Path -LiteralPath $devoPath -PathType Leaf)) { $devoPath = Join-Path $RepoPath ".venv\Scripts\devo" }
if (Test-Path -LiteralPath (Join-Path $RepoPath ".venv") -PathType Container) { Write-Check "PASS" ".venv exists" } else { Write-Check "FAIL" ".venv missing" }
if (Test-Path -LiteralPath $devoPath -PathType Leaf) {
    & $devoPath --help *> $null
    if ($LASTEXITCODE -eq 0) { Write-Check "PASS" "devo command works" } else { Write-Check "FAIL" "devo command failed" }
} else {
    Write-Check "FAIL" "devo command missing"
}

if (Test-Path -LiteralPath (Join-Path $RepoPath "workspace") -PathType Container) { Write-Check "PASS" "workspace exists" } else { Write-Check "FAIL" "workspace missing" }

$backups = @(Get-LatestValidBackup -Root $BackupRoot)
if ($backups.Count -gt 0) {
    $latest = $backups[0]
    Write-Check "PASS" "Latest backup exists: $($latest.Path)"
    if (Test-Path -LiteralPath $devoPath -PathType Leaf) {
        & $devoPath backup verify --path $latest.Path *> $null
        if ($LASTEXITCODE -eq 0) { Write-Check "PASS" "Latest backup verifies" } else { Write-Check "FAIL" "Latest backup verification failed" }
    }
    $age = (Get-Date) - $latest.CreatedAt
    Write-Host "Latest backup age: $([math]::Round($age.TotalHours, 1)) hours"
    if ($age.TotalHours -gt 24) { Write-Check "WARN" "Latest backup is older than 24 hours" }
    Write-Host "Latest retained normal backups:"
    $backups | Where-Object { -not $_.Protected } | Select-Object -First 3 | ForEach-Object { Write-Host "  $($_.CreatedAt.ToString('o')) $($_.Path)" }
    Write-Host "Protected backups:"
    $backups | Where-Object { $_.Protected } | ForEach-Object { Write-Host "  $($_.CreatedAt.ToString('o')) $($_.Path)" }
} else {
    Write-Check "FAIL" "No valid backup found under $BackupRoot"
}

if (Get-Module -ListAvailable -Name ScheduledTasks) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) { Write-Check "PASS" "Scheduled task exists: $TaskName" } else { Write-Check "WARN" "Scheduled task missing: $TaskName" }
} else {
    Write-Check "WARN" "ScheduledTasks module unavailable"
}

if ($failures -gt 0) {
    Write-Host "Summary: FAIL ($failures failures, $warnings warnings)"
    exit 1
}
if ($warnings -gt 0) {
    Write-Host "Summary: WARN ($warnings warnings)"
    exit 0
}
Write-Host "Summary: PASS"
