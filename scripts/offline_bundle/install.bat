@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist VERSION (
  echo ERROR: missing VERSION in %CD%>&2
  exit /b 1
)
if not exist PYTHON_MINOR (
  echo ERROR: missing PYTHON_MINOR in %CD%>&2
  exit /b 1
)

set /p VERSION=<VERSION
set /p PY_MINOR=<PYTHON_MINOR
set VENV_DIR=.venv

echo Creating %VENV_DIR% and installing colosseum==%VERSION% ...

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -%PY_MINOR% -m venv %VENV_DIR%
) else (
  python -m venv %VENV_DIR%
)
if errorlevel 1 exit /b 1

call "%VENV_DIR%\Scripts\activate.bat"
pip install --no-index --find-links=wheels colosseum==%VERSION%
if errorlevel 1 exit /b 1

echo.
echo Installed colosseum %VERSION%.
echo Activate the environment:
echo   %VENV_DIR%\Scripts\activate.bat
echo.
echo Smoke test:
echo   colosseum run smoke\run_sim.py --config smoke\bench.sim.toml

endlocal
