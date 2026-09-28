@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "JOB=C25_CFRP_Abaqus_LE_reduced3D"
set "INP=%JOB%.inp"

echo ============================================================
echo C25-CFRP Abaqus Learning Edition automated run
echo ============================================================

if not exist "%INP%" (
  echo ERROR: %INP% not found in this folder.
  pause
  exit /b 2
)

set "ABQ="
for /f "delims=" %%F in ('dir /b /o-n "C:\SIMULIA\Commands\abq*le.bat" 2^>nul') do (
  if not defined ABQ set "ABQ=C:\SIMULIA\Commands\%%F"
)

if not defined ABQ (
  echo Could not auto-detect Abaqus Learning Edition command.
  echo Looking on PATH...
  for %%V in (abq2026le abq2025le abq2024le abq2023le abq2022le abaqus) do (
    where %%V >nul 2>&1
    if !errorlevel! equ 0 if not defined ABQ set "ABQ=%%V"
  )
)

if not defined ABQ (
  echo ERROR: Abaqus Learning Edition command was not found.
  echo Start the "Abaqus Command" shortcut and run this BAT from there,
  echo or edit ABQ in this file to your abq20XXle.bat path.
  pause
  exit /b 3
)

echo Abaqus command: "%ABQ%"

echo.
echo [1/3] Input syntax/data check...
call "%ABQ%" job=%JOB% input=%INP% syntaxcheck interactive
if errorlevel 1 (
  echo.
  echo Syntax check returned an error. Open %JOB%.dat, %JOB%.msg and %JOB%.log.
  pause
  exit /b 4
)

echo.
echo [2/3] Running nonlinear Abaqus/Standard analysis...
call "%ABQ%" job=%JOB% input=%INP% interactive
if errorlevel 1 (
  echo.
  echo Analysis returned an error. Inspect %JOB%.sta, %JOB%.msg and %JOB%.dat.
  pause
  exit /b 5
)

if not exist "%JOB%.odb" (
  echo ERROR: Analysis ended without an ODB file.
  pause
  exit /b 6
)

echo.
echo [3/3] Extracting load-deflection and field maxima from ODB...
call "%ABQ%" python extract_odb_results.py "%JOB%.odb"
if errorlevel 1 (
  echo WARNING: ODB exists but post-processing script returned an error.
  echo The solver result itself is preserved in %JOB%.odb.
  pause
  exit /b 7
)

echo.
echo ============================================================
echo SUCCESS
echo ODB: %JOB%.odb
echo CSV: %JOB%_history.csv
echo SUMMARY: %JOB%_summary.txt
echo ============================================================
pause
endlocal
