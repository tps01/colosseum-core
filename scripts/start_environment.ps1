param(
    [string]$Python = "python",
    [string]$VenvPath = "",
    [switch]$SkipDev
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if ([string]::IsNullOrWhiteSpace($VenvPath)) {
    $VenvPath = Join-Path $RepoRoot ".venv"
} else {
    $VenvPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($VenvPath)
}

Set-Location $RepoRoot

if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment: $VenvPath"
    & $Python -m venv $VenvPath
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment Python was not found: $VenvPython"
}

if (-not (Test-Path $ActivateScript)) {
    throw "Virtual environment activation script was not found: $ActivateScript"
}

$VersionCheck = "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
& $VenvPython -c $VersionCheck
$VersionCheckExitCode = $LASTEXITCODE
$PythonVersion = ((& $VenvPython --version) -join " ").Trim() -replace "^Python\s+", ""
if ($VersionCheckExitCode -ne 0) {
    throw "Colosseum requires Python >=3.9; found $PythonVersion"
}
Write-Host "Using Python $PythonVersion"

Write-Host "Installing/updating build tooling..."
& $VenvPython -m pip install --upgrade pip setuptools wheel

$SelectedSkipDev = $SkipDev.IsPresent -or ($env:SKIP_DEV -eq "1")
$InstallTarget = "."

Write-Host "Installing editable project: $InstallTarget"
& $VenvPython -m pip install --editable $InstallTarget

if (-not $SelectedSkipDev) {
    $DevRequirements = Join-Path $RepoRoot "requirements-dev.txt"
    if (-not (Test-Path $DevRequirements)) {
        throw "Dev requirements file was not found: $DevRequirements"
    }
    Write-Host "Installing dev requirements: requirements-dev.txt"
    & $VenvPython -m pip install -r $DevRequirements
}

. $ActivateScript

$global:ColosseumVenvPython = $VenvPython
$global:ColosseumVenvRoot = $VenvPath
$global:ColosseumSystemPy = (Get-Command py.exe -ErrorAction SilentlyContinue).Source
function global:py {
    if ($env:VIRTUAL_ENV -and $env:VIRTUAL_ENV -eq $global:ColosseumVenvRoot) {
        & $global:ColosseumVenvPython @args
        return
    }
    if ($global:ColosseumSystemPy) {
        & $global:ColosseumSystemPy @args
        return
    }
    throw "py launcher not found and Colosseum virtual environment is not active."
}

Write-Host ""
Write-Host "Activated Colosseum environment at $VenvPath"
Write-Host "To keep activation in your current shell when needed, run:"
Write-Host "  . .\scripts\start_environment.ps1"
