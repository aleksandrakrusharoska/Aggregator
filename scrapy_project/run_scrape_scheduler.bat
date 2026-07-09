@echo off
REM Start the scrape scheduler (keeps running)
REM Usage: run_scrape_scheduler.bat

set PY=%~dp0\..\..\..\AppData\Local\Programs\Python\Python312\python.exe
REM If PY not valid, just use 'python'
if not exist "%PY%" (
  set PY=python
)
%PY% "%~dp0scrape_scheduler.py"
