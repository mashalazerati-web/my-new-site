# api/excel_import/holiday_importer.py
"""ایمپورت تعطیلات"""

from django.db import transaction
from api.models import Holiday


def import_holidays(worksheet) -> dict:
    result = {'total': 0, 'success': 0, 'errors': [], 'created': 0, 'updated': 0}
    
    headers = {}
    for col_idx in range(1, worksheet.max_column + 1):
        cell = worksheet.cell(row=1, column=col_idx).value
        if cell:
            headers[str(cell).strip()] = col_idx
    
    # ستون‌ها
    col_date = None
    col_name = None
    col_year = None
    
    for h in headers:
        if 'تاریخ' in h:
            col_date = headers[h]
        elif 'نام' in h or 'عنوان' in h:
            col_name = headers[h]
        elif 'سال' in h:
            col_year = headers[h]
    
    if not col_date or not col_name:
        result['errors'].append({'row': 1, 'message': 'ستون‌های تاریخ و نام تعطیلی الزامی هستند'})
        return result
    
    for row_idx in range(2, worksheet.max_row + 1):
        date_val = worksheet.cell(row=row_idx, column=col_date).value
        name_val = worksheet.cell(row=row_idx, column=col_name).value
        year_val = worksheet.cell(row=row_idx, column=col_year).value if col_year else None
        
        if not date_val and not name_val:
            continue
        
        result['total'] += 1
        
        date_str = str(date_val).strip() if date_val else ''
        name_str = str(name_val).strip() if name_val else ''
        
        # تبدیل تاریخ اگر datetime است
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime('%Y-%m-%d')
        
        if not date_str or not name_str:
            result['errors'].append({'row': row_idx, 'message': 'تاریخ و نام الزامی هستند'})
            continue
        
        try:
            year = int(float(year_val)) if year_val else int(date_str.split('-')[0])
        except (ValueError, IndexError):
            year = 1405
        
        try:
            with transaction.atomic():
                holiday, created = Holiday.objects.update_or_create(
                    date=date_str,
                    defaults={'name': name_str, 'year': year}
                )
                if created:
                    result['created'] += 1
                else:
                    result['updated'] += 1
                result['success'] += 1
        except Exception as e:
            result['errors'].append({'row': row_idx, 'message': str(e)})
    
    return result