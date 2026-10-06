# Vision Design Scripts

This directory contains PowerShell scripts for setting up, configuring, and managing the Vision Design application's Dataverse environment and dependencies.

## Overview

The Vision Design project uses Microsoft Dataverse as its backend data platform. These scripts automate the setup and management of:

- System dependencies (Python, Node.js, Azure CLI, Power Platform CLI)
- Dataverse authentication and environment configuration
- Custom table creation and schema management
- Power Platform CLI tools installation and configuration

## Prerequisites

Before running these scripts, ensure you have:

1. **PowerShell 5.0+** (PowerShell 7+ recommended)
2. **Windows 10/11** (scripts are Windows-specific)
3. **Administrator privileges** (for some system-level installations)
4. **Active Azure subscription** with access to a Dataverse environment
5. **Proper permissions** in the target Dataverse environment (System Administrator or System Customizer role)

## Quick Start

1. **Initial System Setup** (run once):
   ```powershell
   # Install system dependencies (requires elevation)
   .\scripts\setup-windows.ps1 -AutoSystemInstall -DoUserSetup
   ```

2. **Configure Environment** (update .env with your settings):
   ```powershell
   # Copy .env.example to .env (done automatically by setup script)
   # Edit .env file with your Dataverse environment URL and credentials
   ```

3. **Authenticate to Dataverse**:
   ```powershell
   # Login to Azure CLI
   az login
   
   # Authenticate Power Platform CLI
   .\scripts\pac-auth.ps1
   
   # (Optional) Persist authentication details to .env
   .\scripts\persist-pac-profile.ps1
   ```

4. **Setup Dataverse Schema**:
   ```powershell
   # Create required tables, columns, and relationships
   .\scripts\setup-dataverse-visiondesign.ps1
   ```

## Script Summary

| Script | Purpose | Prerequisites | Key Actions |
|--------|---------|---------------|-------------|
| `setup-windows.ps1` | Install system dependencies | Admin privileges (optional) | Install tools, Python packages, create .env |
| `pac-auth.ps1` | Authenticate to Dataverse | Azure CLI, PAC CLI | Connect PAC to environment |
| `persist-pac-profile.ps1` | Save auth details to .env | PAC authenticated | Extract and store org info |
| `setup-dataverse-visiondesign.ps1` | Create Dataverse schema | Dataverse permissions | Create tables, relationships, choices |
| `create-dataverse-tables.ps1` | Python wrapper for table creation | Python environment | Execute backend table creation |
| `get-dataverse-tables.ps1` | List dystudio_ tables | Azure CLI auth | Query and display existing tables |
| `install-pac-tools.ps1` | Install PAC extensions | PAC CLI | Install PRT, CMT, PD tools |

## Script Reference

### System Setup Scripts

#### `setup-windows.ps1`
**Purpose**: Installs system dependencies and performs initial environment setup.

**Parameters**:
- `-AutoSystemInstall`: Attempts to install system tools via winget (requires elevation)
- `-DoUserSetup`: Performs user-level setup (Python packages, .env creation, etc.)

**What it does**:
- Installs Python 3.13+, Node.js, Git, Azure CLI, GitHub CLI, Power Platform CLI
- Installs Python dependencies from pyproject.toml
- Creates .env from .env.example
- Installs Microsoft.Graph PowerShell module
- Runs `npm install` for frontend dependencies

**Usage**:
```powershell
# Full automated setup (recommended for new environments)
.\scripts\setup-windows.ps1 -AutoSystemInstall -DoUserSetup

# System installs only
.\scripts\setup-windows.ps1 -AutoSystemInstall

# User-level setup only
.\scripts\setup-windows.ps1 -DoUserSetup
```

### Authentication Scripts

#### `pac-auth.ps1`
**Purpose**: Authenticates Power Platform CLI to your Dataverse environment.

**Requirements**:
- Power Platform CLI (pac) installed
- Azure CLI logged in
- DATAVERSE_ENVIRONMENT_URL configured in .env

**What it does**:
- Reads Dataverse URL from .env file
- Runs `pac auth create --url <environment-url>`
- Verifies authentication with `pac org who`

**Usage**:
```powershell
.\scripts\pac-auth.ps1
```

#### `persist-pac-profile.ps1`
**Purpose**: Extracts non-sensitive authentication details and saves them to .env.

**What it does**:
- Runs `pac org who` to get current authentication status
- Appends organization details to .env (org ID, environment ID, user email, etc.)
- Creates backup of .env before modification

**Usage**:
```powershell
.\scripts\persist-pac-profile.ps1
```

### Dataverse Management Scripts

#### `setup-dataverse-visiondesign.ps1`
**Purpose**: Creates and configures the complete Dataverse schema for Vision Design.

**Parameters**:
- `-OrgUrl <string>`: Override Dataverse URL (optional, reads from .env by default)
- `-Force`: Skip confirmation prompt

**What it creates**:
- **Global Choice Sets**:
  - Media Applicability (Image, Video, Both)
  - Tag Category (Style, Subject, Color, Mood, Brand, Object, Location)
  - Generation Request Type (Image, Video, Image Edit)
  - Generation Status (Pending, In Progress, Completed, Failed, Cancelled)

- **Tables**:
  - `dystudio_assettags`: Asset tagging system
  - `dystudio_visionassets`: Media assets (images/videos)
  - `dystudio_generationhistories`: AI generation tracking

- **Relationships**:
  - Many-to-many between Vision Assets and Asset Tags
  - One-to-many from Generation History to Vision Assets

**Usage**:
```powershell
# Interactive mode (recommended)
.\scripts\setup-dataverse-visiondesign.ps1

# Specify different environment
.\scripts\setup-dataverse-visiondesign.ps1 -OrgUrl "https://contoso.crm.dynamics.com/"

# Skip confirmation
.\scripts\setup-dataverse-visiondesign.ps1 -Force
```

#### `create-dataverse-tables.ps1`
**Purpose**: PowerShell wrapper for the Python table creation script.

**What it does**:
- Validates .env file exists
- Creates backup of .env
- Invokes Python module `backend.tools.create_dataverse_tables`
- Provides detailed error reporting

**Usage**:
```powershell
# Interactive mode
.\scripts\create-dataverse-tables.ps1

# Skip confirmation
.\scripts\create-dataverse-tables.ps1 -Force
```

#### `get-dataverse-tables.ps1`
**Purpose**: Lists all dystudio_ prefixed tables in the connected Dataverse environment.

**What it does**:
- Authenticates using Azure CLI token
- Queries Dataverse Web API for entity definitions
- Filters results to show only dystudio_ tables
- Displays table information in a readable format

**Usage**:
```powershell
.\scripts\get-dataverse-tables.ps1
```

### Power Platform CLI Tools

#### `install-pac-tools.ps1`
**Purpose**: Installs additional Power Platform CLI tools (PRT, CMT, PD).

**What it does**:
- Attempts to install Power Rename Tool (PRT)
- Attempts to install Configuration Migration Tool (CMT)  
- Attempts to install Package Deployer (PD)
- Provides status feedback for each installation

**Usage**:
```powershell
.\scripts\install-pac-tools.ps1
```

### Development/Diagnostic Scripts

#### `tmp-create-entity.ps1`
**Purpose**: Temporary script for testing entity creation via Dataverse Web API.

**Note**: This is a development/diagnostic script with hardcoded values. Do not use in production.

#### `tmp-get-entity.ps1`
**Purpose**: Temporary script for testing entity retrieval via Azure CLI REST commands.

**Note**: This is a development/diagnostic script with hardcoded values. Do not use in production.

## Configuration

### Environment Variables (.env)

The scripts rely on configuration stored in the `.env` file in the repository root. Key variables include:

```env
# Dataverse Configuration
DATAVERSE_ENVIRONMENT_URL=https://your-org.crm.dynamics.com/
DATAVERSE_TABLE_VISIONASSETS=dystudio_visionassets
DATAVERSE_TABLE_ASSETTAGS=dystudio_assettags
DATAVERSE_TABLE_GENERATIONHISTORY=dystudio_generationhistories
DATAVERSE_FIELD_PREFIX=dystudio

# Azure OpenAI Configuration
IMAGEGEN_AOAI_RESOURCE=your-resource-name
IMAGEGEN_DEPLOYMENT=gpt-image-1
IMAGEGEN_AOAI_API_KEY=your-api-key

# Additional provider configurations...
```

### PAC Authentication Profile

After running `persist-pac-profile.ps1`, additional authentication details are appended:

```env
# PAC auth/profile details (non-sensitive)
PAC_AUTH_USER=user@domain.com
PAC_AUTH_USER_ID=user-guid
PAC_ORG_ID=org-guid
PAC_ORG_UNIQUE_NAME=orgname
PAC_ORG_FRIENDLY_NAME=Organization Name
PAC_ORG_URL=https://your-org.crm.dynamics.com/
PAC_ENVIRONMENT_ID=environment-guid
```

## Common Workflows

### First-Time Setup (New Developer)

1. **Clone repository and navigate to scripts directory**
2. **Run full system setup**:
   ```powershell
   .\setup-windows.ps1 -AutoSystemInstall -DoUserSetup
   ```
3. **Configure .env file** with your Dataverse environment details
4. **Authenticate to Azure and Power Platform**:
   ```powershell
   az login
   .\pac-auth.ps1
   .\persist-pac-profile.ps1
   ```
5. **Create Dataverse schema**:
   ```powershell
   .\setup-dataverse-visiondesign.ps1
   ```
6. **Verify setup**:
   ```powershell
   .\get-dataverse-tables.ps1
   ```

### Environment Refresh

When switching to a new Dataverse environment:

1. **Update .env** with new DATAVERSE_ENVIRONMENT_URL
2. **Re-authenticate**:
   ```powershell
   .\pac-auth.ps1
   .\persist-pac-profile.ps1
   ```
3. **Setup schema in new environment**:
   ```powershell
   .\setup-dataverse-visiondesign.ps1
   ```

### Schema Updates

When schema changes are needed:

1. **Modify setup-dataverse-visiondesign.ps1** with required changes
2. **Run setup script** (it's designed to be idempotent):
   ```powershell
   .\setup-dataverse-visiondesign.ps1
   ```
3. **Verify changes**:
   ```powershell
   .\get-dataverse-tables.ps1
   ```

## Troubleshooting

### Common Issues

#### "pac not found" Error
**Solution**: Install Power Platform CLI:
```powershell
# Via winget
winget install Microsoft.PowerPlatformCLI

# Or download from: https://aka.ms/pacinstall
```

#### "Azure CLI not authenticated" Error
**Solution**: Login to Azure CLI:
```powershell
az login
```

#### "Access denied" Dataverse Error
**Solution**: Ensure you have proper permissions:
- System Administrator or System Customizer role in target environment
- Proper Azure AD permissions for the Dataverse resource

#### "Python dependencies not found" Error
**Solution**: Install Python dependencies:
```powershell
.\setup-windows.ps1 -DoUserSetup
```

#### ".env file not found" Error
**Solution**: Create .env file from template:
```powershell
# If .env.example exists
Copy-Item .env.example .env

# Then edit .env with your configuration
```

### Getting Help

- **Verbose output**: Most scripts provide detailed output about what they're doing
- **Error messages**: Scripts include comprehensive error handling with actionable messages
- **Backup safety**: Scripts that modify .env automatically create backups
- **Dry-run capability**: Use confirmation prompts to review actions before execution

### Script Execution Policies

If you encounter execution policy errors:

```powershell
# Temporary bypass for current session
Set-ExecutionPolicy Bypass -Scope Process

# Or run with execution policy parameter
powershell -ExecutionPolicy Bypass -File .\script-name.ps1
```

## Security Considerations

- **Credential Storage**: Never commit sensitive credentials to .env
- **Backup Files**: .env.backup files are created automatically - ensure they're in .gitignore
- **Token Handling**: Scripts use Azure CLI tokens which expire automatically
- **Permissions**: Run with least privilege necessary (admin only when required)

## Contributing

When adding new scripts:

1. **Follow naming convention**: Use kebab-case (e.g., `new-feature-script.ps1`)
2. **Include help header**: Add synopsis, description, parameters, and examples
3. **Use consistent functions**: Import common functions from existing scripts
4. **Add error handling**: Use try/catch blocks and meaningful error messages
5. **Update this README**: Document new scripts in the appropriate section

## Dependencies

### Required Tools
- PowerShell 5.0+ 
- Azure CLI
- Power Platform CLI (pac)
- Python 3.13+
- Git

### Optional Tools
- Node.js 19+ (for frontend development)
- GitHub CLI (for repository operations)
- Windows Package Manager (winget) for automated installs

### PowerShell Modules
- Microsoft.Graph (installed automatically)

### Python Packages
- All packages listed in pyproject.toml (installed automatically)

---

For more information about the Vision Design project, see the main [README.md](../README.md) in the repository root.