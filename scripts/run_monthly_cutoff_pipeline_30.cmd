@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
chcp 65001 >nul
set PYTHONPATH=%CD%\src
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python scripts\run_monthly_cutoff_pipeline_30.py %*
exit /b %ERRORLEVEL%
