$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& "$HOME\.venv\Scripts\Activate.ps1"
python .\run.py
