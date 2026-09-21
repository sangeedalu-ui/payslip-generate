import os
import app
from payslip_pdf import generate_payslip_pdf, _build_earnings_lines

filepath = 'sample_salary_data.xlsx'
df, mapping = app.read_excel_data(filepath)
records = app.build_employee_records(df, mapping)

print('Mapping detected:')
for k, v in mapping.items():
    print(f'  {k} -> {v}')

os.makedirs('output/test', exist_ok=True)

for i, rec in enumerate(records):
    salary = app.compute_salary(rec)
    salary['_earnings_lines'] = _build_earnings_lines(salary)
    name = app.safe_str(rec.get('employee_name', f'emp{i}')).replace(' ', '_')
    month = app.safe_str(rec.get('salary_month', 'Unknown')).replace(' ', '_')
    path = f'output/test/Payslip_{name}_{month}.pdf'
    generate_payslip_pdf(rec, salary, output_path=path)
    print(f'Generated: {path}  Net={salary["net_salary"]:.2f}  Discrepancies={len(salary["discrepancies"])}')

print('\nDone. All payslips generated.')
