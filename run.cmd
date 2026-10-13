@echo off
rem One-click launcher (ASCII only: cmd.exe misreads UTF-8 Chinese comments)
cd /d "%~dp0"
python -m streamlit run app.py --server.address localhost --browser.gatherUsageStats false
