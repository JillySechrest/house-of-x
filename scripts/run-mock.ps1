$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "apps/api")
$port = if ($env:MOCK_MARVEL_PORT) { $env:MOCK_MARVEL_PORT } else { "8001" }
& (Join-Path $root ".venv\Scripts\uvicorn.exe") mock_marvel.app:app --port $port
