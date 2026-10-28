# test_shift_type.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Ward, Profile
from ai_module.services import ContextBuilder


def find_ward_with_staff():
    """پیدا کردن بخشی که پرسنل دارد"""
    wards = Ward.objects.all()
    for w in wards:
        count = Profile.objects.filter(ward=w).exclude(role__in=['head', 'admin', 'supervisor']).count()
        if count > 0:
            return w, count
    return None, 0


def main():
    # پیدا کردن بخش با پرسنل
    print("=" * 60)
    print("همه بخش‌ها:")
    for w in Ward.objects.all():
        count = Profile.objects.filter(ward=w).exclude(role__in=['head', 'admin', 'supervisor']).count()
        print(f"  {w.id}: {w.name} → {count} پرسنل")
    print()

    ward, staff_count = find_ward_with_staff()
    if not ward:
        print("❌ هیچ بخشی با پرسنل یافت نشد!")
        return

    print("=" * 60)
    print(f"بخش انتخابی: {ward.name} (id={ward.id}, {staff_count} پرسنل)")
    print("=" * 60)

    # پروفایل‌های بخش
    profiles = Profile.objects.filter(ward=ward).exclude(role__in=['head', 'admin', 'supervisor'])
    print(f"\nپرسنل:")
    for p in profiles:
        name = f"{p.user.first_name} {p.user.last_name}"
        print(f"  {name[:25]:<27} | shift_type={p.shift_type:<20} | position={p.position} | role={p.role}")

    # Context
    print()
    ctx = ContextBuilder.build_for_main(ward, 1405, 8)
    print(f"Context staff ({len(ctx.staff)}):")
    for sid, s in ctx.staff.items():
        print(f"  {s.name[:25]:<27} | shift_type={s.shift_type}")


if __name__ == '__main__':
    main()