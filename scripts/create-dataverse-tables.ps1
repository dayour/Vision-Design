<#
PowerShell wrapper to run the Dataverse table creation script.
This wrapper will:
 - Ensure .env exists and is readable
 - Back up .env to .env.backup before making changes
 - Invoke the Python helper script to create the tables
 - Print the JSON result
#>

param(
    [switch]$Force
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$envPath = Join-Path $repoRoot '..\.env' | Resolve-Path -ErrorAction SilentlyContinue
if (-not $envPath) {
    Write-Error ".env not found in repo root. Please create and configure .env with DATAVERSE_ENVIRONMENT_URL, and credentials if using client credentials.";
    exit 1
}

$envPath = (Join-Path $repoRoot '..\.env')
$backup = "$envPath.backup"
Copy-Item -Path $envPath -Destination $backup -Force
Write-Host "Backed up .env to $backup"

if (-not $Force) {
    $confirm = Read-Host "This operation may create Dataverse tables and requires admin permissions. Proceed? (y/N)"
    if ($confirm.ToLower() -ne 'y') {
        Write-Host "Operation cancelled by user."
        exit 0
    }
}

# Run Python script
$python = "python"
# Run the helper as a module so package imports resolve from repo root
$moduleArgs = "-m backend.tools.create_dataverse_tables"
Write-Host "Running: $python $moduleArgs"
$processOutput = & $python -m backend.tools.create_dataverse_tables 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Error "Python script failed. Exit code: $exitCode"
    if ($processOutput) { Write-Host ($processOutput -join "`n") }
    exit $exitCode
}

Write-Host "Result from create script:`n$processOutput"

