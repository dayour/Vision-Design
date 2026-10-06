<#
Install common Power Platform 'tools' used for Dataverse solution management.
Notes:
 - Running these commands will download and install external tools (PRT, CMT, PD) and may require elevation/build tools.
 - If pac does not accept the exact subcommand on your installed version, pac will print help and the script will continue.
#>

$tools = @("PRT", "CMT", "PD")
foreach ($t in $tools) {
    Write-Host "Attempting to install pac tool: $t"
    try {
        & pac tool install --name $t 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Tool $t installed or already available."
        } else {
            Write-Warning "pac tool install returned exit code $LASTEXITCODE for tool $t. It may install on first run or require manual install."
        }
    } catch {
        Write-Warning "Failed to invoke pac tool install for $t. Error: $_"
    }
}

Write-Host "Installation attempts finished. Check 'pac tool list' to confirm installed tools."