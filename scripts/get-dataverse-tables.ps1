<#
.SYNOPSIS
    Lists all dystudio_ prefixed tables in the connected Dataverse environment.

.DESCRIPTION
    This script connects to the Dataverse environment specified in .env and retrieves
    all entity definitions that start with the 'dystudio_' prefix. It displays table
    information including logical name, display name, schema name, and basic metadata.
    
    The script uses Azure CLI for authentication and the Dataverse Web API for data
    retrieval. It requires the user to be authenticated via 'az login' and have proper
    permissions to read entity metadata in the target Dataverse environment.

.PARAMETER OrgUrl
    Dataverse environment URL (e.g. https://contoso.crm.dynamics.com/).
    If not provided, will be read from DATAVERSE_ENVIRONMENT_URL in .env file.

.PARAMETER TablePrefix
    Table prefix to filter by. Defaults to 'dystudio_' if not specified.

.PARAMETER ShowDetails
    Include additional table details like description, ownership type, and creation info.

.PARAMETER OutputFormat
    Output format: Table (default), Json, or Csv.

.EXAMPLE
    .\scripts\get-dataverse-tables.ps1
    
    Lists all dystudio_ tables using configuration from .env file.

.EXAMPLE
    .\scripts\get-dataverse-tables.ps1 -ShowDetails
    
    Lists dystudio_ tables with additional metadata details.

.EXAMPLE
    .\scripts\get-dataverse-tables.ps1 -TablePrefix "new_" -OrgUrl "https://contoso.crm.dynamics.com/"
    
    Lists all tables with 'new_' prefix from a specific environment.

.EXAMPLE
    .\scripts\get-dataverse-tables.ps1 -OutputFormat Json
    
    Outputs table information as JSON for programmatic processing.

.NOTES
    Requires Azure CLI (az) to be installed and authenticated.
    Requires appropriate permissions in the target Dataverse environment to read entity metadata.
    Uses only built-in PowerShell modules and Azure CLI for maximum compatibility.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidatePattern('^https://.+\.crm\d*\.dynamics\.com/?$')]
    [string]$OrgUrl,

    [Parameter(Mandatory = $false)]
    [string]$TablePrefix = 'dystudio_',

    [switch]$ShowDetails,

    [Parameter(Mandatory = $false)]
    [ValidateSet('Table', 'Json', 'Csv')]
    [string]$OutputFormat = 'Table'
)

$ErrorActionPreference = 'Stop'

function Read-EnvFile {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        throw ".env file not found at $Path. Please ensure the .env file exists with DATAVERSE_ENVIRONMENT_URL configured."
    }
    
    $envVars = @{}
    $content = Get-Content $Path | Where-Object {
        ($_ -match '=') -and -not ($_ -match '^[#]') -and ($_.Trim() -ne '')
    }
    
    foreach ($line in $content) {
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $value = $parts[1].Trim()
            $envVars[$key] = $value
        }
    }
    
    return $envVars
}

function Write-Info {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Test-Prerequisites {
    Write-Info "Checking prerequisites"
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        throw "PowerShell 5.0 or higher is required. Current version: $($PSVersionTable.PSVersion)"
    }
    
    # Check Azure CLI
    if (-not (Get-Command 'az' -ErrorAction SilentlyContinue)) {
        throw "Azure CLI is not installed or not in PATH. Please install Azure CLI and run 'az login'."
    }
    
    # Check Azure CLI login
    $account = az account show --query user.name -o tsv 2>$null
    if (-not $account -or $LASTEXITCODE -ne 0) {
        throw "Not logged in to Azure CLI. Please run 'az login' first."
    }
    
    Write-Success "Prerequisites check passed (PowerShell $($PSVersionTable.PSVersion), Azure CLI authenticated as $account)"
}

function Get-DataverseHeaders {
    param([string]$ResourceUrl)

    Write-Info "Acquiring access token via Azure CLI"
    
    $token = az account get-access-token --resource $ResourceUrl --query accessToken -o tsv 2>$null
    if (-not $token -or $LASTEXITCODE -ne 0) {
        throw "Failed to acquire access token for resource '$ResourceUrl'. Ensure you have access to the Dataverse environment."
    }

    return @{
        'Authorization'     = "Bearer $token"
        'Accept'            = 'application/json'
        'Content-Type'      = 'application/json'
        'OData-MaxVersion'  = '4.0'
        'OData-Version'     = '4.0'
    }
}

function Invoke-DataverseRequest {
    param(
        [string]$Url,
        [hashtable]$Headers
    )

    try {
        $response = Invoke-RestMethod -Method GET -Uri $Url -Headers $Headers
        return $response
    }
    catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode.Value__
        }
        
        if ($statusCode -eq 404) {
            Write-Warning "Resource not found: $Url"
            return $null
        }
        
        Write-Error "Request failed: $Url"
        Write-Host $_.Exception.Message -ForegroundColor DarkRed
        throw
    }
}

function Get-DataverseTables {
    param(
        [string]$OrgUrl,
        [hashtable]$Headers,
        [string]$Prefix
    )

    Write-Info "Querying Dataverse for tables with prefix '$Prefix'"
    
    # Build the OData query to filter entities by logical name prefix
    # Select relevant fields for display
    $selectFields = 'LogicalName,SchemaName,DisplayName,DisplayCollectionName,Description,OwnershipType,IsCustomEntity,IsActivity,HasNotes,HasActivities,CreatedOn,ModifiedOn'
    $filterQuery = "startswith(LogicalName,'$Prefix')"
    $url = "$OrgUrl/api/data/v9.2/EntityDefinitions?`$select=$selectFields&`$filter=$filterQuery&`$orderby=LogicalName"
    
    $response = Invoke-DataverseRequest -Url $url -Headers $Headers
    
    if (-not $response -or -not $response.value) {
        Write-Warning "No tables found with prefix '$Prefix'"
        return @()
    }
    
    Write-Success "Found $($response.value.Count) table(s) with prefix '$Prefix'"
    return $response.value
}

function Format-TableOutput {
    param(
        [array]$Tables,
        [bool]$ShowDetails,
        [string]$Format
    )

    if ($Tables.Count -eq 0) {
        Write-Warning "No tables to display"
        return
    }

    # Prepare table data
    $tableData = @()
    foreach ($table in $Tables) {
        $displayName = if ($table.DisplayName -and $table.DisplayName.LocalizedLabels) {
            $table.DisplayName.LocalizedLabels[0].Label
        } else {
            "N/A"
        }
        
        $displayCollectionName = if ($table.DisplayCollectionName -and $table.DisplayCollectionName.LocalizedLabels) {
            $table.DisplayCollectionName.LocalizedLabels[0].Label
        } else {
            "N/A"
        }
        
        $description = if ($table.Description -and $table.Description.LocalizedLabels) {
            $table.Description.LocalizedLabels[0].Label
        } else {
            ""
        }

        $row = [PSCustomObject]@{
            LogicalName = $table.LogicalName
            SchemaName = $table.SchemaName
            DisplayName = $displayName
            DisplayCollectionName = $displayCollectionName
        }

        if ($ShowDetails) {
            $row | Add-Member -NotePropertyName Description -NotePropertyValue $description
            $row | Add-Member -NotePropertyName OwnershipType -NotePropertyValue $table.OwnershipType
            $row | Add-Member -NotePropertyName IsCustomEntity -NotePropertyValue $table.IsCustomEntity
            $row | Add-Member -NotePropertyName IsActivity -NotePropertyValue $table.IsActivity
            $row | Add-Member -NotePropertyName HasNotes -NotePropertyValue $table.HasNotes
            $row | Add-Member -NotePropertyName HasActivities -NotePropertyValue $table.HasActivities
            
            if ($table.CreatedOn) {
                $createdOn = [DateTime]::Parse($table.CreatedOn).ToString("yyyy-MM-dd HH:mm")
                $row | Add-Member -NotePropertyName CreatedOn -NotePropertyValue $createdOn
            }
            
            if ($table.ModifiedOn) {
                $modifiedOn = [DateTime]::Parse($table.ModifiedOn).ToString("yyyy-MM-dd HH:mm")
                $row | Add-Member -NotePropertyName ModifiedOn -NotePropertyValue $modifiedOn
            }
        }

        $tableData += $row
    }

    # Output based on format
    switch ($Format) {
        'Json' {
            $tableData | ConvertTo-Json -Depth 3
        }
        'Csv' {
            $tableData | ConvertTo-Csv -NoTypeInformation
        }
        'Table' {
            $tableData | Format-Table -AutoSize
        }
    }
}

# Main execution
try {
    Test-Prerequisites

    # Load configuration from .env file
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repoRoot = Split-Path -Parent $scriptDir
    $envPath = Join-Path $repoRoot '.env'

    Write-Info "Loading configuration from .env file"
    $config = Read-EnvFile -Path $envPath

    # Use OrgUrl parameter if provided, otherwise get from .env
    if (-not $OrgUrl) {
        $OrgUrl = $config.DATAVERSE_ENVIRONMENT_URL
        if (-not $OrgUrl) {
            throw "DATAVERSE_ENVIRONMENT_URL not found in .env file and -OrgUrl parameter not provided."
        }
    }

    # Clean up URL
    $OrgUrl = $OrgUrl.TrimEnd('/')
    
    Write-Info "Target Dataverse Environment: $OrgUrl"
    Write-Info "Table Prefix Filter: '$TablePrefix'"
    
    # Get authentication headers
    $headers = Get-DataverseHeaders -ResourceUrl $OrgUrl
    
    # Query for tables
    $tables = Get-DataverseTables -OrgUrl $OrgUrl -Headers $headers -Prefix $TablePrefix
    
    # Display results
    if ($tables.Count -eq 0) {
        Write-Warning "No tables found with prefix '$TablePrefix' in environment $OrgUrl"
        Write-Host ""
        Write-Host "Possible reasons:" -ForegroundColor Yellow
        Write-Host "  • Tables haven't been created yet (run setup-dataverse-visiondesign.ps1)" -ForegroundColor Gray
        Write-Host "  • Different table prefix is being used" -ForegroundColor Gray
        Write-Host "  • Insufficient permissions to read entity metadata" -ForegroundColor Gray
        Write-Host "  • Connected to wrong Dataverse environment" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "Tables in $OrgUrl with prefix '$TablePrefix':" -ForegroundColor Cyan
        Write-Host ("=" * 60) -ForegroundColor Cyan
        Format-TableOutput -Tables $tables -ShowDetails $ShowDetails -Format $OutputFormat
        
        Write-Host ""
        Write-Success "Listed $($tables.Count) table(s) successfully"
    }
}
catch {
    Write-Error "Script execution failed: $($_.Exception.Message)"
    
    # Provide helpful troubleshooting information
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  • Ensure you're logged in to Azure CLI: az login" -ForegroundColor Gray
    Write-Host "  • Verify .env contains correct DATAVERSE_ENVIRONMENT_URL" -ForegroundColor Gray
    Write-Host "  • Check that you have permissions to read entity metadata in Dataverse" -ForegroundColor Gray
    Write-Host "  • Confirm the Dataverse environment is accessible and running" -ForegroundColor Gray
    
    exit 1
}