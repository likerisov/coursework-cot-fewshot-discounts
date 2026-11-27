@echo off
chcp 65001 > nul
python -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
python src\analyze_portfolio.py
pause
