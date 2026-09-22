"""End-to-end test using Flask test client (no server needed)."""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import app

app.app.config['TESTING'] = True
client = app.app.test_client()

print('=== 1. Test index page ===')
r = client.get('/')
print(f'  GET / -> {r.status_code}, "PAYSLIP" in body: {b"PAYSLIP GENERATOR" in r.data}')

print('\n=== 2. Test upload (no file) ===')
r = client.post('/upload', data={})
print(f'  POST /upload (no file) -> {r.status_code} (redirect expected)')

print('\n=== 3. Test upload (sample file) ===')
with open('sample_salary_data.xlsx', 'rb') as f:
    data = {'file': (io.BytesIO(f.read()), 'sample_salary_data.xlsx')}
r = client.post('/upload', data=data, content_type='multipart/form-data')
print(f'  POST /upload -> {r.status_code}')
print(f'  "PREVIEW EMPLOYEE DATA" in body: {b"PREVIEW EMPLOYEE DATA" in r.data}')
print(f'  Employee count shown: {"5 records" in r.data.decode("utf-8", "ignore") or (b"Employees:" in r.data)}')

print('\n=== 4. Test generate (individual PDFs) ===')
r = client.post('/generate', data={
    'company_name': 'ResearchCorp India Pvt. Ltd.',
    'company_address': '123 Test Ave',
    'company_phone': '+91',
    'company_email': 'hr@test.com',
    'company_website': 'test.com',
    'salary_month': '',
    'generate_all': 'on',
    'generate_combined': 'on',
}, follow_redirects=False)
print(f'  POST /generate -> {r.status_code}')
print(f'  "PAYSLIPS GENERATED" in body: {b"PAYSLIPS GENERATED" in r.data}')
# Check for generated PDFs in output folder
print(f'  "All_Employees_Payslips.pdf" mentioned: {b"All_Employees_Payslips.pdf" in r.data}')

print('\n=== 5. Test download individual PDF ===')
# Find the output dir from response
body = r.data.decode('utf-8', 'ignore')
# Just verify files exist in output
output_root = os.path.join(os.path.dirname(app.__file__), 'output')
dirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
latest = max(dirs, key=lambda d: os.path.getmtime(os.path.join(output_root, d)))
latest_dir = os.path.join(output_root, latest)
files = os.listdir(latest_dir)
print(f'  Latest output dir: {latest}')
print(f'  Files generated ({len(files)}): {files}')

print('\n=== 6. Test download single via /download/<token>/<file> ===')
token = latest
r = client.get(f'/download/{token}/{files[0]}')
print(f'  GET /download -> {r.status_code}, content-type: {r.content_type}')

print('\n=== 7. Test combined PDF download ===')
combined = os.path.join(latest_dir, 'All_Employees_Payslips.pdf')
if os.path.exists(combined):
    r = client.get(f'/download/{token}/All_Employees_Payslips.pdf')
    print(f'  GET combined -> {r.status_code}, size: {len(r.data)} bytes')

print('\n=== 8. Test ZIP download ===')
r = client.get(f'/download_all/{token}')
print(f'  GET /download_all -> {r.status_code}, content-type: {r.content_type}')

print('\nALL TESTS COMPLETE')
