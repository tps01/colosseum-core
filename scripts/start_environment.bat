@echo off
rem Create/update and activate the Colosseum development virtual environment.
rem
rem Usage from cmd.exe:
rem   scripts\start_environment.bat
rem
rem Environment overrides:
rem   set PYTHON=python
rem   set VENV_PATH=C:\path\to\.venv
rem   set EXTRAS=bench,test,docs,mutation

set "COLOSSEUM_SCRIPT_DIR=%~dp0"
for %%I in ("%COLOSSEUM_SCRIPT_DIR%..") do set "COLOSSEUM_REPO_ROOT=%%~fI"

if not defined PYTHON set "PYTHON=python"
if not defined VENV_PATH set "VENV_PATH=%COLOSSEUM_REPO_ROOT%\.venv"
if not defined EXTRAS set "EXTRAS=test,mutation"

pushd "%COLOSSEUM_REPO_ROOT%" >nul
if errorlevel 1 (
    echo Failed to change to repository root: %COLOSSEUM_REPO_ROOT% 1>&2
    exit /b 1
)

if not exist "%VENV_PATH%" (
    echo Creating virtual environment: %VENV_PATH%
    "%PYTHON%" -m venv "%VENV_PATH%"
    if errorlevel 1 goto fail_venv
)

set "COLOSSEUM_VENV_PYTHON=%VENV_PATH%\Scripts\python.exe"
set "COLOSSEUM_ACTIVATE_SCRIPT=%VENV_PATH%\Scripts\activate.bat"

if not exist "%COLOSSEUM_VENV_PYTHON%" (
    echo Virtual environment Python was not found: %COLOSSEUM_VENV_PYTHON% 1>&2
    popd >nul
    exit /b 1
)

if not exist "%COLOSSEUM_ACTIVATE_SCRIPT%" (
    echo Virtual environment activation script was not found: %COLOSSEUM_ACTIVATE_SCRIPT% 1>&2
    popd >nul
    exit /b 1
)

for /f "tokens=2,*" %%A in ('"%COLOSSEUM_VENV_PYTHON%" --version 2^>^&1') do set "COLOSSEUM_PYTHON_VERSION=%%A"
"%COLOSSEUM_VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    echo Colosseum requires Python ^>=3.9; found %COLOSSEUM_PYTHON_VERSION% 1>&2
    popd >nul
    exit /b 1
)
echo Using Python %COLOSSEUM_PYTHON_VERSION%

echo Installing/updating build tooling...
"%COLOSSEUM_VENV_PYTHON%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto fail_tooling

set "COLOSSEUM_INSTALL_TARGET=."
if not "%EXTRAS%"=="" set "COLOSSEUM_INSTALL_TARGET=.[%EXTRAS%]"

echo Installing editable project: %COLOSSEUM_INSTALL_TARGET%
"%COLOSSEUM_VENV_PYTHON%" -m pip install --editable "%COLOSSEUM_INSTALL_TARGET%"
if errorlevel 1 goto fail_project

call "%COLOSSEUM_ACTIVATE_SCRIPT%"

echo.
echo Activated Colosseum environment at %VENV_PATH%
echo Run this script from cmd.exe when PowerShell script execution is disabled.

popd >nul
exit /b 0

:fail_venv
echo Failed to create virtual environment with: %PYTHON% 1>&2
popd >nul
exit /b 1

:fail_tooling
echo Failed to install/update build tooling. 1>&2
popd >nul
exit /b 1

:fail_project
echo Failed to install editable project. 1>&2
popd >nul
exit /b 1
