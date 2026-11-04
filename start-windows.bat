@echo off
rem Tabletop GM launcher for Windows. Double-click to run.
rem First run: finds Python 3.11+ (offers to install it with winget), creates a private
rem .venv folder here, installs Tabletop GM, then shows the menu. Later runs go straight to the menu.
setlocal EnableExtensions
title Tabletop GM
cd /d "%~dp0"

set "PY="
for %%V in (3.13 3.12 3.11) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  for %%P in ("%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe") do (
    if not defined PY if exist "%%~P" set PY="%%~P"
  )
)
if defined PY goto run

echo.
echo  Tabletop GM needs Python 3.11 or newer, and it is not installed.
where winget >nul 2>&1
if errorlevel 1 goto manual
echo.
choice /c YN /m " Install Python 3.12 now with winget (Microsoft's package manager)"
if errorlevel 2 goto manual
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
  set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  goto run
)

:manual
echo.
echo  Install Python from https://www.python.org/downloads/
echo  (tick "Add python.exe to PATH" in the installer), then double-click this file again.
start "" "https://www.python.org/downloads/"
echo.
pause
exit /b 1

:run
%PY% scripts\bootstrap.py %*
if errorlevel 1 (
  echo.
  echo  Something went wrong. The message above says what.
  pause
  exit /b 1
)
exit /b 0
