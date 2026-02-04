@echo off
cd /d "%~dp0"
echo Starting Telegram Cloud Scraper Pro...
echo Open in browser: http://localhost:8501
echo.
streamlit run app.py --server.port=8501
pause
