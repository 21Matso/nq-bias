@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title NQ Bias Terminal

if exist ".venv\installed.ok" goto run

echo.
echo  Forste gang: setter opp programmet. Dette tar 1-3 minutter...
echo.
set "PY="
where py >nul 2>nul && py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo  Fant ikke Python 3.10 eller nyere.
  echo.
  echo  1. Nettsiden python.org apnes na. Last ned og installer Python.
  echo  2. VIKTIG: huk av for "Add python.exe to PATH" nederst i installasjonsvinduet.
  echo  3. Dobbeltklikk pa denne filen igjen.
  start "" https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)
if exist ".venv" rmdir /s /q ".venv"
%PY% -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo ok> ".venv\installed.ok"
echo.
echo  Ferdig installert!
echo.

:run
".venv\Scripts\python.exe" nqbias.py --menu
exit /b 0

:fail
echo.
echo  Installasjonen feilet. Sjekk nettforbindelsen og dobbeltklikk pa filen igjen.
if exist ".venv" rmdir /s /q ".venv"
pause
exit /b 1
