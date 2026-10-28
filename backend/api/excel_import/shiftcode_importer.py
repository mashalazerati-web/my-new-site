# api/excel_import/shiftcode_importer.py
"""ایمپورت کدهای شیفت"""

from django.db import transaction
from api.models import ShiftCode


def import_shift_codes(worksheet) -> dict:
    result = {'total': 0, 'success': 0, 'errors': [], 'created': 0, 'updated': 0}
    
    headers = {}
    for col_idx in range(1, worksheet.max_column + 1):
        cell = worksheet.cell(row=1, column=col_idx).value
        if cell:
            headers[str(cell).strip()] = col_idx
    
    col_code = None
    col_label = None
    col_active = None
    
    for h in headers:
        if 'کد' in h:
            col_code = headers[h]
        elif 'نام' in h or 'نمایشی' in h:
            col_label = headers[h]
        elif 'فعال' in h:
            col_active = headers[h]
    
    if not col_code:
        result['errors'].append({'row': 1, 'message': 'ستون "کد" الزامی است'})
        return result
    
    for row_idx in range(2, worksheet.max_row + 1):
        code_val = worksheet.cell(row=row_idx, column=col_code).value
        label_val = worksheet.cell(row=row_idx, column=col_label).value if col_label else None
        active_val = worksheet.cell(row=row_idx, column=col_active).value if col_active else None
        
        if not code_val:
            continue
        
        result['total'] += 1
        
        code = str(code_val).strip()
        label = str(label_val).strip() if label_val else code
        
        # فعال؟
        is_active = True
        if active_val is not None:
            text = str(active_val).strip().lower()
            is_active = text in ('1', 'true', 'بله', 'yes', 'y', 'فعال')
        
        try:
            with transaction.atomic():
                shift_code, created = ShiftCode.objects.update_or_create(
                    code=code,
                    defaults={'label': label, 'is_active': is_active}
                )
                if created:
                    result['created'] += 1
                else:
                    result['updated'] += 1
                result['success'] += 1
        except Exception as e:
            result['errors'].append({'row': row_idx, 'message': str(e)})
    
    return result