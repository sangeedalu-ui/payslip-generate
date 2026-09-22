import os
import re
import io
import uuid
from datetime import datetime
from functools import reduce

import pandas as pd
from flask import (
    Flask, render_template, request, send_file, redirect,
    url_for, flash, session, jsonify, abort
)
from payslip_pdf import (
    generate_payslip_pdf, PayslipPDF, _build_earnings_lines,
    _fmt_currency as payslip_fmt_currency, number_to_words,
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(__file__), 'output')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

FIELD_ALIASES = {
    'employee_id': ['employee id', 'emp id', 'emp_id', 'employee_id', 'id', 'employeeid', 'empid'],
    'employee_name': ['employee name', 'emp name', 'name', 'employee_name', 'emp_name', 'empname', 'employee name', 'full name', 'employee full name', "employee's name", 'staff name'],
    'designation': ['designation', 'title', 'job title', 'role', 'position', 'job role', 'employee designation'],
    'department': ['department', 'dept', 'dept.', 'department name', 'dept name'],
    'date_of_joining': ['date of joining', 'joining date', 'doj', 'join date', 'date of joining', 'joined date', 'date of join', 'joining'],
    'work_location': ['work location', 'location', 'office', 'city', 'branch', 'workplace', 'place of work', 'working location'],
    'salary_month': ['salary month', 'month', 'pay period', 'pay period', 'salary period', 'payslip month', 'for the month', 'salary for the month', 'month of'],
    'paid_days': ['paid days', 'days paid', 'working days', 'work days', 'days', 'paid days', 'days worked', 'no of days', 'no of days paid', 'total days'],
    'basic_salary': ['basic salary', 'basic', 'basic pay', 'basic salary', 'base salary', 'base pay', 'gross salary', 'gross', 'gross pay', 'monthly basic', 'basic wages'],
    'bonus': ['bonus', 'performance bonus', 'incentive', 'incentives', 'special bonus', 'annual bonus', 'year end bonus'],
    'hra': ['hra', 'house rent allowance', 'house rent', 'rent allowance', 'house rent allowance (hra)'],
    'conveyance': ['conveyance', 'conveyance allowance', 'travel allowance', 'transport', 'transport allowance'],
    'medical': ['medical', 'medical allowance', 'medical reimbursement', 'medical allowance'],
    'special_allowance': ['special allowance', 'special', 'other allowance', 'special allowance', 'allowances'],
    'overtime': ['overtime', 'ot', 'over time', 'overtime pay', 'overtime allowance'],
    'provident_fund': ['provident fund', 'pf', 'epf', 'provident fund (pf)', 'employee pf'],
    'esi': ['esi', 'esic', 'employee state insurance', 'employee state insurance (esi)'],
    'professional_tax': ['professional tax', 'pt', 'prof tax', 'professional tax', 'pro tax'],
    'tds': ['tds', 'tax deducted at source', 'income tax', 'tax', 'tds tax'],
    'other_deductions': ['other deductions', 'other deduction', 'misc deductions', 'miscellaneous', 'other', 'miscellaneous deductions'],
    'net_salary': ['net salary', 'net pay', 'take home', 'net salary', 'in hand', 'net_amount', 'amount paid', 'net amount'],
    'total_earnings': ['total earnings', 'gross earnings', 'total earning', 'total earnings'],
    'total_deductions': ['total deductions', 'total deduction', 'total deductions'],
}


def normalize_column(name):
    return re.sub(r'[^a-z0-9]', '', name.lower().strip())


def match_column(col_name, field_key):
    norm = normalize_column(col_name)
    for alias in FIELD_ALIASES[field_key]:
        if normalize_column(alias) == norm:
            return True
    return False


def map_columns(df):
    mapping = {}
    used_cols = set()
    for field_key in FIELD_ALIASES:
        for col in df.columns:
            if col not in used_cols and match_column(col, field_key):
                mapping[field_key] = col
                used_cols.add(col)
                break
    return mapping


def to_float(val):
    if pd.isna(val) or val == '' or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def format_currency(amount):
    if amount is None:
        return '₹0.00'
    amount = round(float(amount), 2)
    if amount < 0:
        return f'-₹{abs(amount):,.2f}'
    return f'₹{amount:,.2f}'


def format_currency_words(amount):
    if amount is None or amount == 0:
        return 'Rupees Zero Only'
    amount = abs(round(float(amount), 2))
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def int_to_words(n):
        if n == 0:
            return 'Zero'
        parts = []
        if n >= 10000000:
            parts.append(int_to_words(n // 10000000) + ' Crore')
            n %= 10000000
        if n >= 100000:
            parts.append(int_to_words(n // 100000) + ' Lakh')
            n %= 100000
        if n >= 1000:
            parts.append(int_to_words(n // 1000) + ' Thousand')
            n %= 1000
        if n >= 100:
            parts.append(ones[n // 100] + ' Hundred')
            n %= 100
        if n >= 20:
            word = tens[n // 10]
            if n % 10:
                word += ' ' + ones[n % 10]
            parts.append(word)
        elif n > 0:
            parts.append(ones[n])
        return ' '.join(p for p in parts if p)

    whole = int(amount)
    decimal = round((amount - whole) * 100)
    result = 'Rupees ' + int_to_words(whole)
    if decimal > 0:
        result += ' and ' + int_to_words(decimal) + ' Paise'
    result += ' Only'
    return result


def read_excel_data(filepath):
    df = pd.read_excel(filepath, engine='openpyxl')
    df.columns = [str(c).strip() for c in df.columns]
    mapping = map_columns(df)
    return df, mapping


def build_employee_records(df, mapping):
    records = []
    for _, row in df.iterrows():
        rec = {}
        for field_key, col_name in mapping.items():
            rec[field_key] = row[col_name]
        rec['_raw'] = {col: row[col] for col in df.columns}
        records.append(rec)
    return records


def compute_salary(rec):
    basic = to_float(rec.get('basic_salary', 0))
    bonus = to_float(rec.get('bonus', 0))
    hra = to_float(rec.get('hra', 0))
    conveyance = to_float(rec.get('conveyance', 0))
    medical = to_float(rec.get('medical', 0))
    special = to_float(rec.get('special_allowance', 0))
    overtime = to_float(rec.get('overtime', 0))

    pf = to_float(rec.get('provident_fund', 0))
    esi = to_float(rec.get('esi', 0))
    pt = to_float(rec.get('professional_tax', 0))
    tds = to_float(rec.get('tds', 0))
    other_ded = to_float(rec.get('other_deductions', 0))

    total_earnings = basic + bonus + hra + conveyance + medical + special + overtime
    total_deductions = pf + esi + pt + tds + other_ded
    net_salary = total_earnings - total_deductions

    provided_net = to_float(rec.get('net_salary', 0))
    provided_gross = to_float(rec.get('total_earnings', 0))
    provided_total_ded = to_float(rec.get('total_deductions', 0))

    has_earnings_components = total_earnings > 0
    has_deduction_components = total_deductions > 0

    discrepancies = []
    if has_earnings_components:
        net_salary = total_earnings - total_deductions
    elif provided_net > 0:
        net_salary = provided_net
    elif provided_gross > 0 and not has_deduction_components:
        net_salary = provided_gross
    else:
        net_salary = provided_net

    if provided_gross > 0 and has_earnings_components and abs(provided_gross - total_earnings) > 0.01:
        discrepancies.append(f'Total Earnings mismatch: Excel shows {format_currency(provided_gross)}, calculated {format_currency(total_earnings)}')
    if provided_total_ded > 0 and has_deduction_components and abs(provided_total_ded - total_deductions) > 0.01:
        discrepancies.append(f'Total Deductions mismatch: Excel shows {format_currency(provided_total_ded)}, calculated {format_currency(total_deductions)}')
    if provided_net > 0 and has_earnings_components and abs(provided_net - net_salary) > 0.01:
        discrepancies.append(f'Net Salary mismatch: Excel shows {format_currency(provided_net)}, calculated {format_currency(net_salary)}')

    return {
        'basic_salary': basic,
        'bonus': bonus,
        'hra': hra,
        'conveyance': conveyance,
        'medical': medical,
        'special_allowance': special,
        'overtime': overtime,
        'total_earnings': total_earnings,
        'provident_fund': pf,
        'esi': esi,
        'professional_tax': pt,
        'tds': tds,
        'other_deductions': other_ded,
        'total_deductions': total_deductions,
        'net_salary': net_salary,
        'discrepancies': discrepancies,
    }


def safe_str(val, default=''):
    if pd.isna(val) or val is None:
        return default
    return str(val).strip()


def format_date(val):
    if pd.isna(val) or val is None:
        return ''
    if isinstance(val, datetime):
        return val.strftime('%d-%b-%Y')
    if isinstance(val, pd.Timestamp):
        return val.strftime('%d-%b-%Y')
    s = str(val).strip()
    for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d %b %Y', '%B %d, %Y']:
        try:
            return datetime.strptime(s, fmt).strftime('%d-%b-%Y')
        except ValueError:
            continue
    return s


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('index'))

    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Please upload an Excel file (.xlsx or .xls).', 'error')
        return redirect(url_for('index'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{uuid.uuid4().hex}_{file.filename}')
    file.save(filepath)

    try:
        df, mapping = read_excel_data(filepath)
    except Exception as e:
        flash(f'Error reading Excel file: {str(e)}', 'error')
        return redirect(url_for('index'))

    required_fields = ['employee_name']
    missing = [f for f in required_fields if f not in mapping]
    if missing:
        flash(f'Could not identify required columns: {", ".join(missing)}. Please check your Excel file headers.', 'error')
        return redirect(url_for('index'))

    records = build_employee_records(df, mapping)

    salary_months = set()
    for rec in records:
        m = safe_str(rec.get('salary_month', ''))
        if m:
            salary_months.add(m)

    session['filepath'] = filepath
    session['mapping'] = mapping
    session['record_count'] = len(records)

    return render_template('preview.html',
                           records=records,
                           mapping=mapping,
                           salary_months=sorted(salary_months),
                           filename=file.filename)


@app.route('/generate', methods=['POST'])
def generate():
    filepath = session.get('filepath')
    if not filepath or not os.path.exists(filepath):
        flash('Please upload a file first.', 'error')
        return redirect(url_for('index'))

    company_name = request.form.get('company_name', 'ResearchCorp India Pvt. Ltd.')
    company_address = request.form.get('company_address', '123 Innovation Park, Electronic City, Bengaluru - 560100')
    company_phone = request.form.get('company_phone', '+91 80 1234 5678')
    company_email = request.form.get('company_email', 'hr@researchcorp.in')
    company_website = request.form.get('company_website', 'www.researchcorp.in')

    company = {
        'name': company_name,
        'address': company_address,
        'phone': company_phone,
        'email': company_email,
        'website': company_website,
    }

    selected_month = request.form.get('salary_month', '')
    generate_all = request.form.get('generate_all', '') == 'on'
    generate_combined = request.form.get('generate_combined', '') == 'on'

    try:
        df, mapping = read_excel_data(filepath)
    except Exception as e:
        flash(f'Error reading Excel file: {str(e)}', 'error')
        return redirect(url_for('index'))

    records = build_employee_records(df, mapping)

    if selected_month and not generate_all:
        month_col = mapping.get('salary_month')
        if month_col:
            records = [r for r in records if safe_str(r.get('salary_month', '')).lower() == selected_month.lower()]

    if not records:
        flash('No employees found for the selected criteria.', 'error')
        return redirect(url_for('index'))

    output_token = uuid.uuid4().hex
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], output_token)
    os.makedirs(output_dir, exist_ok=True)

    pdf_files = []
    discrepancies_list = []

    for rec in records:
        salary = compute_salary(rec)
        salary['_earnings_lines'] = _build_earnings_lines(salary)

        if salary['discrepancies']:
            emp_name = safe_str(rec.get('employee_name', 'Unknown'))
            discrepancies_list.append((emp_name, salary['discrepancies']))

        emp_name_safe = safe_str(rec.get('employee_name', 'Unknown')).replace(' ', '_').replace('/', '_')
        salary_month = safe_str(rec.get('salary_month', 'Unknown')).replace(' ', '_').replace('/', '_')
        filename = f'Payslip_{emp_name_safe}_{salary_month}.pdf'
        filepath_pdf = os.path.join(output_dir, filename)

        generate_payslip_pdf(rec, salary, company, output_path=filepath_pdf)
        pdf_files.append((filename, output_token))

    combined_pdf_path = None
    if generate_combined and len(records) > 1:
        from payslip_pdf import PayslipPDF

        combined = PayslipPDF()
        for rec in records:
            salary = compute_salary(rec)
            salary['_earnings_lines'] = _build_earnings_lines(salary)
            combined.add_page()
            combined._draw_header(company, rec.get('salary_month', ''))
            combined._employee_section(rec)
            if salary.get('discrepancies'):
                combined._discrepancy(salary['discrepancies'])
            combined._salary_tables(salary)
            net = salary['net_salary']
            x0 = combined.get_x()
            y0 = combined.get_y() + 4
            combined.set_fill_color(26, 35, 126)
            combined.rect(x0, y0, 210 - 28, 13, 'F')
            combined.set_text_color(255, 255, 255)
            combined._set_font( 'B', 13)
            combined.set_xy(x0 + 6, y0 + 3.5)
            combined.cell(70, 6, 'NET SALARY')
            combined.set_xy(210 - 14 - 48, y0 + 2.5)
            combined._set_font( 'B', 15)
            combined.cell(48, 8, payslip_fmt_currency(net), align='R')
            combined.set_y(y0 + 18)
            combined._set_font( 'B', 9)
            combined.set_text_color(26, 35, 126)
            combined.set_xy(x0, combined.get_y())
            combined.cell(30, 5, 'Amount in Words:')
            combined._set_font( '', 9)
            combined.set_text_color(51, 51, 51)
            combined.set_x(x0 + 31)
            combined.multi_cell(210 - 28 - 31, 5, number_to_words(net))
            combined.set_y(-36)
            combined._footer(datetime.now().strftime('%d-%b-%Y %H:%M'))

        combined_pdf_path = os.path.join(output_dir, 'All_Employees_Payslips.pdf')
        combined.output(combined_pdf_path)

    return render_template('download.html',
                           pdf_files=pdf_files,
                           output_token=output_token,
                           combined_pdf_path=combined_pdf_path,
                           discrepancies=discrepancies_list)


@app.route('/download/<token>/<path:filename>')
def download_file(token, filename):
    base = os.path.realpath(app.config['OUTPUT_FOLDER'])
    full = os.path.realpath(os.path.join(base, token, filename))
    if not full.startswith(base + os.sep) or not os.path.isfile(full):
        abort(404)
    return send_file(full, as_attachment=True)


@app.route('/download_all/<token>')
def download_all(token):
    import zipfile
    base = os.path.realpath(app.config['OUTPUT_FOLDER'])
    target_dir = os.path.realpath(os.path.join(base, token))
    if not target_dir.startswith(base + os.sep) or not os.path.isdir(target_dir):
        abort(404)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in os.listdir(target_dir):
            if f.endswith('.pdf'):
                full = os.path.join(target_dir, f)
                if os.path.isfile(full):
                    zf.write(full, f)
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='Payslips.zip')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
