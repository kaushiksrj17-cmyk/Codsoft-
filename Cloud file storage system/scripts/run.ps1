<#
.SYNOPSIS
    Cloud File Storage System - Application Launch Script
.DESCRIPTION
    Launches the Streamlit application using the local project virtual environment.
#>

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Warning "Virtual environment python executable was not found."
    Write-Host "Please execute .\scripts\setup.ps1 first to build the environment." -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Cloud File Storage System dashboard..." -ForegroundColor Cyan
& "$VenvPython" -m streamlit run app.py
