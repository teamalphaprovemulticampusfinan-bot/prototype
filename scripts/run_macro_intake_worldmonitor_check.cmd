@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set COMPANY_DIR=%~1
set COMPANY=%~2
set MODE=%~3

if "%COMPANY_DIR%"=="" set COMPANY_DIR=nepes
if "%COMPANY%"=="" set COMPANY=nepes

if /I "%MODE%"=="nogdelt" (
  set MACRO_ENABLE_GDELT=0
) else (
  set MACRO_ENABLE_GDELT=1
)

if "%MACRO_GDELT_MIN_INTERVAL_SEC%"=="" set MACRO_GDELT_MIN_INTERVAL_SEC=6
if "%MACRO_GDELT_429_SLEEP_SEC%"=="" set MACRO_GDELT_429_SLEEP_SEC=0
if "%MACRO_GDELT_MAXRECORDS%"=="" set MACRO_GDELT_MAXRECORDS=5
set MACRO_GDELT_RETRY_ON_429=0
set MACRO_GDELT_PRE_WAIT=0
set MACRO_REUSE_TODAY_OUTPUTS=1
set MACRO_SMM_PUBLIC_TRY=0

echo ================================================================================
echo Macro intake check
echo ================================================================================
echo COMPANY_DIR=%COMPANY_DIR%
echo COMPANY=%COMPANY%
echo MACRO_ENABLE_GDELT=%MACRO_ENABLE_GDELT%
echo ================================================================================

python main.py intake --company-dir %COMPANY_DIR% --company "%COMPANY%" --agents macro --stop-on-error

if errorlevel 1 (
  echo [ERROR] macro intake failed.
  exit /b 1
)

echo ================================================================================
echo Latest macro output files
echo ================================================================================
dir /O-D data\_global_common\macro\*.csv

echo ================================================================================
echo Workspace check
echo ================================================================================
if exist workspace (
  echo workspace exists: YES
) else (
  echo workspace exists: NO
)
