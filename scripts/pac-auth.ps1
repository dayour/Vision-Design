<#
Helper script to authenticate Power Platform CLI (pac) to a specific Dataverse environment.
Usage: pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/pac-auth.ps1
This script will:
- Check for pac availability
- Prompt to run 'pac install latest' if pac is missing
- Run `pac auth create --url <DATAVERSE_ENVIRONMENT_URL>` using the environment set in .env
- Run `pac org who` to verify the org

Note: pac must be installed. If it's not installed, run the setup script with -AutoSystemInstall or install pac manually.
#>

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$envFile = Join-Path $RepoRoot '.env'

function Write-Info($s){ Write-Host "[INFO] $s" -ForegroundColor Cyan }
function Write-Warn($s){ Write-Host "[WARN] $s" -ForegroundColor Yellow }
function Write-Err($s){ Write-Host "[ERROR] $s" -ForegroundColor Red }

# Load .env values (simple parser)
if (-not (Test-Path $envFile)) {
    Write-Err ".env not found in repo root. Please create .env with DATAVERSE_ENVIRONMENT_URL set."
    exit 1
}

$envContent = Get-Content $envFile | Where-Object { 
    ($_ -match '=') -and -not ($_ -match '^[#]') 
}
$envDict = @{}
foreach ($line in $envContent) {
    $parts = $line -split '='
    $key = $parts[0].Trim()
    $value = ($parts[1..($parts.Length - 1)] -join '=').Trim()
    $envDict[$key] = $value
}

$dataverseUrl = $envDict['DATAVERSE_ENVIRONMENT_URL']
if (-not $dataverseUrl) {
    Write-Err "DATAVERSE_ENVIRONMENT_URL not set in .env. Please set it to your Dataverse org URL."
    exit 1
}

if (-not (Get-Command pac -ErrorAction SilentlyContinue)) {
    Write-Warn "pac CLI not found. Install it first: https://learn.microsoft.com/power-platform/developer/cli/install"
    Write-Warn "You can also run scripts/setup-windows.ps1 -AutoSystemInstall to attempt automated installation (may require elevation)."
    exit 1
}

Write-Info "Authenticating pac to Dataverse environment: $dataverseUrl"
try {
    pac auth create --url $dataverseUrl
    Write-Info "Running 'pac org who' to verify authentication..."
    pac org who
} catch {
    Write-Err "pac authentication failed: $_"
    exit 1
}

Write-Info "pac authentication script completed. If login uses interactive browser, follow prompts."