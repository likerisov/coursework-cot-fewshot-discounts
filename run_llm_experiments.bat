@echo off
chcp 65001 > nul
python src\run_experiments.py --repeat 3
if errorlevel 1 exit /b 1
python src\evaluate_results.py
pause
