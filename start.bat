@echo off
echo ========================================
echo   Employee Payslip Generator
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import flask, openpyxl, pandas, fpdf" >nul 2>&1
if errorlevel 1 (
    echo Dependencies missing. Installing now...
    python -m pip install -r requirements.txt
)

echo.
if not exist "sample_salary_data.xlsx" (
    echo Generating sample data...
    python create_sample.py
)

echo.
echo Starting Payslip Generator on http://localhost:5000
echo Press Ctrl+C to stop
echo.
python app.py
pause
