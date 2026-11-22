@echo off
REM Arranque local en Windows
cd /d %~dp0
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
if exist .env for /f "usebackq tokens=1,* delims==" %%a in (".env") do set %%a=%%b
streamlit run app.py
