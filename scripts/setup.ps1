$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e "apps/api[dev]"
if ($LASTEXITCODE -ne 0) { throw "API install failed" }
Push-Location apps/web
npm ci
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "npm ci failed" }
Pop-Location
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "Setup complete. The mock shim needs placeholder MARVEL_* values in .env; no real Marvel keys exist."
