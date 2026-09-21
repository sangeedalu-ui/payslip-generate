"""Generate a sample Excel file for testing the payslip generator."""
import pandas as pd
from datetime import datetime

data = {
    'Employee ID': ['EMP001', 'EMP002', 'EMP003', 'EMP004', 'EMP005'],
    'Employee Name': [
        'Priya Sharma',
        'Rajesh Kumar',
        'Ananya Patel',
        'Vikram Singh',
        'Meera Nair'
    ],
    'Designation': [
        'Senior Research Analyst',
        'Software Engineer',
        'Data Scientist',
        'Project Manager',
        'Research Associate'
    ],
    'Department': [
        'Research & Development',
        'Engineering',
        'Data Science',
        'Operations',
        'Research & Development'
    ],
    'Date of Joining': [
        datetime(2021, 3, 15),
        datetime(2022, 7, 1),
        datetime(2023, 1, 10),
        datetime(2020, 11, 20),
        datetime(2024, 6, 5)
    ],
    'Work Location': [
        'Bengaluru',
        'Hyderabad',
        'Bengaluru',
        'Mumbai',
        'Pune'
    ],
    'Salary Month': ['September 2026'] * 5,
    'Paid Days': [30, 28, 30, 30, 26],
    'Basic Salary': [65000, 55000, 60000, 80000, 45000],
    'HRA': [26000, 22000, 24000, 32000, 18000],
    'Conveyance': [1600, 1600, 1600, 1600, 1600],
    'Medical Allowance': [2500, 2500, 2500, 2500, 2500],
    'Special Allowance': [10000, 8000, 9000, 12000, 7000],
    'Bonus': [5000, 3000, 4000, 8000, 2000],
    'Overtime': [0, 2400, 0, 0, 1200],
    'Provident Fund': [7800, 6600, 7200, 9600, 5400],
    'ESI': [0, 0, 0, 0, 0],
    'Professional Tax': [200, 200, 200, 200, 200],
    'TDS': [8000, 5500, 7000, 12000, 3500],
    'Other Deductions': [500, 300, 400, 600, 200],
    'Net Salary': [93600, 81900, 90300, 113700, 68000],
}

df = pd.DataFrame(data)
output_path = 'sample_salary_data.xlsx'
df.to_excel(output_path, index=False, engine='openpyxl')
print(f'Sample Excel file created: {output_path}')
print(f'Contains {len(data["Employee ID"])} employee records')
print(f'Columns: {list(data.keys())}')
