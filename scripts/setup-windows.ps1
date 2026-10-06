<#
Setup script for Windows (PowerShell)
- Usage: powershell -ExecutionPolicy Bypass -File ./scripts/setup-windows.ps1 [-AutoSystemInstall] [-DoUserSetup]
- AutoSystemInstall will attempt to install system tools via winget (requires admin/elevation or user permission).
- DoUserSetup performs non-privileged actions: install uv, pip-install python deps, copy .env, npm install frontend (if Node present), install Microsoft.Graph PowerShell module.
#>

param(
    [switch]$AutoSystemInstall,
    [switch]$DoUserSetup
)

function Write-Info($s){ Write-Host "[INFO] $s" -ForegroundColor Cyan }
function Write-Warn($s){ Write-Host "[WARN] $s" -ForegroundColor Yellow }
function Write-Err($s){ Write-Host "[ERROR] $s" -ForegroundColor Red }

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Write-Info "Repository root: $RepoRoot"

# Helper to check command existence
function Command-Exists($cmd){
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

# Show current versions
Write-Info "Checking existing tools..."
if (Command-Exists python) { python --version } else { Write-Warn "Python not found on PATH." }
if (Command-Exists node) { node --version } else { Write-Warn "Node.js not found on PATH." }
if (Command-Exists npm) { npm --version } else { Write-Warn "npm not found on PATH." }
if (Command-Exists az) { az --version | Select-Object -First 1 } else { Write-Warn "Azure CLI (az) not found." }
if (Command-Exists pac) { pac --version } else { Write-Warn "Power Platform CLI (pac) not found." }
if (Command-Exists gh) { gh --version } else { Write-Warn "GitHub CLI (gh) not found." }

# Attempt system installs via winget if requested
if ($AutoSystemInstall) {
    if (-not (Command-Exists winget)) {
        Write-Warn "winget not found. Cannot perform automated system installs. Install winget or use manual steps in README." 
    } else {
        Write-Info "winget is available. The script will run recommended system installs. This may require elevation and user confirmation."
        $packages = @(
            @{ Id = 'Python.Python.3'; Name = 'Python 3 (latest)'; },
            @{ Id = 'OpenJS.NodeJS'; Name = 'Node.js (LTS)'; },
            @{ Id = 'Git.Git'; Name = 'Git'; },
            @{ Id = 'Microsoft.AzureCLI'; Name = 'Azure CLI'; },
            @{ Id = 'GitHub.cli'; Name = 'GitHub CLI'; },
            @{ Id = 'Microsoft.PowerPlatformCLI'; Name = 'Power Platform CLI'; }
        )
        foreach ($p in $packages) {
            Write-Info "Installing $($p.Name) via winget (id=$($p.Id))"
            winget install --id $($p.Id) -e --silent -h
        }
    }
}

if ($DoUserSetup) {
    Write-Info "Starting non-privileged (user-level) setup..."

    # Install uv (user-level via remote installer)
    try {
        Write-Info "Installing uv package manager (user-level). This runs the official installer from astral.sh"
        iex (irm 'https://astral.sh/uv/install.ps1')
        Write-Info "uv install invoked."
    } catch {
        Write-Warn "uv installer failed or blocked: $_"
    }

    # Ensure python is available
    if (-not (Command-Exists python)) {
        Write-Err "Python not found. Please install Python 3.13+ (the project requires >=3.13 per pyproject.toml)."
    } else {
        # Upgrade pip
        Write-Info "Upgrading pip (user)."
        python -m pip install --upgrade pip --user

        # Install dependencies from pyproject's project.dependencies list
        Write-Info "Installing Python dependencies listed in pyproject.toml (user-level)."
        $deps = @(
            'azure-identity>=1.21.0',
            'azure-core>=1.35.0',
            'fastapi[standard]>=0.115.12',
            'ipykernel>=6.29.5',
            'openai>=1.70.0',
            'opencv-python>=4.11.0.86',
            'pandas>=2.2.3',
            'pillow>=11.1.0',
            'pydantic-settings>=2.8.1',
            'pytest-asyncio>=0.26.0',
            'python-dotenv>=1.1.0',
            'python-multipart>=0.0.20',
            'replicate>=1.0.4',
            'tabulate>=0.9.0',
            'uvicorn>=0.34.0',
            'msal>=1.31.1',
            'requests>=2.32.0'
        )
        foreach ($d in $deps) {
            Write-Info "pip installing: $d"
            python -m pip install "$d" --user
        }
    }

    # Copy .env.example to .env if not present
    $envExample = Join-Path $RepoRoot '.env.example'
    $envFile = Join-Path $RepoRoot '.env'
    if (Test-Path $envFile) {
        Write-Info ".env already exists. Skipping copy."
    } elseif (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Info "Created .env from .env.example. Update it with your secrets."
    } else {
        Write-Warn ".env.example not found; please create .env manually."
    }

    # Install Microsoft Graph PowerShell module (user scope)
    try {
        Write-Info "Installing Microsoft.Graph PowerShell module (current user scope)."
        Install-Module -Name Microsoft.Graph -Scope CurrentUser -Force -AllowClobber -ErrorAction Stop
    } catch {
        Write-Warn "Could not install Microsoft.Graph module automatically: $_"
    }

    # Install Power Platform CLI (pac) - try to install locally for the current user
    if (Command-Exists pac) {
        Write-Info "Power Platform CLI already installed: $(pac --version 2>&1)"
    } else {
        Write-Info "Power Platform CLI (pac) not found. Attempting install..."

        if (Command-Exists winget) {
            try {
                Write-Info "Installing Power Platform CLI via winget (may require elevation)."
                $wingetArgs = @("install","--id","Microsoft.PowerPlatformCLI","-e","--silent")
                $wingetOutput = & winget @wingetArgs 2>&1
                if ($LASTEXITCODE -ne 0) {
                    Write-Warn "winget reported an error installing Power Platform CLI: $wingetOutput"
                    throw "winget install failed"
                } else {
                    Write-Info "winget install output: $wingetOutput"
                }
            } catch {
                Write-Warn "winget install failed or was interrupted: $_"
                Write-Info "Falling back to downloading the official installer (https://aka.ms/pacinstall) and launching it interactively."
                $installerUrl = 'https://aka.ms/pacinstall'
                $installerPath = Join-Path $env:TEMP 'PowerPlatformCLIInstaller.exe'
                try {
                    Write-Info "Downloading Power Platform CLI installer to $installerPath"
                    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing -ErrorAction Stop
                    Write-Info "Launching installer (you may be prompted for elevation)."
                    Start-Process -FilePath $installerPath -Wait -Verb RunAs
                } catch {
                    Write-Warn "Failed to download or run the installer: $_"
                }
            }
        } else {
            Write-Warn "winget not found. Falling back to downloading the official installer (interactive elevation may be required)."
            $installerUrl = 'https://aka.ms/pacinstall'
            $installerPath = Join-Path $env:TEMP 'PowerPlatformCLIInstaller.exe'
            try {
                Write-Info "Downloading Power Platform CLI installer to $installerPath"
                Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing -ErrorAction Stop
                Write-Info "Launching installer (you may be prompted for elevation)."
                Start-Process -FilePath $installerPath -Wait -Verb RunAs
            } catch {
                Write-Warn "Failed to download or run the installer: $_"
            }
        }

        # Verify installation and run pac's own updater to get latest runtime pieces
        if (Command-Exists pac) {
            try {
                $version = pac --version 2>&1
                Write-Info "pac installed: $version"
                Write-Info "Running 'pac install latest' to ensure latest components are present."
                pac install latest
            } catch {
                Write-Warn "pac installed but could not run 'pac install latest' successfully: $_"
            }
        } else {
            Write-Warn "Power Platform CLI still not found after attempted installation. Please install manually: https://learn.microsoft.com/power-platform/developer/cli/install"
        }
    }

    # Frontend npm install (only if node and npm exist)
    $frontendDir = Join-Path $RepoRoot 'frontend'
    if (Test-Path $frontendDir) {
        if (Command-Exists npm) {
            Push-Location $frontendDir
            try {
                Write-Info "Running 'npm install --legacy-peer-deps' in frontend directory"
                npm install --legacy-peer-deps
            } catch {
                Write-Warn "npm install failed: $_"
            } finally {
                Pop-Location
            }
        } else {
            Write-Warn "npm not found; skipping frontend dependency installation. Install Node.js (19+) and re-run this script."
        }
    } else {
        Write-Warn "frontend directory not found; skipping npm install."
    }

    Write-Info "User-level setup finished. Review output for warnings/errors."
}

Write-Info "Script completed. For system-level installs (Azure CLI, Power Platform CLI, GitHub CLI, Node.js) run with -AutoSystemInstall or follow README manual steps."