@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python .\scripts\run_tech_intake_5companies.py %*
exit /b %ERRORLEVEL%
