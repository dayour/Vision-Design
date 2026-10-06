<#
Persist PAC authentication profile details into .env (non-sensitive information only).
This script will:
 - Call `pac org who --output json` if available to collect org and user details
 - Fall back to parsing textual output of `pac org who` if JSON output is not supported
 - Append non-sensitive keys to .env (org id, environment id, user email, etc.) after backing up .env
#>

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$envPath = Join-Path $repoRoot '..\.env'
if (-not (Test-Path $envPath)) {
    Write-Error ".env not found in repo root. Please run scripts/pac-auth.ps1 to create/validate authentication first."
    exit 1
}

# Backup
$backup = "$envPath.backup"
Copy-Item -Path $envPath -Destination $backup -Force
Write-Host "Backed up .env to $backup"

# Try JSON output
$whoJson = $null
try {
    $whoJsonText = & pac org who --output json 2>$null
    if ($LASTEXITCODE -eq 0 -and $whoJsonText) {
        $whoJson = $whoJsonText | ConvertFrom-Json
    }
} catch {
    # ignore
}

if (-not $whoJson) {
    # Fallback to parsing plain output
    $whoText = & pac org who 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to run 'pac org who'. Ensure pac is installed and authenticated. Output: $whoText"
        exit 1
    }

    # Parse common lines
    $lines = $whoText -split "`n"
    $pacProfile = @{}
    foreach ($line in $lines) {
        if ($line -match "Org ID:\s*(.+)") { $pacProfile.orgId = $matches[1].Trim() }
        if ($line -match "Environment ID:\s*(.+)") { $pacProfile.environmentId = $matches[1].Trim() }
        if ($line -match "Org URL:\s*(https?://\S+)") { $pacProfile.orgUrl = $matches[1].Trim() }
        if ($line -match "User Email:\s*(\S+@\S+)") { $pacProfile.userEmail = $matches[1].Trim() }
        if ($line -match "User ID:\s*(\S+)") { $pacProfile.userId = $matches[1].Trim() }
        if ($line -match "Unique Name:\s*(\S+)") { $pacProfile.uniqueName = $matches[1].Trim() }
        if ($line -match "Friendly Name:\s*(.+)") { $pacProfile.friendlyName = $matches[1].Trim() }
    }
} else {
    # Map known JSON properties - be permissive with naming
    $pacProfile = @{}
    if ($whoJson.organizationId) { $pacProfile.orgId = $whoJson.organizationId }
    if ($whoJson.environmentId) { $pacProfile.environmentId = $whoJson.environmentId }
    if ($whoJson.url) { $pacProfile.orgUrl = $whoJson.url }
    if ($whoJson.userId) { $pacProfile.userId = $whoJson.userId }
    if ($whoJson.userName) { $pacProfile.userEmail = $whoJson.userName }
    if ($whoJson.uniqueName) { $pacProfile.uniqueName = $whoJson.uniqueName }
    if ($whoJson.friendlyName) { $pacProfile.friendlyName = $whoJson.friendlyName }
}

if (-not $pacProfile.orgId) {
    Write-Error "Could not determine organization details from pac org who output. Aborting."
    exit 1
}

# Prepare .env lines - do not include tokens or other secrets
$linesToAppend = @(
    "# PAC auth/profile details (non-sensitive)",
    "PAC_AUTH_USER=$($pacProfile.userEmail -replace '\\r|\\n','')",
    "PAC_AUTH_USER_ID=$($pacProfile.userId -replace '\\r|\\n','')",
    "PAC_ORG_ID=$($pacProfile.orgId -replace '\\r|\\n','')",
    "PAC_ORG_UNIQUE_NAME=$($pacProfile.uniqueName -replace '\\r|\\n','')",
    "PAC_ORG_FRIENDLY_NAME=$($pacProfile.friendlyName -replace '\\r|\\n','')",
    "PAC_ORG_URL=$($pacProfile.orgUrl -replace '\\r|\\n','')",
    "PAC_ENVIRONMENT_ID=$($pacProfile.environmentId -replace '\\r|\\n','')",
    ""
)

Add-Content -Path $envPath -Value ($linesToAppend -join "`n")
Write-Host "PAC profile information appended to .env (non-sensitive fields). Please verify .env and ensure secrets are not stored here."