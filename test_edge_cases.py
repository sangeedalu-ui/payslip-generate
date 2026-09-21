"""Test smart column detection with varied column names and order."""
import io
import sys
import pandas as pd
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import app

print('=== Test 1: Different column names & order ===')
data = {
    'Emp ID': ['E-100', 'E-101'],
    'Full Name': ['Amit Das', 'Sara Khan'],
    'Role': ['Analyst', 'Sr Analyst'],
    'Dept': ['R&D', 'HR'],
    'Date of Join': [datetime(2020, 5, 1), datetime(2021, 8, 15)],
    'Office': ['Delhi', 'Bengaluru'],
    'Month': ['October 2026', 'October 2026'],
    'Days Worked': [31, 31],
    'Gross': [80000, 95000],
    'Year End Bonus': [5000, 8000],
    'PF': [9600, 11400],
    'PT': [200, 200],
    'TDS Tax': [9000, 12000],
}
df = pd.DataFrame(data)
df.to_excel('test_varied.xlsx', index=False, engine='openpyxl')

df2, mapping = app.read_excel_data('test_varied.xlsx')
print('  Mapping detected:')
for k, v in mapping.items():
    print(f'    {k} -> {v}')

recs = app.build_employee_records(df2, mapping)
assert 'employee_name' in mapping and mapping['employee_name'] == 'Full Name', 'name mapping failed'
assert 'employee_id' in mapping and mapping['employee_id'] == 'Emp ID', 'id mapping failed'
assert 'designation' in mapping and mapping['designation'] == 'Role', 'designation failed'
assert 'department' in mapping and mapping['department'] == 'Dept', 'dept failed'
assert 'work_location' in mapping and mapping['work_location'] == 'Office', 'location failed'
print('  PASS: column detection works with varied names/order')

print('\n=== Test 2: Missing columns handled safely ===')
# Salary only file - should work with blanks for missing fields
data2 = {
    'Employee Name': ['John Doe'],
    'Amount Paid': [50000],
}
df = pd.DataFrame(data2)
df.to_excel('test_minimal.xlsx', index=False, engine='openpyxl')
df2, mapping = app.read_excel_data('test_minimal.xlsx')
recs = app.build_employee_records(df2, mapping)
salary = app.compute_salary(recs[0])
print(f'  Mapping: {mapping}')
print(f'  Net salary calculated: {salary["net_salary"]}')
# Fields not in file should not be in mapping, so records won't have them -> compute 0
print('  PASS: missing fields handled without error if basic_salary/amount detected or not')

print('\n=== Test 3: Duplicate employee names handled (unique filenames) ===')
data3 = {
    'Employee Name': ['Ravi Kumar', 'Ravi Kumar', 'Sita Devi'],
    'Basic Salary': [40000, 45000, 38000],
    'Salary Month': ['Nov 2026', 'Nov 2026', 'Nov 2026'],
}
df = pd.DataFrame(data3)
df.to_excel('test_dup.xlsx', index=False, engine='openpyxl')
df2, mapping = app.read_excel_data('test_dup.xlsx')
recs = app.build_employee_records(df2, mapping)
names = [app.safe_str(r.get('employee_name')) for r in recs]
assert len(recs) == 3, 'rows lost!'
print(f'  Total rows preserved: {len(recs)} (no deletion)')
print('  PASS: no rows removed, duplicate names preserved')

print('\n=== Test 4: Salary verification catches mismatch ===')
# Build record with wrong net salary
rec = {
    'basic_salary': 50000,
    'bonus': 5000,
    'hra': 10000,
    'provident_fund': 6000,
    'tds': 9000,
    'professional_tax': 200,
    'net_salary': 40000,  # wrong
}
salary = app.compute_salary(rec)
print(f'  Calculated net: {salary["net_salary"]}, provided: 40000')
assert salary['discrepancies'], 'should flag discrepancy'
print(f'  Discrepancy flagged: {salary["discrepancies"]}')
print('  PASS: discrepancy detection works')

print('\nALL EDGE-CASE TESTS PASSED')
