<#
 .SYNOPSIS
    Idempotent Dataverse setup for the Vision Design project.

 .DESCRIPTION
    Ensures all required global choices, tables, columns, relationships, and
    keys exist for the Vision Design application. Uses the Web API so it can
    run in any environment provided the signed-in account has maker/admin
    permissions. 
    
    The script reads configuration from the .env file in the repository root,
    including the Dataverse environment URL and table names. It works with 
    existing tables by detecting what's already present and only creating 
    missing components.
    
    The script is intentionally verbose and heavily commented so future 
    contributors can understand each step without re-reading the companion 
    runbook (dataverse_README.md).

 .PARAMETER OrgUrl
    Dataverse environment URL (e.g. https://contoso.crm.dynamics.com/).
    If not provided, will be read from DATAVERSE_ENVIRONMENT_URL in .env file.

 .PARAMETER Force
    Skip the interactive confirmation prompt.

 .EXAMPLE
    pwsh ./scripts/setup-dataverse-visiondesign.ps1
    
    Uses configuration from .env file to connect to existing environment and
    create missing tables/columns/relationships.

 .EXAMPLE
    pwsh ./scripts/setup-dataverse-visiondesign.ps1 -OrgUrl "https://dydev25.crm.dynamics.com/" -Force
    
    Overrides the environment URL from .env and skips confirmation.

 .NOTES
    Requires Azure CLI (for token acquisition) and either pre-authenticated
    Azure CLI or interactive login. Uses only built-in PowerShell modules plus
    az. Reads table names and field prefixes from .env configuration.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidatePattern('^https://.+\.crm\d*\.dynamics\.com/?$')]
    [string]$OrgUrl,

    [switch]$Force
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

function Invoke-WithRetry {
    param(
        [scriptblock]$ScriptBlock,
        [int]$MaxRetries = 3,
        [int]$DelaySeconds = 2,
        [string]$Operation = "operation"
    )
    
    $attempt = 1
    while ($attempt -le $MaxRetries) {
        try {
            return & $ScriptBlock
        }
        catch {
            if ($attempt -eq $MaxRetries) {
                Write-Host "❌ $Operation failed after $MaxRetries attempts: $($_.Exception.Message)" -ForegroundColor Red
                throw
            }
            
            $statusCode = $null
            if ($_.Exception.Response) {
                $statusCode = $_.Exception.Response.StatusCode.Value__
            }
            
            # Only retry on transient errors (429, 5xx)
            if ($statusCode -eq 429 -or ($statusCode -ge 500 -and $statusCode -le 599)) {
                Write-Host "⚠️  $Operation attempt $attempt failed (HTTP $statusCode), retrying in $DelaySeconds seconds..." -ForegroundColor Yellow
                Start-Sleep -Seconds $DelaySeconds
                $attempt++
                $DelaySeconds *= 2  # Exponential backoff
            } else {
                throw
            }
        }
    }
}

function Write-Section {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor White
}

function Confirm-Execution {
    param([string]$OrgUrl, [hashtable]$Config)
    if ($Force) { return }
    
    Write-Host "`nEnvironment Configuration:" -ForegroundColor Cyan
    Write-Host "  Dataverse URL: $OrgUrl" -ForegroundColor White
    Write-Host "  Table Names:" -ForegroundColor White
    Write-Host "    - Vision Assets: $($Config.DATAVERSE_TABLE_VISIONASSETS)" -ForegroundColor Gray
    Write-Host "    - Asset Tags: $($Config.DATAVERSE_TABLE_ASSETTAGS)" -ForegroundColor Gray
    Write-Host "    - Generation History: $($Config.DATAVERSE_TABLE_GENERATIONHISTORY)" -ForegroundColor Gray
    Write-Host "  Field Prefix: $($Config.DATAVERSE_FIELD_PREFIX)" -ForegroundColor White
    
    $answer = Read-Host "`nThis will create missing tables/columns or work with existing ones in the environment above. Continue? (y/N)"
    if ($answer.Trim().ToLowerInvariant() -ne 'y') {
        Write-Host 'Operation cancelled by user.' -ForegroundColor Yellow
        exit 0
    }
}

function Get-DataverseHeaders {
    param([string]$ResourceUrl)

    Write-Step "Acquiring access token via Azure CLI"
    
    # Check if Azure CLI is available
    if (-not (Get-Command 'az' -ErrorAction SilentlyContinue)) {
        throw "Azure CLI is not installed or not in PATH. Please install Azure CLI and run 'az login'."
    }
    
    # Check if user is logged in
    $account = az account show --query user.name -o tsv 2>$null
    if (-not $account -or $LASTEXITCODE -ne 0) {
        throw "Not logged in to Azure CLI. Please run 'az login' first."
    }
    
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
        [ValidateSet('GET', 'POST', 'PATCH', 'DELETE')]
        [string]$Method,

        [string]$Url,

        [hashtable]$Headers,

        [Parameter(ValueFromPipeline = $true)]
        [object]$Body = $null,

        [switch]$Silent,
        
        [switch]$NoRetry
    )

    $invokeParams = @{
        Method  = $Method
        Uri     = $Url
        Headers = $Headers
    }

    if ($Body) {
        if ($Body -is [string]) {
            $invokeParams['Body'] = $Body
        }
        else {
            $invokeParams['Body'] = ($Body | ConvertTo-Json -Depth 15)
        }
    }

    $operation = "$Method $($Url -replace '.*api/data/v9\.2/', '')"
    
    if ($NoRetry) {
        try {
            return Invoke-RestMethod @invokeParams
        }
        catch {
            if (-not $Silent) {
                Write-Host "❌ Request failed: $Url" -ForegroundColor Red
                Write-Host $_ -ForegroundColor DarkRed
            }
            throw
        }
    } else {
        return Invoke-WithRetry -ScriptBlock {
            Invoke-RestMethod @invokeParams
        } -Operation $operation
    }
}

function Test-EntityExists {
    param([string]$LogicalName, [string]$OrgUrl, [hashtable]$Headers)
    $uri = "$OrgUrl/api/data/v9.2/EntityDefinitions(LogicalName='$LogicalName')?`$select=MetadataId"
    try {
        $result = Invoke-DataverseRequest -Method GET -Url $uri -Headers $Headers -Silent -NoRetry
        return $null -ne $result
    }
    catch {
        if ($_.Exception.Response.StatusCode.Value__ -eq 404) {
            return $false
        }
        throw
    }
}

function Test-GlobalOptionSetExists {
    param([string]$Name)
    $uri = "$global:ApiBase/GlobalOptionSetDefinitions(Name='$Name')?`$select=MetadataId"
    try {
        $result = Invoke-DataverseRequest -Method GET -Url $uri -Headers $global:Headers -Silent -NoRetry
        return $null -ne $result
    }
    catch {
        if ($_.Exception.Response.StatusCode.Value__ -eq 404) {
            return $false
        }
        throw
    }
}

function Test-RelationshipExists {
    param([string]$SchemaName)
    $uri = "$global:ApiBase/RelationshipDefinitions(SchemaName='$SchemaName')?`$select=MetadataId"
    try {
        $result = Invoke-DataverseRequest -Method GET -Url $uri -Headers $global:Headers -Silent -NoRetry
        return $null -ne $result
    }
    catch {
        if ($_.Exception.Response.StatusCode.Value__ -eq 404) {
            return $false
        }
        throw
    }
}

function Test-AlternateKeyExists {
    param([string]$EntityLogicalName, [string]$SchemaName)
    $uri = "$global:ApiBase/EntityDefinitions(LogicalName='$EntityLogicalName')/Keys"
    try {
        $keys = Invoke-DataverseRequest -Method GET -Url $uri -Headers $global:Headers -Silent -NoRetry
        return ($keys.value | Where-Object { $_.SchemaName -eq $SchemaName }) -ne $null
    }
    catch {
        if ($_.Exception.Response.StatusCode.Value__ -eq 404) {
            return $false
        }
        throw
    }
}

function Ensure-GlobalOptionSet {
    param(
        [string]$Name,
        [string]$DisplayName,
        [array]$Options
    )

    Write-Step "Ensuring global choice '$Name'"
    
    if (Test-GlobalOptionSetExists -Name $Name) {
        Write-Host "   ✅ Exists" -ForegroundColor Green
        return
    }

    $body = @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.OptionSetMetadata'
        Name           = $Name
        DisplayName    = @{
            '@odata.type'     = 'Microsoft.Dynamics.CRM.Label'
            LocalizedLabels   = @(@{
                '@odata.type' = 'Microsoft.Dynamics.CRM.LocalizedLabel'
                Label         = $DisplayName
                LanguageCode  = 1033
            })
        }
        Description    = @{
            '@odata.type'     = 'Microsoft.Dynamics.CRM.Label'
            LocalizedLabels   = @(@{
                '@odata.type' = 'Microsoft.Dynamics.CRM.LocalizedLabel'
                Label         = "Choice for $DisplayName"
                LanguageCode  = 1033
            })
        }
        OptionSetType  = 'Picklist'
        IsGlobal       = $true
        IsCustomOptionSet = $true
        Options        = @()
    }

    foreach ($option in $Options) {
        $body.Options += @{
            Value = $option.Value
            Label = @{
                '@odata.type'   = 'Microsoft.Dynamics.CRM.Label'
                LocalizedLabels = @(@{
                    '@odata.type' = 'Microsoft.Dynamics.CRM.LocalizedLabel'
                    Label         = $option.Label
                    LanguageCode  = 1033
                })
            }
        }
    }

        try {
            $response = Invoke-DataverseRequest -Method POST -Url "$global:ApiBase/GlobalOptionSetDefinitions" -Headers $global:Headers -Body $body
            Write-Host "   ✅ Created" -ForegroundColor Green
            return $response.MetadataId
        }
        catch {
            $message = $_.Exception.Message
            if (-not $message) {
                $message = $_.ToString()
            }

            $responseContent = $null
            if ($_.ErrorDetails -and $null -ne $_.ErrorDetails.Message -and $_.ErrorDetails.Message.Trim()) {
                $responseContent = $_.ErrorDetails.Message
            }
            elseif ($_.Exception -and $_.Exception.Response -and $_.Exception.Response.Content) {
                try {
                    $responseContent = $_.Exception.Response.Content.ReadAsStringAsync().Result
                }
                catch {}
            }

            if ($responseContent) {
                Write-Host "   ⚠ Duplicate detection response: $responseContent" -ForegroundColor Yellow
                try {
                    $json = $responseContent | ConvertFrom-Json
                    if ($json.error.message) {
                        $message = $json.error.message
                    }
                }
                catch {}
            }

            if (-not $message) {
                $message = $_.ToString()
            }

            Write-Host "   ⚠ Duplicate detection message: $message" -ForegroundColor Yellow
            if ($message -match 'not unique') {
                Write-Host '   ⚠ Already exists (detected during creation)' -ForegroundColor Yellow
                return $null
            }
            throw
        }
}

function Ensure-Entity {
    param(
        [string]$LogicalName,
        [string]$SchemaName,
        [string]$DisplayName,
        [string]$PluralName,
        [string]$PrimaryName,
        [string]$PrimaryNameDisplay,
        [string]$PrimaryNameDescription
    )

    if (Test-EntityExists -LogicalName $LogicalName -OrgUrl $OrgUrl -Headers $global:Headers) {
        Write-Host "✅ Table $LogicalName already exists" -ForegroundColor Green
        return
    }

    Write-Step "Creating table $LogicalName"

    $primaryAttribute = @{
        '@odata.type'  = 'Microsoft.Dynamics.CRM.StringAttributeMetadata'
        SchemaName     = $PrimaryName
        DisplayName    = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$PrimaryNameDisplay; LanguageCode=1033})}
        Description    = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$PrimaryNameDescription; LanguageCode=1033})}
        RequiredLevel  = @{ Value = 'ApplicationRequired' }
        MaxLength      = 200
    }

    $entityMetadata = @{
        '@odata.type'         = 'Microsoft.Dynamics.CRM.EntityMetadata'
        SchemaName            = $SchemaName
        DisplayName           = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayName; LanguageCode=1033})}
        DisplayCollectionName = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$PluralName; LanguageCode=1033})}
        Description           = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label="Table for $PluralName"; LanguageCode=1033})}
        OwnershipType         = 'UserOwned'
        IsActivity            = $false
        HasNotes              = $true
        HasActivities         = $false
        PrimaryNameAttribute  = $PrimaryName
    }

    $createRequest = @{
        '@odata.type'      = 'Microsoft.Dynamics.CRM.CreateEntityRequest'
        Entity             = $entityMetadata
        PrimaryAttribute   = $primaryAttribute
        HasNotes           = $true
        HasActivities      = $false
    }

    Invoke-DataverseRequest -Method POST -Url "$global:ApiBase/Execute" -Headers $global:Headers -Body $createRequest | Out-Null
    Write-Host "   ✅ Created" -ForegroundColor Green
}

function Test-AttributeExists {
    param([string]$EntityLogicalName, [string]$SchemaName)
    $uri = "$global:ApiBase/EntityDefinitions(LogicalName='$EntityLogicalName')/Attributes(LogicalName='$SchemaName')?`$select=MetadataId"
    try {
        Invoke-DataverseRequest -Method GET -Url $uri -Headers $global:Headers -Silent -NoRetry | Out-Null
        return $true
    }
    catch {
        if ($_.Exception.Response.StatusCode.Value__ -eq 404) { return $false }
        throw
    }
}

function Ensure-Attribute {
    param(
        [string]$EntityLogicalName,
        [hashtable]$Definition
    )

    if (Test-AttributeExists -EntityLogicalName $EntityLogicalName -SchemaName $Definition.SchemaName) {
        Write-Host "   ✅ Column $($Definition.SchemaName) exists" -ForegroundColor Green
        return
    }

    Write-Host "   ➕ Creating column $($Definition.SchemaName)" -ForegroundColor Yellow
    Invoke-DataverseRequest -Method POST -Url "$global:ApiBase/EntityDefinitions(LogicalName='$EntityLogicalName')/Attributes" -Headers $global:Headers -Body $Definition | Out-Null
    Write-Host "      ✅ Created" -ForegroundColor Green
}

function New-StringAttribute {
    param([string]$SchemaName, [string]$DisplayName, [string]$Description, [int]$MaxLength = 4000, [string]$Required = 'None', [string]$Format = 'Text')
    return @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.StringAttributeMetadata'
        SchemaName    = $SchemaName
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayName; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$Description; LanguageCode=1033})}
        RequiredLevel = @{ Value = $Required }
        MaxLength     = $MaxLength
        FormatName    = @{ Value = $Format }
    }
}

function New-MemoAttribute {
    param([string]$SchemaName, [string]$DisplayName, [string]$Description, [int]$MaxLength = 4000)
    return @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.MemoAttributeMetadata'
        SchemaName    = $SchemaName
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayName; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$Description; LanguageCode=1033})}
        RequiredLevel = @{ Value = 'None' }
        MaxLength     = $MaxLength
        Format        = @{ Value = 'TextArea' }
    }
}

function New-IntegerAttribute {
    param([string]$SchemaName, [string]$DisplayName, [string]$Description, [int]$Min = 0, [int]$Max = 2147483647)
    return @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.IntegerAttributeMetadata'
        SchemaName    = $SchemaName
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayName; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$Description; LanguageCode=1033})}
        Format        = 'None'
        MinValue      = $Min
        MaxValue      = $Max
        RequiredLevel = @{ Value = 'None' }
    }
}

function New-DecimalAttribute {
    param([string]$SchemaName, [string]$DisplayName, [string]$Description, [double]$Min = -100000000000.0, [double]$Max = 100000000000.0, [int]$Precision = 2)
    return @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.DecimalAttributeMetadata'
        SchemaName    = $SchemaName
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayName; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$Description; LanguageCode=1033})}
        MinValue      = $Min
        MaxValue      = $Max
        Precision     = $Precision
        RequiredLevel = @{ Value = 'None' }
    }
}

function New-BooleanAttribute {
    param([string]$SchemaName, [string]$DisplayName, [string]$Description)
    return @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.BooleanAttributeMetadata'
        SchemaName    = $SchemaName
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayName; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$Description; LanguageCode=1033})}
        RequiredLevel = @{ Value = 'None' }
        DefaultValue  = $false
        OptionSet     = @{
            '@odata.type' = 'Microsoft.Dynamics.CRM.BooleanOptionSetMetadata'
            TrueOption    = @{
                '@odata.type' = 'Microsoft.Dynamics.CRM.OptionMetadata'
                Value         = 1
                Label         = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Yes'; LanguageCode=1033})}
            }
            FalseOption   = @{
                '@odata.type' = 'Microsoft.Dynamics.CRM.OptionMetadata'
                Value         = 0
                Label         = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='No'; LanguageCode=1033})}
            }
        }
    }
}

function New-OptionSetAttribute {
    param([string]$SchemaName, [string]$DisplayName, [string]$Description, [string]$GlobalOptionSetName, [string]$Required = 'None')
    return @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.PicklistAttributeMetadata'
        SchemaName    = $SchemaName
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayName; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$Description; LanguageCode=1033})}
        RequiredLevel = @{ Value = $Required }
        OptionSet     = @{
            '@odata.type'     = 'Microsoft.Dynamics.CRM.OptionSetMetadata'
            IsGlobal          = $true
            Name              = $GlobalOptionSetName
        }
    }
}

function Ensure-AlternateKey {
    param([string]$EntityLogicalName, [string]$SchemaName, [string[]]$Columns, [string]$DisplayName)

    if (Test-AlternateKeyExists -EntityLogicalName $EntityLogicalName -SchemaName $SchemaName) {
        Write-Host "✅ Alternate key $SchemaName exists" -ForegroundColor Green
        return
    }

    Write-Host "   ➕ Creating alternate key $SchemaName" -ForegroundColor Yellow
    $uri = "$global:ApiBase/EntityDefinitions(LogicalName='$EntityLogicalName')/Keys"
    $body = @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.EntityKeyMetadata'
        SchemaName    = $SchemaName
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayName; LanguageCode=1033})}
        KeyAttributes = $Columns
    }

    Invoke-DataverseRequest -Method POST -Url $uri -Headers $global:Headers -Body $body | Out-Null
    Write-Host "      ✅ Created" -ForegroundColor Green
}

function Ensure-ManyToManyRelationship {
    param(
        [string]$SchemaName,
        [string]$Entity1,
        [string]$Entity2,
        [string]$Entity1Label,
        [string]$Entity2Label,
        [string]$IntersectEntityName
    )

    if (Test-RelationshipExists -SchemaName $SchemaName) {
        Write-Host "✅ Relationship $SchemaName exists" -ForegroundColor Green
        return
    }

    Write-Host "   ➕ Creating M:N relationship $SchemaName" -ForegroundColor Yellow
    if (-not $IntersectEntityName) {
        $IntersectEntityName = "${Entity1}_${Entity2}".ToLowerInvariant()
    }

    $body = @{
        '@odata.type'                  = 'Microsoft.Dynamics.CRM.ManyToManyRelationshipMetadata'
        SchemaName                     = $SchemaName
        IntersectEntityName            = $IntersectEntityName
        Entity1LogicalName             = $Entity1
        Entity1NavigationPropertyName  = "${Entity1}_$Entity2".ToLowerInvariant()
        Entity2LogicalName             = $Entity2
        Entity2NavigationPropertyName  = "${Entity2}_$Entity1".ToLowerInvariant()
        Entity1AssociatedMenuConfiguration = @{
            Behavior = 'UseCollectionName'
            Group    = 'Details'
            Label    = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$Entity2Label; LanguageCode=1033})}
            Order    = 10
        }
        Entity2AssociatedMenuConfiguration = @{
            Behavior = 'UseCollectionName'
            Group    = 'Details'
            Label    = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$Entity1Label; LanguageCode=1033})}
            Order    = 10
        }
        CascadeConfiguration = @{
            Assign    = 'NoCascade'
            Delete    = 'NoCascade'
            Share     = 'NoCascade'
            Unshare   = 'NoCascade'
            RollupView= 'NoCascade'
        }
    }

    Invoke-DataverseRequest -Method POST -Url "$global:ApiBase/RelationshipDefinitions" -Headers $global:Headers -Body $body | Out-Null
    Write-Host "      ✅ Created" -ForegroundColor Green
}

function Ensure-OneToManyRelationship {
    param(
        [string]$SchemaName,
        [string]$ReferencedEntity,
        [string]$ReferencingEntity,
        [string]$LookupSchema,
        [string]$DisplayLabel
    )

    if (Test-RelationshipExists -SchemaName $SchemaName) {
        Write-Host "✅ Relationship $SchemaName exists" -ForegroundColor Green
        return
    }

    Write-Host "   ➕ Creating 1:N relationship $SchemaName" -ForegroundColor Yellow
    $body = @{
        '@odata.type'       = 'Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata'
        SchemaName          = $SchemaName
        ReferencedEntity    = $ReferencedEntity
        ReferencedAttribute = "${ReferencedEntity}id"
        ReferencingEntity   = $ReferencingEntity
        Lookup              = @{
            SchemaName   = $LookupSchema
            DisplayName  = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label=$DisplayLabel; LanguageCode=1033})}
            RequiredLevel= @{ Value = 'None' }
        }
        CascadeConfiguration = @{
            Assign  = 'Cascade'
            Delete  = 'RemoveLink'
            Share   = 'Cascade'
            Unshare = 'Cascade'
            Reparent= 'Cascade'
        }
    }

    Invoke-DataverseRequest -Method POST -Url "$global:ApiBase/RelationshipDefinitions" -Headers $global:Headers -Body $body | Out-Null
    Write-Host "      ✅ Created" -ForegroundColor Green
}

function Test-Prerequisites {
    Write-Step "Checking prerequisites"
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        throw "PowerShell 5.0 or higher is required. Current version: $($PSVersionTable.PSVersion)"
    }
    
    # Check Azure CLI
    if (-not (Get-Command 'az' -ErrorAction SilentlyContinue)) {
        throw "Azure CLI is not installed or not in PATH. Please install Azure CLI."
    }
    
    # Check Azure CLI login
    $account = az account show --query user.name -o tsv 2>$null
    if (-not $account -or $LASTEXITCODE -ne 0) {
        throw "Not logged in to Azure CLI. Please run 'az login' first."
    }
    
    Write-Host "   ✅ Prerequisites check passed" -ForegroundColor Green
}

Test-Prerequisites

# Load configuration from .env file
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$envPath = Join-Path $repoRoot '.env'

Write-Step "Loading configuration from .env file"
$config = Read-EnvFile -Path $envPath

# Use OrgUrl parameter if provided, otherwise get from .env
if (-not $OrgUrl) {
    $OrgUrl = $config.DATAVERSE_ENVIRONMENT_URL
    if (-not $OrgUrl) {
        throw "DATAVERSE_ENVIRONMENT_URL not found in .env file and -OrgUrl parameter not provided."
    }
}

# Get table names from .env (with fallback to defaults)
$visionAssetsTable = if ($config.DATAVERSE_TABLE_VISIONASSETS) { $config.DATAVERSE_TABLE_VISIONASSETS } else { 'dystudio_visionassets' }
$assetTagsTable = if ($config.DATAVERSE_TABLE_ASSETTAGS) { $config.DATAVERSE_TABLE_ASSETTAGS } else { 'dystudio_assettags' }
$generationHistoryTable = if ($config.DATAVERSE_TABLE_GENERATIONHISTORY) { $config.DATAVERSE_TABLE_GENERATIONHISTORY } else { 'dystudio_generationhistories' }
$fieldPrefix = if ($config.DATAVERSE_FIELD_PREFIX) { $config.DATAVERSE_FIELD_PREFIX } else { 'dystudio' }

Write-Host "   ✅ Configuration loaded" -ForegroundColor Green

Confirm-Execution -OrgUrl $OrgUrl -Config $config

$OrgUrl = $OrgUrl.TrimEnd('/')
$global:ApiBase = "$OrgUrl/api/data/v9.2"
$global:Headers = Get-DataverseHeaders -ResourceUrl $OrgUrl

Write-Section 'Global Choices'
$mediaApplicabilityId = Ensure-GlobalOptionSet -Name "${fieldPrefix}_MediaApplicability" -DisplayName 'Media Applicability' -Options @(
    @{ Label = 'Image'; Value = 100000000 },
    @{ Label = 'Video'; Value = 100000001 },
    @{ Label = 'Both'; Value = 100000002 }
)

$tagCategoryId = Ensure-GlobalOptionSet -Name "${fieldPrefix}_TagCategory" -DisplayName 'Tag Category' -Options @(
    @{ Label = 'Style'; Value = 100000000 },
    @{ Label = 'Subject'; Value = 100000001 },
    @{ Label = 'Color'; Value = 100000002 },
    @{ Label = 'Mood'; Value = 100000003 },
    @{ Label = 'Brand'; Value = 100000004 },
    @{ Label = 'Object'; Value = 100000005 },
    @{ Label = 'Location'; Value = 100000006 }
)

$requestTypeId = Ensure-GlobalOptionSet -Name "${fieldPrefix}_RequestType" -DisplayName 'Generation Request Type' -Options @(
    @{ Label = 'Image'; Value = 100000000 },
    @{ Label = 'Video'; Value = 100000001 },
    @{ Label = 'Image Edit'; Value = 100000002 }
)

$statusChoiceId = Ensure-GlobalOptionSet -Name "${fieldPrefix}_GenerationStatus" -DisplayName 'Generation Status' -Options @(
    @{ Label = 'Pending'; Value = 100000000 },
    @{ Label = 'In Progress'; Value = 100000001 },
    @{ Label = 'Completed'; Value = 100000002 },
    @{ Label = 'Failed'; Value = 100000003 },
    @{ Label = 'Cancelled'; Value = 100000004 }
)

Write-Section "Table: $assetTagsTable"
Ensure-Entity -LogicalName $assetTagsTable -SchemaName "${fieldPrefix}_AssetTag" -DisplayName 'Asset Tag' -PluralName 'Asset Tags' -PrimaryName "${fieldPrefix}_name" -PrimaryNameDisplay 'Name' -PrimaryNameDescription 'Display name for the asset tag'

$assetTagAttributes = @(
    (New-StringAttribute -SchemaName "${fieldPrefix}_tag_name" -DisplayName 'Tag Name' -Description 'Alternate tag name' -MaxLength 200),
    (New-OptionSetAttribute -SchemaName "${fieldPrefix}_category" -DisplayName 'Category' -Description 'Categorisation of the tag' -GlobalOptionSetName "${fieldPrefix}_TagCategory"),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_description" -DisplayName 'Description' -Description 'Description of the tag' -MaxLength 2000),
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_usage_count" -DisplayName 'Usage Count' -Description 'Number of times the tag has been used'),
    @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.DateTimeAttributeMetadata'
        SchemaName    = "${fieldPrefix}_last_used"
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Last Used'; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Last time the tag was used'; LanguageCode=1033})}
        DateTimeBehavior = 'UserLocal'
        RequiredLevel = @{ Value = 'None' }
    },
    (New-OptionSetAttribute -SchemaName "${fieldPrefix}_media_applicability" -DisplayName 'Media Applicability' -Description 'Applicable media types' -GlobalOptionSetName "${fieldPrefix}_MediaApplicability")
)

foreach ($attribute in $assetTagAttributes) {
    Ensure-Attribute -EntityLogicalName $assetTagsTable -Definition $attribute
}

Ensure-AlternateKey -EntityLogicalName $assetTagsTable -SchemaName "${fieldPrefix}_AssetTag_Name_UniqueKey" -Columns @("${fieldPrefix}_name") -DisplayName 'Asset Tag Name Unique Key'

Write-Section "Table: $visionAssetsTable"
Ensure-Entity -LogicalName $visionAssetsTable -SchemaName "${fieldPrefix}_VisionAsset" -DisplayName 'Vision Asset' -PluralName 'Vision Assets' -PrimaryName "${fieldPrefix}_name" -PrimaryNameDisplay 'Name' -PrimaryNameDescription 'Display name for the asset'

$mediaTypeAttribute = @{
    '@odata.type' = 'Microsoft.Dynamics.CRM.PicklistAttributeMetadata'
    AttributeType = 'Picklist'
    SchemaName    = "${fieldPrefix}_media_type"
    DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Media Type'; LanguageCode=1033})}
    Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Media type of the asset'; LanguageCode=1033})}
    RequiredLevel = @{ Value = 'ApplicationRequired' }
    OptionSet     = @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.OptionSetMetadata'
        IsGlobal      = $false
        Options       = @(
            @{
                Value = 100000000
                Label = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Image'; LanguageCode=1033})}
            },
            @{
                Value = 100000001
                Label = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Video'; LanguageCode=1033})}
            }
        )
    }
}

$visionAssetAttributes = @(
    $mediaTypeAttribute,
    (New-StringAttribute -SchemaName "${fieldPrefix}_blob_name" -DisplayName 'Blob Name' -Description 'Blob identifier' -MaxLength 500),
    (New-StringAttribute -SchemaName "${fieldPrefix}_container" -DisplayName 'Container' -Description 'Storage container name' -MaxLength 200),
    (New-StringAttribute -SchemaName "${fieldPrefix}_url" -DisplayName 'Asset URL' -Description 'Public URL to the asset' -MaxLength 500 -Format 'Url'),
    (New-StringAttribute -SchemaName "${fieldPrefix}_filename" -DisplayName 'Filename' -Description 'Original filename' -MaxLength 260),
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_size" -DisplayName 'File Size' -Description 'File size in bytes'),
    (New-StringAttribute -SchemaName "${fieldPrefix}_content_type" -DisplayName 'Content Type' -Description 'Mime type' -MaxLength 200),
    (New-StringAttribute -SchemaName "${fieldPrefix}_folder_path" -DisplayName 'Folder Path' -Description 'Folder or virtual path' -MaxLength 500),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_prompt" -DisplayName 'Prompt' -Description 'Generation prompt' -MaxLength 4000),
    (New-StringAttribute -SchemaName "${fieldPrefix}_model" -DisplayName 'Model' -Description 'AI model used' -MaxLength 200),
    (New-StringAttribute -SchemaName "${fieldPrefix}_generation_id" -DisplayName 'Generation Id' -Description 'External generation id' -MaxLength 200),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_summary" -DisplayName 'Summary' -Description 'Generated summary' -MaxLength 4000),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_description" -DisplayName 'Description' -Description 'Generated description' -MaxLength 4000),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_products" -DisplayName 'Products' -Description 'Detected products' -MaxLength 4000),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_tags" -DisplayName 'Tags Json' -Description 'Tag metadata as JSON' -MaxLength 4000),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_feedback" -DisplayName 'Feedback' -Description 'Feedback from reviewers' -MaxLength 4000),
    (New-StringAttribute -SchemaName "${fieldPrefix}_quality" -DisplayName 'Quality' -Description 'Quality setting' -MaxLength 100),
    (New-StringAttribute -SchemaName "${fieldPrefix}_background" -DisplayName 'Background' -Description 'Background configuration' -MaxLength 200),
    (New-StringAttribute -SchemaName "${fieldPrefix}_output_format" -DisplayName 'Output Format' -Description 'Format of the generated asset' -MaxLength 50),
    (New-BooleanAttribute -SchemaName "${fieldPrefix}_has_transparency" -DisplayName 'Has Transparency' -Description 'Indicates if transparency is present'),
    (New-DecimalAttribute -SchemaName "${fieldPrefix}_duration" -DisplayName 'Duration (s)' -Description 'Duration for video assets' -Min 0 -Max 36000 -Precision 3),
    (New-DecimalAttribute -SchemaName "${fieldPrefix}_fps" -DisplayName 'Frames Per Second' -Description 'Frames per second' -Min 0 -Max 240 -Precision 3),
    (New-StringAttribute -SchemaName "${fieldPrefix}_resolution" -DisplayName 'Resolution' -Description 'Resolution descriptor' -MaxLength 50),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_analysis_data" -DisplayName 'Analysis Data' -Description 'Full analysis payload' -MaxLength 1048576),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_custom_metadata" -DisplayName 'Custom Metadata' -Description 'Custom metadata blob' -MaxLength 1048576),
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_width" -DisplayName 'Width' -Description 'Pixel width'),
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_height" -DisplayName 'Height' -Description 'Pixel height'),
    (New-BooleanAttribute -SchemaName "${fieldPrefix}_has_analysis" -DisplayName 'Has Analysis' -Description 'Indicates if analysis is available'),
    @{
        '@odata.type'     = 'Microsoft.Dynamics.CRM.FileAttributeMetadata'
        SchemaName        = "${fieldPrefix}_image_file"
        LogicalName       = "${fieldPrefix}_image_file"
        DisplayName       = @{
            '@odata.type' = 'Microsoft.Dynamics.CRM.Label'
            LocalizedLabels = @(
                @{ '@odata.type' = 'Microsoft.Dynamics.CRM.LocalizedLabel'; Label = 'Image File'; LanguageCode = 1033 }
            )
        }
        Description       = @{
            '@odata.type' = 'Microsoft.Dynamics.CRM.Label'
            LocalizedLabels = @(
                @{ '@odata.type' = 'Microsoft.Dynamics.CRM.LocalizedLabel'; Label = 'Binary image file storage'; LanguageCode = 1033 }
            )
        }
        RequiredLevel     = @{ Value = 'None' }
        MaxSizeInKB       = 131072
    }
)

foreach ($attribute in $visionAssetAttributes) {
    Ensure-Attribute -EntityLogicalName $visionAssetsTable -Definition $attribute
}

Write-Section "Table: $generationHistoryTable"
Ensure-Entity -LogicalName $generationHistoryTable -SchemaName "${fieldPrefix}_GenerationHistory" -DisplayName 'Generation History' -PluralName 'Generation Histories' -PrimaryName "${fieldPrefix}_name" -PrimaryNameDisplay 'Name' -PrimaryNameDescription 'Display name for generation record'

$generationAttributes = @(
    (New-StringAttribute -SchemaName "${fieldPrefix}_generation_id" -DisplayName 'Generation ID' -Description 'External generation identifier' -MaxLength 200 -Required 'ApplicationRequired'),
    (New-OptionSetAttribute -SchemaName "${fieldPrefix}_request_type" -DisplayName 'Request Type' -Description 'Type of generation request' -GlobalOptionSetName "${fieldPrefix}_RequestType" -Required 'ApplicationRequired'),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_prompt" -DisplayName 'Prompt' -Description 'Original prompt' -MaxLength 4000),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_enhanced_prompt" -DisplayName 'Enhanced Prompt' -Description 'Enhanced prompt' -MaxLength 4000),
    (New-StringAttribute -SchemaName "${fieldPrefix}_model" -DisplayName 'Model' -Description 'Model used' -MaxLength 200),
    (New-MemoAttribute -SchemaName "${fieldPrefix}_parameters_json" -DisplayName 'Parameters Json' -Description 'Serialized parameter payload' -MaxLength 1048576),
    (New-OptionSetAttribute -SchemaName "${fieldPrefix}_status" -DisplayName 'Status' -Description 'Job status' -GlobalOptionSetName "${fieldPrefix}_GenerationStatus" -Required 'ApplicationRequired'),
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_result_count" -DisplayName 'Result Count' -Description 'Number of results' -Min 0),
    @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.DateTimeAttributeMetadata'
        SchemaName    = "${fieldPrefix}_started_at"
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Started At'; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Generation start time'; LanguageCode=1033})}
        DateTimeBehavior = 'UserLocal'
        RequiredLevel = @{ Value = 'ApplicationRequired' }
    },
    @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.DateTimeAttributeMetadata'
        SchemaName    = "${fieldPrefix}_completed_at"
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Completed At'; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Generation completion time'; LanguageCode=1033})}
        DateTimeBehavior = 'UserLocal'
        RequiredLevel = @{ Value = 'None' }
    },
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_duration_ms" -DisplayName 'Duration (ms)' -Description 'Duration in milliseconds' -Min 0),
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_tokens_used" -DisplayName 'Tokens Used' -Description 'Total tokens consumed' -Min 0),
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_input_tokens" -DisplayName 'Input Tokens' -Description 'Input tokens' -Min 0),
    (New-IntegerAttribute -SchemaName "${fieldPrefix}_output_tokens" -DisplayName 'Output Tokens' -Description 'Output tokens' -Min 0),
    @{
        '@odata.type' = 'Microsoft.Dynamics.CRM.MoneyAttributeMetadata'
        SchemaName    = "${fieldPrefix}_estimated_cost"
        DisplayName   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Estimated Cost'; LanguageCode=1033})}
        Description   = @{'@odata.type'='Microsoft.Dynamics.CRM.Label'; LocalizedLabels=@(@{'@odata.type'='Microsoft.Dynamics.CRM.LocalizedLabel'; Label='Estimated cost in USD'; LanguageCode=1033})}
        Precision     = 4
        MinValue      = 0
        MaxValue      = 1000000
        RequiredLevel = @{ Value = 'None' }
    },
    (New-MemoAttribute -SchemaName "${fieldPrefix}_error_message" -DisplayName 'Error Message' -Description 'Error message in case of failure' -MaxLength 4000)
)

foreach ($attribute in $generationAttributes) {
    Ensure-Attribute -EntityLogicalName $generationHistoryTable -Definition $attribute
}

Ensure-AlternateKey -EntityLogicalName $generationHistoryTable -SchemaName "${fieldPrefix}_GenerationHistory_GenerationId_Key" -Columns @("${fieldPrefix}_generation_id") -DisplayName 'Generation ID Unique Key'

Write-Section 'Relationships'
Ensure-ManyToManyRelationship -SchemaName "${fieldPrefix}_visionasset_assettags" -Entity1 $visionAssetsTable -Entity2 $assetTagsTable -Entity1Label 'Asset Tags' -Entity2Label 'Vision Assets' -IntersectEntityName "${fieldPrefix}_${visionAssetsTable}_${assetTagsTable}"
Ensure-OneToManyRelationship -SchemaName "${fieldPrefix}_generationhistory_visionassets" -ReferencedEntity $generationHistoryTable -ReferencingEntity $visionAssetsTable -LookupSchema "${fieldPrefix}_generationhistoryid" -DisplayLabel 'Generation History'

Write-Section 'Summary'
Write-Host '✅ Dataverse schema ensured successfully.' -ForegroundColor Green