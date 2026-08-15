# Create .venv in this bundle directory and install colosseum from local wheels.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path VERSION) -or -not (Test-Path PYTHON_MINOR)) {
    Write-Error "missing VERSION or PYTHON_MINOR in $PWD"
}

$version = (Get-Content -Raw VERSION).Trim()
$pyMinor = (Get-Content -Raw PYTHON_MINOR).Trim()
$venv = Join-Path $PWD '.venv'

Write-Host "Creating $venv and installing colosseum-core[bench]==$version ..."

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py "-$pyMinor" -m venv $venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m venv $venv
} else {
    throw "Python $pyMinor not found (install Python or the py launcher)"
}

& (Join-Path $venv 'Scripts\Activate.ps1')
pip install --no-index --find-links=wheels "colosseum-core[bench]==$version"

Write-Host ""
Write-Host "Installed colosseum $version."
Write-Host "Activate the environment:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Smoke test:"
Write-Host "  colosseum run smoke\run_sim.py --config smoke\bench.sim.toml"
