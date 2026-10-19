<#
.SYNOPSIS
    Cloud File Storage System - Windows PowerShell Setup Script
.DESCRIPTION
    Creates a project-isolated Python virtual environment, installs dependencies,
    provisions local development configuration from .env.example, and initializes the metadata database schema.
    Complies strictly with local security constraints (does not alter global execution policies or system files).
#>

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  Cloud File Storage System - Setup & Initialization (Phase 1)    " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Locate project root directory
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
Write-Host "[+] Project Root: $ProjectRoot" -ForegroundColor Gray

# 2. Verify Python Installation
Write-Host "`n[1/5] Checking Python installation..." -ForegroundColor Yellow
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Error "Python was not found on PATH. Please ensure Python 3.11+ is installed and available on PATH."
    exit 1
}

$PythonVersion = & python --version 2>&1
Write-Host "      Detected: $PythonVersion" -ForegroundColor Green

# 3. Create or reuse virtual environment
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "`n[2/5] Configuring virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path $VenvPython)) {
    Write-Host "      Creating clean virtual environment at .venv..." -ForegroundColor Gray
    & python -m venv "$VenvDir"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment."
        exit 1
    }
    Write-Host "      Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "      Existing virtual environment detected at .venv." -ForegroundColor Green
}

# 4. Upgrade pip and install project requirements
Write-Host "`n[3/5] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& "$VenvPython" -m pip install --upgrade pip --quiet
& "$VenvPython" -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install required Python packages."
    exit 1
}
Write-Host "      Dependencies installed successfully." -ForegroundColor Green

# 5. Provision local .env if absent
Write-Host "`n[4/5] Checking environment configuration (.env)..." -ForegroundColor Yellow
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item -Path $EnvExample -Destination $EnvFile
        Write-Host "      Copied .env.example to .env (development placeholders ready)." -ForegroundColor Green
    } else {
        Write-Warning "      .env.example was not found. Please create .env manually."
    }
} else {
    Write-Host "      Existing .env file detected." -ForegroundColor Green
}

# 6. Initialize SQLite Metadata Database
Write-Host "`n[5/5] Initializing metadata database schema..." -ForegroundColor Yellow
$DataDir = Join-Path $ProjectRoot "data"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

& "$VenvPython" -c "import sys; sys.path.insert(0, '.'); from src.database import init_db; init_db(); print('      Database tables and indexes initialized successfully.')"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Database schema initialization failed. You can run init_db() manually later."
}

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!                                                " -ForegroundColor Green
Write-Host "  To launch the dashboard, execute: .\scripts\run.ps1             " -ForegroundColor Cyan
Write-Host "  To run test suite, execute: .\.venv\Scripts\pytest             " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
