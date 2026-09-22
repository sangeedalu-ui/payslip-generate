"""Professional payslip PDF generation using fpdf2 (pure Python, no native deps)."""
import os
from datetime import datetime

from fpdf import FPDF

NAVY = (26, 35, 126)
INDIGO = (40, 53, 147)
LIGHT_BG = (245, 247, 255)
DIVIDER = (224, 224, 224)
TEXT = (51, 51, 51)
MUTED = (119, 119, 119)
WHITE = (255, 255, 255)
TOTAL_BG = (232, 234, 246)
ORANGE = (230, 81, 0)
AMBER_BG = (255, 243, 224)
RED = (198, 40, 40)

PAGE_W = 210
PAGE_H = 297
MARGIN = 14


def _fmt_currency(amount):
    if amount is None:
        return 'Rs 0.00'
    amount = round(float(amount), 2)
    return f'Rs {amount:,.2f}'


def number_to_words(amount):
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
            w = tens[n // 10]
            if n % 10:
                w += ' ' + ones[n % 10]
            parts.append(w)
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


def _format_display_date(val):
    if val is None:
        return ''
    if isinstance(val, (datetime,)) or hasattr(val, 'strftime'):
        try:
            return val.strftime('%d-%b-%Y')
        except Exception:
            return str(val)
    s = str(val).strip()
    if not s or s.lower() == 'nan':
        return ''
    for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d %b %Y', '%B %d, %Y', '%d-%m-%y']:
        try:
            return datetime.strptime(s[:10], fmt).strftime('%d-%b-%Y')
        except ValueError:
            continue
    return s


class PayslipPDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(MARGIN, 12, MARGIN)
        self._register_fonts()

    def _register_fonts(self):
        self._core_font = False
        font_regular = self._find_font(['arial.ttf', 'DejaVuSans.ttf'])
        if not font_regular:
            self._core_font = True
            return
        font_bold = self._find_font(['arialbd.ttf', 'DejaVuSans-Bold.ttf'])
        self.add_font('PayslipFont', '', font_regular)
        self.add_font('PayslipFont', 'B', font_bold or font_regular)

    @staticmethod
    def _find_font(candidates):
        base_dirs = [
            os.environ.get('WINDIR', 'C:/Windows') + '/Fonts',
            '/usr/share/fonts/truetype/dejavu/',
            '/usr/share/fonts/truetype/liberation/',
        ]
        for base in base_dirs:
            for cand in candidates:
                p = os.path.join(base, cand)
                if os.path.exists(p):
                    return p
        return None

    def _set_font(self, style, size):
        if getattr(self, '_core_font', False):
            self.set_font('helvetica', style, size)
        else:
            self.set_font('PayslipFont', style, size)

    def _draw_header(self, company, salary_month):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, PAGE_W, 30, 'F')

        # Logo placeholder
        self.set_fill_color(*INDIGO)
        self.rect(14, 5, 20, 20, 'FD')
        self._set_font( '', 6)
        self.set_text_color(*WHITE)
        self.set_xy(15, 10)
        self.cell(18, 4, 'COMPANY', align='C')
        self.set_xy(15, 14)
        self.cell(18, 4, 'LOGO', align='C')

        # Company info
        self.set_xy(38, 5)
        self._set_font( 'B', 13)
        self.cell(110, 6, company.get('name', ''), align='L')
        self._set_font( '', 7.5)
        self.set_text_color(230, 230, 230)
        self.set_xy(38, 12)
        self.cell(110, 4, company.get('address', ''), align='L')
        self.set_xy(38, 17)
        contact = f"Phone: {company.get('phone', '')}  |  Email: {company.get('email', '')}  |  {company.get('website', '')}"
        self.cell(110, 4, contact, align='L')

        # Payslip title
        self.set_xy(160, 6)
        self._set_font( 'B', 20)
        self.set_text_color(*WHITE)
        self.cell(40, 8, 'PAYSLIP', align='R')
        self.set_xy(160, 16)
        self._set_font( '', 9)
        self.set_text_color(210, 215, 255)
        self.cell(40, 5, str(salary_month) if salary_month else '', align='R')

        self.ln(36)
        self.set_text_color(*NAVY)
        self._set_font( 'B', 10)

    def _employee_section(self, emp):
        self.set_fill_color(*LIGHT_BG)
        x0 = self.get_x()
        y0 = self.get_y()
        self.rect(x0, y0, PAGE_W - 2 * MARGIN, 42, 'F')
        self.set_draw_color(*DIVIDER)
        self.line(x0, y0 + 6, PAGE_W - MARGIN, y0 + 6)

        self._set_font( 'B', 8)
        self.set_text_color(*NAVY)
        self.set_xy(x0, y0 + 2)
        self.cell(60, 5, 'EMPLOYEE INFORMATION')

        fields = [
            ('Employee Name', emp.get('employee_name', 'N/A')),
            ('Employee ID', emp.get('employee_id', 'N/A')),
            ('Designation', emp.get('designation', 'N/A')),
            ('Department', emp.get('department', 'N/A')),
            ('Date of Joining', _format_display_date(emp.get('date_of_joining', ''))),
            ('Work Location', emp.get('work_location', 'N/A')),
            ('Salary Month', emp.get('salary_month', '')),
            ('Paid Days', emp.get('paid_days', '')),
        ]

        col_w = (PAGE_W - 2 * MARGIN - 24) / 3
        cursor_y = y0 + 9
        row = 0
        for i in range(0, len(fields), 3):
            chunk = fields[i:i + 3]
            for j, (label, value) in enumerate(chunk):
                x = x0 + 8 + j * (col_w + 8)
                self.set_xy(x, cursor_y)
                self._set_font( '', 6.5)
                self.set_text_color(*MUTED)
                self.cell(col_w, 4, label.upper())
                self.set_xy(x, cursor_y + 4.5)
                self._set_font( 'B', 9)
                self.set_text_color(*TEXT)
                self.cell(col_w, 5, str(value)[:32])
            row += 1
            cursor_y += 13.5

        self.set_y(y0 + 42)

    def _discrepancy(self, discs):
        self.set_fill_color(*AMBER_BG)
        x0 = self.get_x()
        y0 = self.get_y()
        self.rect(x0, y0, PAGE_W - 2 * MARGIN, 12, 'F')
        self.set_draw_color(*ORANGE)
        self.line(x0, y0, x0, y0 + 12)
        self.set_xy(x0 + 5, y0 + 1)
        self._set_font( 'B', 7.5)
        self.set_text_color(*ORANGE)
        self.cell(0, 4, 'WARNING: SALARY DISCREPANCY DETECTED')
        self._set_font( '', 7)
        text = '  |  '.join(discs)
        self.set_xy(x0 + 5, y0 + 5)
        self.cell(PAGE_W - 2 * MARGIN - 10, 4, text[:110])
        self.set_y(y0 + 16)

    def _salary_tables(self, salary):
        x0 = self.get_x()
        y0 = self.get_y()
        col_w = (PAGE_W - 2 * MARGIN - 8) / 2
        self._draw_table(x0, y0, col_w, 'EARNINGS', [
            ('Basic Salary', salary['basic_salary']),
        ], salary['total_earnings'], 'Total Earnings', salary.get('_earnings_lines', []))

        self._draw_table(x0 + col_w + 8, y0, col_w, 'DEDUCTIONS', [
            ('Provident Fund (PF)', salary['provident_fund']),
            ('ESI', salary['esi']),
            ('Professional Tax', salary['professional_tax']),
            ('TDS', salary['tds']),
            ('Other Deductions', salary['other_deductions']),
        ], salary['total_deductions'], 'Total Deductions', [])

        self.set_y(y0 + 8 + max(len(salary.get('_earnings_lines', [])) + 3, 7) * 7)

    def _draw_table(self, x, y, col_w, title, base_rows, total, total_label, extra_lines):
        self.set_xy(x, y)
        self._set_font( 'B', 9)
        self.set_text_color(*WHITE)
        self.set_fill_color(*NAVY)
        self.cell(col_w, 8, title, 'LT', 0, 'L')
        self.cell(0, 0)
        self.cell(col_w, 8, 'Amount', 'RT', 1, 'R')
        self.set_fill_color(*LIGHT_BG)

        row_h = 7
        line_y = y + 8
        self._set_font( '', 9)

        all_rows = base_rows + extra_lines
        for i, (label, val) in enumerate(all_rows):
            if i % 2 == 0:
                self.set_fill_color(*LIGHT_BG)
            else:
                self.set_fill_color(*WHITE)
            self.set_text_color(*TEXT)
            self.set_xy(x, line_y)
            self._set_font( '', 9)
            self.cell(col_w - 28, row_h, label[:30], 0, 0, 'L')
            self.cell(28, row_h, _fmt_currency(val), 0, 1, 'R', fill=True)

        # Total row
        self.set_xy(x, line_y)
        self._set_font( 'B', 9)
        self.set_text_color(*NAVY)
        self.set_fill_color(*TOTAL_BG)
        self.cell(col_w - 28, row_h + 1, total_label, 'LT', 0, 'L', fill=True)
        self.cell(28, row_h + 1, _fmt_currency(total), 'RT', 1, 'R', fill=True)

    def _net_salary(self, net):
        self.set_fill_color(*NAVY)
        x0 = self.get_x()
        y0 = self.get_y() + 4
        self.rect(x0, y0, PAGE_W - 2 * MARGIN, 12, 'F')
        self.set_text_color(*WHITE)
        self.set_xy(x0 + 6, y0 + 3)
        self._set_font( 'B', 12)
        self.cell(80, 6, 'NET SALARY')
        self.set_xy(PAGE_W - MARGIN - 12, y0 + 1.5)
        self._set_font( 'B', 14)
        self.cell(12, 9, _fmt_currency(net), align='R')

    def _amount_words(self, net):
        self.set_xy(MARGIN, self.get_y() + 18)
        self._set_font( '', 9)
        self.set_text_color(*MUTED)
        self.cell(30, 5, '')
        self.set_text_color(*NAVY)
        self._set_font( 'B', 9)
        self.set_xy(MARGIN, self.get_y())
        self.set_text_color(*TEXT)
        self._set_font( '', 9)
        return number_to_words(net)

    def _footer(self, now):
        x0 = MARGIN
        x1 = PAGE_W - MARGIN
        div_y = 262

        self.set_y(div_y)
        self.set_draw_color(*DIVIDER)
        self.line(x0, div_y, x1, div_y)

        # Authorized signature (left)
        self.set_draw_color(*MUTED)
        self.line(x0, 277, x0 + 45, 277)
        self._set_font('', 8)
        self.set_text_color(*MUTED)
        self.set_xy(x0, 278.5)
        self.cell(45, 4, 'Authorized Signature', align='C')

        # Footer notes (right), stacked from divider down
        notes = [
            ('This is a computer-generated payslip and does not require a physical signature.', MUTED),
            ('CONFIDENTIAL: This document contains salary information intended solely for the named employee.', RED),
            (f'Generated on: {now}', MUTED),
        ]
        col_x = PAGE_W / 2
        col_w = x1 - col_x
        self._set_font('', 7)
        cur = div_y + 2
        for text, color in notes:
            self.set_text_color(*color)
            self.set_xy(col_x, cur)
            self.multi_cell(col_w, 3.5, text, align='R')
            cur = self.get_y() + 1
        self.set_text_color(*MUTED)


def _build_earnings_lines(salary):
    lines = []
    if salary.get('hra', 0):
        lines.append(('HRA', salary['hra']))
    if salary.get('conveyance', 0):
        lines.append(('Conveyance', salary['conveyance']))
    if salary.get('medical', 0):
        lines.append(('Medical Allowance', salary['medical']))
    if salary.get('special_allowance', 0):
        lines.append(('Special Allowance', salary['special_allowance']))
    if salary.get('overtime', 0):
        lines.append(('Overtime', salary['overtime']))
    if salary.get('bonus', 0):
        lines.append(('Bonus', salary['bonus']))
    return lines


def generate_payslip_pdf(rec, salary, company=None, output_path=None):
    if company is None:
        company = {
            'name': 'ResearchCorp India Pvt. Ltd.',
            'address': '123 Innovation Park, Electronic City, Bengaluru - 560100',
            'phone': '+91 80 1234 5678',
            'email': 'hr@researchcorp.in',
            'website': 'www.researchcorp.in',
        }

    salary = dict(salary)
    salary['_earnings_lines'] = _build_earnings_lines(salary)

    pdf = PayslipPDF()
    pdf.add_page()
    pdf._draw_header(company, rec.get('salary_month', ''))
    pdf._employee_section(rec)
    if salary.get('discrepancies'):
        pdf._discrepancy(salary['discrepancies'])
    pdf._salary_tables(salary)

    net = salary['net_salary']
    words = number_to_words(net)

    # Net salary bar with words
    x0 = pdf.get_x()
    y0 = pdf.get_y() + 4
    pdf.set_fill_color(*NAVY)
    pdf.rect(x0, y0, PAGE_W - 2 * MARGIN, 13, 'F')
    pdf.set_text_color(*WHITE)
    pdf._set_font( 'B', 13)
    pdf.set_xy(x0 + 6, y0 + 3.5)
    pdf.cell(70, 6, 'NET SALARY')
    pdf.set_xy(PAGE_W - MARGIN - 48, y0 + 2.5)
    pdf._set_font( 'B', 15)
    pdf.cell(48, 8, _fmt_currency(net), align='R')

    # Words
    pdf.set_y(y0 + 18)
    pdf._set_font( 'B', 9)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(x0, pdf.get_y())
    pdf.cell(30, 5, 'Amount in Words:')
    pdf._set_font( '', 9)
    pdf.set_text_color(*TEXT)
    pdf.set_x(x0 + 31)
    pdf.multi_cell(PAGE_W - 2 * MARGIN - 31, 5, words)

    pdf.set_y(-36)
    pdf._footer(datetime.now().strftime('%d-%b-%Y %H:%M'))

    if output_path:
        pdf.output(output_path)
        return output_path
    return pdf
