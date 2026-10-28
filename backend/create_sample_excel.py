# create_sample_excel.py
"""
ساخت فایل اکسل نمونه با Dropdown های معتبر
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment


def create_sample_excel():
    wb = Workbook()
    
    # ============================================================
    # استایل‌های مشترک
    # ============================================================
    header_font = Font(name='B Nazanin', size=12, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E40AF', end_color='1E40AF', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    content_font = Font(name='B Nazanin', size=11)
    content_align = Alignment(horizontal='right', vertical='center')
    
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    example_fill = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid')
    
    # ============================================================
    # شیت ۰: لیست‌های کشویی (مرجع)
    # ============================================================
    ws_refs = wb.active
    ws_refs.title = 'لیست‌های_مرجع'
    ws_refs.sheet_view.rightToLeft = True
    
    # تعریف لیست‌ها
    roles_list = ['پرستار', 'سرپرستار', 'سوپروایزر', 'مترون']
    
    positions_list = [
        'مترون',
        'جانشین مترون',
        'سوپروایزر بالینی',
        'سرپرستار',
        'سوپروایزر بخش',
        'کارشناس خبره و جانشین 1',
        'کارشناس خبره و جانشین 2',
        'پرستار',
        'ماما',
        'کارشناس آموزش شیردهی',
        'کارشناس/کاردان اتاق عمل',
        'بهیار',
        'کمک پرستار',
        'نگهبانی',
        'اینترنشیپ',
        'کارشناس/کاردان بخش',
        'پشتیبانی',
        'خدمات',
    ]
    
    shift_types_list = [
        'سه نوبتی',
        'ثابت صبح',
        'ثابت عصر',
        'ثابت شب',
        'دو نوبتی (عصر-شب)',
        'دو نوبتی (صبح-شب)',
        'دو نوبتی (صبح-عصر)',
    ]
    
    employment_list = ['رسمی', 'پیمانی', 'قراردادی', 'شرکتی', 'طرحی']
    
    # نوشتن لیست‌ها در ستون‌های A, B, C, D
    columns = [
        ('نقش', roles_list),
        ('سمت', positions_list),
        ('نوع شیفت', shift_types_list),
        ('وضعیت استخدام', employment_list),
    ]
    
    max_rows = max(len(lst) for _, lst in columns)
    
    for col_idx, (header, items) in enumerate(columns, 1):
        # هدر
        cell = ws_refs.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws_refs.column_dimensions[get_column_letter(col_idx)].width = 25
        
        # آیتم‌ها
        for row_idx, item in enumerate(items, 2):
            cell = ws_refs.cell(row=row_idx, column=col_idx, value=item)
            cell.font = content_font
            cell.alignment = content_align
            cell.border = thin_border
    
    ws_refs.row_dimensions[1].height = 30
    
    # ============================================================
    # شیت ۱: پرسنل
    # ============================================================
    ws1 = wb.create_sheet('پرسنل', 1)  # موقعیت دوم
    ws1.sheet_view.rightToLeft = True
    
    headers1 = [
        'نام کاربری *',
        'کد ملی',
        'نام *',
        'نام خانوادگی *',
        'نقش *',
        'بخش *',
        'بخش‌های اضافی',
        'سمت',
        'نوع شیفت',
        'وضعیت استخدام',
        'سابقه کار (1-35)',
        'ایمیل',
        'رمز عبور موقت',
    ]
    widths1 = [18, 15, 15, 18, 15, 15, 20, 22, 20, 18, 15, 22, 18]
    
    for col_idx, header in enumerate(headers1, 1):
        cell = ws1.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws1.column_dimensions[get_column_letter(col_idx)].width = widths1[col_idx - 1]
    
    ws1.row_dimensions[1].height = 40
    
    # ============================================================
    # ✅ Data Validation (Dropdown) — ستون‌های ۵ تا ۱۱
    # ============================================================
    
    # فرض: تا ردیف ۱۰۰۰ کاربر ممکن است اطلاعات وارد کند
    max_data_rows = 1000
    
    # -------------------------------
    # ستون ۵: نقش
    # -------------------------------
    dv_role = DataValidation(
        type="list",
        formula1="=لیست‌های_مرجع!$A$2:$A$5",
        allow_blank=True,
        showDropDown=False,   # ← False یعنی dropdown نمایش داده شود!
    )
    dv_role.error = 'لطفاً از لیست انتخاب کنید'
    dv_role.errorTitle = 'مقدار نامعتبر'
    dv_role.prompt = 'نقش کاربر را از لیست انتخاب کنید'
    dv_role.promptTitle = 'نقش'
    dv_role.showErrorMessage = True
    dv_role.showInputMessage = True
    ws1.add_data_validation(dv_role)
    dv_role.add(f'E2:E{max_data_rows + 1}')
    
    # -------------------------------
    # ستون ۸: سمت
    # -------------------------------
    dv_position = DataValidation(
        type="list",
        formula1="=لیست‌های_مرجع!$B$2:$B$19",
        allow_blank=True,
        showDropDown=False,
    )
    dv_position.error = 'لطفاً از لیست انتخاب کنید'
    dv_position.errorTitle = 'مقدار نامعتبر'
    dv_position.prompt = 'سمت را از لیست انتخاب کنید'
    dv_position.promptTitle = 'سمت'
    dv_position.showErrorMessage = True
    dv_position.showInputMessage = True
    ws1.add_data_validation(dv_position)
    dv_position.add(f'H2:H{max_data_rows + 1}')
    
    # -------------------------------
    # ستون ۹: نوع شیفت
    # -------------------------------
    dv_shift = DataValidation(
        type="list",
        formula1="=لیست‌های_مرجع!$C$2:$C$8",
        allow_blank=True,
        showDropDown=False,
    )
    dv_shift.error = 'لطفاً از لیست انتخاب کنید'
    dv_shift.errorTitle = 'مقدار نامعتبر'
    dv_shift.prompt = 'نوع شیفت را انتخاب کنید'
    dv_shift.promptTitle = 'نوع شیفت'
    dv_shift.showErrorMessage = True
    dv_shift.showInputMessage = True
    ws1.add_data_validation(dv_shift)
    dv_shift.add(f'I2:I{max_data_rows + 1}')
    
    # -------------------------------
    # ستون ۱۰: وضعیت استخدام
    # -------------------------------
    dv_employment = DataValidation(
        type="list",
        formula1="=لیست‌های_مرجع!$D$2:$D$6",
        allow_blank=True,
        showDropDown=False,
    )
    dv_employment.error = 'لطفاً از لیست انتخاب کنید'
    dv_employment.errorTitle = 'مقدار نامعتبر'
    dv_employment.prompt = 'وضعیت استخدام را انتخاب کنید'
    dv_employment.promptTitle = 'وضعیت استخدام'
    dv_employment.showErrorMessage = True
    dv_employment.showInputMessage = True
    ws1.add_data_validation(dv_employment)
    dv_employment.add(f'J2:J{max_data_rows + 1}')
    
    # -------------------------------
    # ستون ۱۱: سابقه کار (1-35)
    # -------------------------------
    dv_experience = DataValidation(
        type="whole",
        operator="between",
        formula1="1",
        formula2="35",
        allow_blank=True,
        showErrorMessage=True,
    )
    dv_experience.error = 'سابقه کار باید عددی بین ۱ تا ۳۵ باشد'
    dv_experience.errorTitle = 'عدد نامعتبر'
    dv_experience.prompt = 'سابقه کار به سال (بین ۱ تا ۳۵)'
    dv_experience.promptTitle = 'سابقه کار'
    dv_experience.showInputMessage = True
    ws1.add_data_validation(dv_experience)
    dv_experience.add(f'K2:K{max_data_rows + 1}')
    
    # -------------------------------
    # ستون ۶: بخش
    # -------------------------------
    # ⚠️ نام بخش‌ها باید از دیتابیس بیاید
    # راه‌حل: یک شیت مخفی با نام بخش‌ها
    try:
        import os
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
        django.setup()
        
        from api.models import Ward
        ward_names = list(Ward.objects.values_list('name', flat=True))
    except Exception as e:
        print(f'⚠️ خطا در خواندن بخش‌ها: {e}')
        ward_names = ['SCU', 'ICU', 'جراحی یک', 'جراحی دو']
    
    if ward_names:
        # نوشتن بخش‌ها در شیت مرجع (ستون E)
        for row_idx, ward_name in enumerate(ward_names, 2):
            cell = ws_refs.cell(row=row_idx, column=5, value=ward_name)
            cell.font = content_font
            cell.alignment = content_align
            cell.border = thin_border
        
        # هدر
        cell = ws_refs.cell(row=1, column=5, value='بخش')
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws_refs.column_dimensions['E'].width = 25
        
        last_ward_row = len(ward_names) + 1
        dv_ward = DataValidation(
            type="list",
            formula1=f"=لیست‌های_مرجع!$E$2:$E${last_ward_row}",
            allow_blank=True,
            showDropDown=False,
        )
        dv_ward.error = 'لطفاً از لیست انتخاب کنید'
        dv_ward.errorTitle = 'بخش نامعتبر'
        dv_ward.prompt = 'بخش را از لیست انتخاب کنید'
        dv_ward.promptTitle = 'بخش'
        dv_ward.showErrorMessage = True
        dv_ward.showInputMessage = True
        ws1.add_data_validation(dv_ward)
        dv_ward.add(f'F2:F{max_data_rows + 1}')
    
    # ============================================================
    # ردیف نمونه
    # ============================================================
    sample_row1 = [
        'ali.olavi',
        '1234567890',
        'علی',
        'علوی',
        'پرستار',
        ward_names[0] if ward_names else 'SCU',
        '',
        'پرستار',
        'سه نوبتی',
        'رسمی',
        5,
        'ali@hospital.ir',
        '12345678',
    ]
    
    for col_idx, value in enumerate(sample_row1, 1):
        cell = ws1.cell(row=2, column=col_idx, value=value)
        cell.font = content_font
        cell.alignment = content_align
        cell.border = thin_border
        cell.fill = example_fill
    
    # کامنت راهنما روی سلول نمونه
    comment = Comment(
        'این ردیف نمونه است — آن را حذف کنید و اطلاعات خود را وارد کنید',
        'سیستم'
    )
    ws1.cell(row=2, column=1).comment = comment
    
    # ============================================================
    # شیت ۲: بخش‌ها
    # ============================================================
    ws2 = wb.create_sheet('بخش‌ها', 2)
    ws2.sheet_view.rightToLeft = True
    
    headers2 = [
        'نام بخش *',
        'نام زیربخش',
        'بخش والد',
        'حداقل صبح *',
        'حداقل عصر *',
        'حداقل شب *',
        'حداقل صبح (تعطیل)',
        'حداقل عصر (تعطیل)',
        'حداقل شب (تعطیل)',
        'کدهای شیفت',
    ]
    widths2 = [18, 18, 15, 14, 14, 14, 18, 18, 18, 25]
    
    for col_idx, header in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws2.column_dimensions[get_column_letter(col_idx)].width = widths2[col_idx - 1]
    
    ws2.row_dimensions[1].height = 35
    
    sample_row2 = ['SCU', '', '', '4', '4', '3', '2', '2', '2', 'M, E, N, H, -']
    for col_idx, value in enumerate(sample_row2, 1):
        cell = ws2.cell(row=2, column=col_idx, value=value)
        cell.font = content_font
        cell.alignment = content_align
        cell.border = thin_border
        cell.fill = example_fill
    
    # Data Validation برای عدد
    for col_letter in ['D', 'E', 'F', 'G', 'H', 'I']:
        dv = DataValidation(
            type="whole",
            operator="between",
            formula1="0",
            formula2="100",
            allow_blank=True,
        )
        ws2.add_data_validation(dv)
        dv.add(f'{col_letter}2:{col_letter}100')
    
    # ============================================================
    # شیت ۳: تعطیلات
    # ============================================================
    ws3 = wb.create_sheet('تعطیلات', 3)
    ws3.sheet_view.rightToLeft = True
    
    headers3 = ['تاریخ * (1405-01-01)', 'نام تعطیلی *', 'سال *']
    widths3 = [25, 25, 12]
    
    for col_idx, header in enumerate(headers3, 1):
        cell = ws3.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws3.column_dimensions[get_column_letter(col_idx)].width = widths3[col_idx - 1]
    
    ws3.row_dimensions[1].height = 35
    
    sample_row3 = ['1405-01-01', 'عید نوروز', '1405']
    for col_idx, value in enumerate(sample_row3, 1):
        cell = ws3.cell(row=2, column=col_idx, value=value)
        cell.font = content_font
        cell.alignment = content_align
        cell.border = thin_border
        cell.fill = example_fill
    
    # ============================================================
    # شیت ۴: کدهای شیفت
    # ============================================================
    ws4 = wb.create_sheet('کدهای_شیفت', 4)
    ws4.sheet_view.rightToLeft = True
    
    headers4 = ['کد *', 'نام نمایشی *', 'فعال']
    widths4 = [10, 20, 10]
    
    for col_idx, header in enumerate(headers4, 1):
        cell = ws4.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws4.column_dimensions[get_column_letter(col_idx)].width = widths4[col_idx - 1]
    
    ws4.row_dimensions[1].height = 30
    
    samples4 = [
        ('M', 'صبح', 'بله'),
        ('E', 'عصر', 'بله'),
        ('N', 'شب', 'بله'),
        ('H', 'مرخصی', 'بله'),
        ('-', 'آف', 'بله'),
    ]
    
    for row_idx, sample in enumerate(samples4, 2):
        for col_idx, value in enumerate(sample, 1):
            cell = ws4.cell(row=row_idx, column=col_idx, value=value)
            cell.font = content_font
            cell.alignment = content_align
            cell.border = thin_border
            cell.fill = example_fill
    
    # Dropdown برای ستون فعال
    dv_active = DataValidation(
        type="list",
        formula1='"بله,خیر"',
        allow_blank=True,
        showDropDown=False,
    )
    ws4.add_data_validation(dv_active)
    dv_active.add('C2:C100')
    
    # ============================================================
    # شیت ۵: راهنما
    # ============================================================
    ws5 = wb.create_sheet('راهنما', 5)
    ws5.sheet_view.rightToLeft = True
    
    guide_lines = [
        ('📖 راهنمای استفاده از فایل', 'title'),
        ('', ''),
        ('🎯 هدف:', 'subtitle'),
        ('آپلود گروهی اطلاعات به سیستم مدیریت شیفت پرستاری', 'text'),
        ('', ''),
        ('📌 شیت‌ها:', 'subtitle'),
        ('• پرسنل: اطلاعات پرستاران، سرپرستاران، سوپروایزرها', 'text'),
        ('• بخش‌ها: بخش‌های بیمارستان', 'text'),
        ('• تعطیلات: تعطیلات رسمی', 'text'),
        ('• کدهای_شیفت: کدهای شیفت کاری', 'text'),
        ('• لیست‌های_مرجع: لیست‌های Dropdown (تغییر ندهید!)', 'text'),
        ('', ''),
        ('✨ ویژگی‌های هوشمند:', 'subtitle'),
        ('• نقش، سمت، نوع شیفت، وضعیت استخدام → Dropdown', 'text'),
        ('• بخش → Dropdown از دیتابیس', 'text'),
        ('• سابقه کار → فقط عدد بین ۱ تا ۳۵', 'text'),
        ('', ''),
        ('⚠️ نکات مهم:', 'subtitle'),
        ('۱. ستون‌های دارای * اجباری هستند', 'text'),
        ('۲. ردیف زرد = نمونه (حذف کنید)', 'text'),
        ('۳. تاریخ: فرمت YYYY-MM-DD (مثل 1405-01-01)', 'text'),
        ('۴. فقط فرمت xlsx', 'text'),
        ('۵. حجم < 5 مگابایت', 'text'),
        ('', ''),
        ('🎨 نکته درباره Dropdown ها:', 'subtitle'),
        ('روی هر سلول که کلیک کنید، یک فلش کوچک سمت راست ظاهر می‌شود', 'text'),
        ('با کلیک روی فلش، لیست گزینه‌ها باز می‌شود', 'text'),
        ('', ''),
        ('❓ اگر لیست Dropdown باز نشد:', 'subtitle'),
        ('۱. ستون‌های بین ردیف ۲ تا ۱۰۰۰ فعال هستند', 'text'),
        ('۲. اگر ردیف جدید اضافه کردید، Dropdown خودکار اعمال می‌شود', 'text'),
        ('۳. اگر کار نکرد، Excel را ببندید و دوباره باز کنید', 'text'),
    ]
    
    ws5.column_dimensions['A'].width = 95
    
    for row_idx, (text, style) in enumerate(guide_lines, 1):
        cell = ws5.cell(row=row_idx, column=1, value=text)
        cell.alignment = Alignment(horizontal='right', vertical='center', wrap_text=True)
        
        if style == 'title':
            cell.font = Font(name='B Nazanin', size=16, bold=True, color='1E40AF')
            ws5.row_dimensions[row_idx].height = 35
        elif style == 'subtitle':
            cell.font = Font(name='B Nazanin', size=13, bold=True, color='B45309')
            ws5.row_dimensions[row_idx].height = 28
        elif style == 'label':
            cell.font = Font(name='B Nazanin', size=11, bold=True, color='1E3A8A')
        else:
            cell.font = Font(name='B Nazanin', size=11)
    
    # ============================================================
    # تنظیم ترتیب شیت‌ها
    # ============================================================
    # ترتیب نهایی: پرسنل، بخش‌ها، تعطیلات، کدهای_شیفت، راهنما، لیست‌های_مرجع
    order = ['پرسنل', 'بخش‌ها', 'تعطیلات', 'کدهای_شیفت', 'راهنما', 'لیست‌های_مرجع']
    wb._sheets = [wb[name] for name in order]
    
    # ============================================================
    # ذخیره
    # ============================================================
    filename = 'نمونه_اطلاعات.xlsx'
    wb.save(filename)
    
    print('=' * 60)
    print(f'✅ فایل "{filename}" ساخته شد!')
    print('=' * 60)
    print()
    print('📋 شیت‌ها:')
    print('   ۱. پرسنل          ← با Dropdown و محدودیت')
    print('   ۲. بخش‌ها')
    print('   ۳. تعطیلات')
    print('   ۴. کدهای_شیفت')
    print('   ۵. راهنما')
    print('   ۶. لیست‌های_مرجع   ← لیست‌های Dropdown')
    print()
    print('✨ ویژگی‌های جدید:')
    print('   • نقش → Dropdown')
    print(f'   • بخش → Dropdown ({len(ward_names)} بخش از دیتابیس)')
    print('   • سمت → Dropdown (18 گزینه)')
    print('   • نوع شیفت → Dropdown (7 گزینه)')
    print('   • وضعیت استخدام → Dropdown (5 گزینه)')
    print('   • سابقه کار → 1 تا 35')
    print()
    print('🎯 فایل را باز کنید و اطلاعات را وارد نمایید.')


if __name__ == '__main__':
    create_sample_excel()