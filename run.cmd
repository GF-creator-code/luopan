@echo off
rem 一键启动出海罗盘（本机体验入口）
cd /d "%~dp0"
python -m streamlit run app.py --server.address localhost --browser.gatherUsageStats false
