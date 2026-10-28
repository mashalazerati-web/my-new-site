# api/excel_import/ward_importer.py
"""ایمپورت بخش‌ها"""

from django.db import transaction
from api.models import Ward, ShiftCode


def import_wards(worksheet) -> dict:
    result = {
        'total': 0, 'success': 0, 'errors': [],
        'created': 0, 'updated': 0,
    }
    
    headers = {}
    for col_idx in range(1, worksheet.max_column + 1):
        cell = worksheet.cell(row=1, column=col_idx).value
        if cell:
            headers[str(cell).strip()] = col_idx
    
    if 'نام بخش *' not in headers:
        result['errors'].append({'row': 1, 'message': 'ستون "نام بخش *" یافت نشد'})
        return result
    
    for row_idx in range(2, worksheet.max_row + 1):
        row = _read_ward_row(worksheet, row_idx, headers)
        if not row:
            continue
        
        result['total'] += 1
        
        if not row['name']:
            result['errors'].append({'row': row_idx, 'message': 'نام بخش الزامی است'})
            continue
        
        try:
            with transaction.atomic():
                created, updated = _save_ward(row)
                if created:
                    result['created'] += 1
                elif updated:
                    result['updated'] += 1
                result['success'] += 1
        except Exception as e:
            result['errors'].append({'row': row_idx, 'message': str(e)})
    
    return result


def _read_ward_row(worksheet, row_idx, headers):
    def get(name):
        for h in headers:
            if h == name or h.replace(' *', '') == name.replace(' *', ''):
                return worksheet.cell(row=row_idx, column=headers[h]).value
        return None
    
    row = {
        'name': get('نام بخش'),
        'sub_ward_name': get('نام زیربخش'),
        'parent_name': get('بخش والد'),
        'min_staff_morning': get('حداقل صبح'),
        'min_staff_evening': get('حداقل عصر'),
        'min_staff_night': get('حداقل شب'),
        'holiday_morning': get('حداقل صبح (تعطیل)'),
        'holiday_evening': get('حداقل عصر (تعطیل)'),
        'holiday_night': get('حداقل شب (تعطیل)'),
        'shift_codes': get('کدهای شیفت'),
    }
    
    if not row['name']:
        return None
    
    # پاکسازی
    for k in row:
        if isinstance(row[k], str):
            row[k] = row[k].strip()
    
    return row


def _save_ward(row):
    name = str(row['name']).strip()
    
    # بخش والد
    parent = None
    if row['parent_name']:
        parent = Ward.objects.filter(name=str(row['parent_name']).strip()).first()
    
    ward, created = Ward.objects.get_or_create(
        name=name,
        defaults={'parent': parent}
    )
    
    if row['sub_ward_name']:
        ward.sub_ward_name = str(row['sub_ward_name']).strip()
    
    if parent:
        ward.parent = parent
    
    # حداقل پرسنل
    for field, key in [
        ('min_staff_morning', 'min_staff_morning'),
        ('min_staff_evening', 'min_staff_evening'),
        ('min_staff_night', 'min_staff_night'),
        ('holiday_min_staff_morning', 'holiday_morning'),
        ('holiday_min_staff_evening', 'holiday_evening'),
        ('holiday_min_staff_night', 'holiday_night'),
    ]:
        if row.get(key):
            try:
                setattr(ward, field, int(float(row[key])))
            except (ValueError, TypeError):
                pass
    
    ward.save()
    
    # کدهای شیفت
    if row['shift_codes']:
        codes_text = str(row['shift_codes'])
        codes = [c.strip() for c in codes_text.replace('،', ',').split(',') if c.strip()]
        
        # ساخت کدهای شیفت (اگر موجود نبودند)
        shift_objs = []
        for code in codes:
            sc, _ = ShiftCode.objects.get_or_create(
                code=code,
                defaults={'label': code, 'is_active': True}
            )
            shift_objs.append(sc)
        
        ward.active_shift_codes.set(shift_objs)
    
    return (ward if created else None, ward if not created else None)