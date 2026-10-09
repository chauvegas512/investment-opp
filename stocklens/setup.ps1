$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$stocklensPython = Get-Command python -ErrorAction SilentlyContinue
if (-not $stocklensPython) { throw 'Install Python >= 3.10 from python.org, then run setup.ps1 again.' }
python -c "import sys; assert sys.version_info >= (3,10), 'Python >= 3.10 required'"
if ($LASTEXITCODE -ne 0) { throw 'Python >= 3.10 required.' }
$stocklensVenv = Join-Path $HOME '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $stocklensVenv 'Scripts/python.exe'))) { python -m venv $stocklensVenv }
& (Join-Path $stocklensVenv 'Scripts/Activate.ps1')
python -m pip install -U pip
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
Write-Host 'Setup complete. Run start.ps1 and open http://127.0.0.1:8787. Edge is used for PDF export.'
