<#
.SYNOPSIS
    Cloud File Storage System - Application Launch Script
.DESCRIPTION
    Launches the Streamlit application using the local project virtual environment.
#>

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvStreamlit = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $VenvStreamlit)) {
    Write-Warning "Virtual environment streamlit executable was not found."
    Write-Host "Please execute .\scripts\setup.ps1 first to build the environment." -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Cloud File Storage System dashboard..." -ForegroundColor Cyan
& "$VenvStreamlit" run app.py
