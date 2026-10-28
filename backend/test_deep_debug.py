# test_deep_debug.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Ward
from ai_module.services import ContextBuilder, ScheduleService
from ai_module.rules import get_rule_registry


def main():
    # بخش اورژانس
    ward = Ward.objects.get(id=109)
    print(f"بخش: {ward.name}")
    
    # Context
    ctx = ContextBuilder.build_for_main(ward, 1405, 8)
    print(f"پرسنل: {len(ctx.staff)}")
    
    # قوانین
    registry = get_rule_registry()
    rules = [
        registry.create('max_consecutive_nights', max_nights=2),
        registry.create('no_work_after_night'),
        registry.create('minimum_staff_coverage'),
        registry.create('fair_shift_distribution',
                        min_shift_per_staff=15,
                        max_shift_per_staff=45),
    ]
    
    # تولید
    service = ScheduleService()
    result = service.generate(ctx, rules)
    
    # گزارش
    print()
    print("=" * 80)
    print("گزارش پرسنل:")
    print("=" * 80)
    print(f"{'نام':<25} {'M':>4} {'E':>4} {'N':>4} {'H':>4} {'آف':>4} {'لانگ':>5}")
    print("-" * 80)
    
    zero_shifts = []
    high_shifts = []
    
    for s in result['schedule']:
        total = s['total_m'] + s['total_e'] + s['total_n']
        print(f"{s['staff_name'][:24]:<25} {s['total_m']:>4} {s['total_e']:>4} {s['total_n']:>4} {s['total_h']:>4} {s['total_off']:>4} {s['total_longs']:>5}")
        
        if total == 0:
            zero_shifts.append(s['staff_name'])
        if s['total_n'] >= 8:
            high_shifts.append((s['staff_name'], s['total_n']))
    
    print()
    print("=" * 80)
    print(f"پرسنل با صفر شیفت ({len(zero_shifts)}):")
    for name in zero_shifts:
        print(f"  ❌ {name}")
    
    print()
    print(f"پرسنل با ۸+ شب ({len(high_shifts)}):")
    for name, n in high_shifts:
        print(f"  🔴 {name}: {n} شب")
    
    # بررسی قوانین روی یک پرسنل با صفر شیفت
    if zero_shifts:
        print()
        print("=" * 80)
        print("چرا پرسنل اول صفر شیفت گرفته؟")
        print("=" * 80)
        
        # پیدا کردن staff_id
        first_zero_name = zero_shifts[0]
        first_zero_id = None
        for sid, s in ctx.staff.items():
            if s.name == first_zero_name:
                first_zero_id = sid
                break
        
        if first_zero_id:
            # چک Hard rules برای روز ۱، شیفت N
            from ai_module.rules.violations import RuleResult
            passes, violation = service._check_hard_rules(
                ctx, {}, first_zero_id, 1, 'N', 
                [r for r in rules if r.category in ('hard', 'legal')],
                [r for r in rules if r.category == 'soft']
            )
            print(f"  چک Hard برای {first_zero_name} روز ۱، شیفت N:")
            print(f"    Passes: {passes}")
            print(f"    Violation: {violation}")
    
    # چرا شب‌ها ناعادلانه؟
    print()
    print("=" * 80)
    print("چرا شب‌ها ناعادلانه توزیع شده؟")
    print("=" * 80)
    
    # نگاه کن به روز اول
    first_day_shifts = {}
    for s in result['schedule']:
        day1 = s['days'][0]['shift']
        first_day_shifts[s['staff_name']] = day1
    
    print("روز اول:")
    for name, shift in first_day_shifts.items():
        print(f"  {name[:25]:<27} → {shift}")


if __name__ == '__main__':
    main()