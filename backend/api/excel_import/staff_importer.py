# api/excel_import/staff_importer.py
"""ایمپورت پرسنل"""

from django.contrib.auth.models import User
from django.db import transaction
from api.models import Profile, Ward


ROLE_MAP = {
    'پرستار': 'staff', 'staff': 'staff',
    'سرپرستار': 'head', 'head': 'head',
    'سوپروایزر': 'supervisor', 'supervisor': 'supervisor',
    'مترون': 'admin', 'admin': 'admin',
    'مدیر': 'admin', 'مدیر پرستاری': 'admin',
}

POSITION_MAP = {
    'مترون': '1', 'جانشین مترون': '2', 'سوپروایزر بالینی': '3',
    'سرپرستار': '4', 'سرپرستار/ مسئول بخش': '4',
    'سوپروایزر بخش': '5',
    'پرستار': '8', 'ماما': '9', 'بهیار': '11',
    'کارشناس/کاردان بخش': '12', 'خدمات': '13',
}

SHIFT_TYPE_MAP = {
    'سه نوبتی': 'سه_نوبتی', 'سه_نوبتی': 'سه_نوبتی',
    'ثابت صبح': 'ثابت_صبح', 'ثابت_صبح': 'ثابت_صبح',
    'ثابت عصر': 'ثابت_عصر', 'ثابت_عصر': 'ثابت_عصر',
    'ثابت شب': 'ثابت_شب', 'ثابت_شب': 'ثابت_شب',
}

EMPLOYMENT_MAP = {
    'رسمی': 'رسمی', 'پیمانی': 'پیمانی', 'قراردادی': 'قراردادی',
    'شرکتی': 'شرکتی', 'طرحی': 'طرحی',
}


def import_staff(worksheet) -> dict:
    """ایمپورت پرسنل از worksheet"""
    result = {
        'total': 0, 'success': 0, 'errors': [], 'warnings': [],
        'created': 0, 'updated': 0,
    }
    
    # خواندن هدرها
    headers = {}
    for col_idx in range(1, worksheet.max_column + 1):
        cell = worksheet.cell(row=1, column=col_idx).value
        if cell:
            headers[str(cell).strip()] = col_idx
    
    # چک ستون‌های الزامی
    required = ['نام کاربری *', 'نام *', 'نام خانوادگی *', 'نقش *', 'بخش *']
    for col in required:
        if col not in headers:
            result['errors'].append({
                'row': 1,
                'message': f'ستون "{col}" یافت نشد',
            })
            return result
    
    # پردازش ردیف‌ها
    for row_idx in range(2, worksheet.max_row + 1):
        row = _read_staff_row(worksheet, row_idx, headers)
        
        if not row:  # ردیف خالی
            continue
        
        result['total'] += 1
        
        # اعتبارسنجی
        errors = _validate_staff_row(row_idx, row)
        if errors:
            result['errors'].extend(errors)
            continue
        
        # ذخیره
        try:
            with transaction.atomic():
                created, updated = _save_staff(row)
                if created:
                    result['created'] += 1
                elif updated:
                    result['updated'] += 1
                result['success'] += 1
        except Exception as e:
            result['errors'].append({
                'row': row_idx,
                'message': f'خطا در ذخیره: {str(e)}',
            })
    
    return result


def _read_staff_row(worksheet, row_idx, headers) -> dict:
    """خواندن یک ردیف"""
    def get(col_name):
        col_key = None
        for h in headers:
            if h == col_name or h.replace(' *', '') == col_name.replace(' *', ''):
                col_key = h
                break
        if not col_key:
            return None
        val = worksheet.cell(row=row_idx, column=headers[col_key]).value
        if val is None:
            return None
        return str(val).strip() if isinstance(val, str) else val
    
    row = {
        'username': get('نام کاربری'),
        'national_id': get('کد ملی'),
        'first_name': get('نام'),
        'last_name': get('نام خانوادگی'),
        'role': get('نقش'),
        'ward': get('بخش'),
        'additional_wards': get('بخش‌های اضافی'),
        'position': get('سمت'),
        'shift_type': get('نوع شیفت'),
        'employment_status': get('وضعیت استخدام'),
        'work_experience': get('سابقه کار'),
        'email': get('ایمیل'),
        'password': get('رمز عبور موقت'),
    }
    
    # ردیف خالی؟
    if not any([row['username'], row['first_name'], row['last_name']]):
        return None
    
    return row


def _validate_staff_row(row_idx, row) -> list:
    """اعتبارسنجی"""
    errors = []
    
    if not row['username']:
        errors.append({'row': row_idx, 'message': 'نام کاربری الزامی است'})
    
    if not row['first_name']:
        errors.append({'row': row_idx, 'message': 'نام الزامی است'})
    
    if not row['last_name']:
        errors.append({'row': row_idx, 'message': 'نام خانوادگی الزامی است'})
    
    if not row['role']:
        errors.append({'row': row_idx, 'message': 'نقش الزامی است'})
    elif str(row['role']).strip() not in ROLE_MAP:
        errors.append({
            'row': row_idx,
            'message': f'نقش "{row["role"]}" معتبر نیست. مقادیر مجاز: پرستار، سرپرستار، سوپروایزر، مترون',
        })
    
    if not row['ward']:
        errors.append({'row': row_idx, 'message': 'بخش الزامی است'})
    elif not Ward.objects.filter(name=str(row['ward']).strip()).exists():
        errors.append({
            'row': row_idx,
            'message': f'بخش "{row["ward"]}" یافت نشد',
        })
    
    return errors


def _save_staff(row) -> tuple:
    """ذخیره یک پرسنل"""
    username = str(row['username']).strip()
    role = ROLE_MAP.get(str(row['role']).strip(), 'staff')
    ward = Ward.objects.filter(name=str(row['ward']).strip()).first()
    
    if not ward:
        raise Exception('بخش یافت نشد')
    
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': str(row['first_name']).strip(),
            'last_name': str(row['last_name']).strip(),
            'email': str(row['email']).strip() if row['email'] else '',
        }
    )
    
    # به‌روزرسانی
    user.first_name = str(row['first_name']).strip()
    user.last_name = str(row['last_name']).strip()
    if row['email']:
        user.email = str(row['email']).strip()
    
    # رمز
    if created:
        password = str(row['password']).strip() if row['password'] else '12345678'
        user.set_password(password)
    elif row['password']:
        user.set_password(str(row['password']).strip())
    
    user.save()
    
    # پروفایل
    profile, profile_created = Profile.objects.get_or_create(
        user=user,
        defaults={'role': role, 'ward': ward}
    )
    
    profile.role = role
    profile.ward = ward
    
    if row['position']:
        profile.position = POSITION_MAP.get(str(row['position']).strip(), '8')
    
    if row['shift_type']:
        profile.shift_type = SHIFT_TYPE_MAP.get(str(row['shift_type']).strip(), 'سه_نوبتی')
    
    if row['employment_status']:
        profile.employment_status = EMPLOYMENT_MAP.get(str(row['employment_status']).strip(), 'رسمی')
    
    if row['work_experience']:
        try:
            profile.work_experience = int(float(row['work_experience']))
        except (ValueError, TypeError):
            profile.work_experience = 0
    
    profile.save()
    
    # بخش‌های اضافی
    if row['additional_wards']:
        additional = str(row['additional_wards'])
        names = [w.strip() for w in additional.replace('،', ',').split(',') if w.strip()]
        wards = Ward.objects.filter(name__in=names)
        profile.additional_wards.set(wards)
    
    return (profile if created else None, profile if not created else None)