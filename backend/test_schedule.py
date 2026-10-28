# backend/test_full.py
"""
تست جامع: پرامپت + توزیع عادلانه + قوانین
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ai_module.services import ContextBuilder, ScheduleService
from ai_module.prompt import PromptInterpreter
from ai_module.rules import get_rule_registry
from api.models import Ward
import statistics


def run_test():
    ward = Ward.objects.get(id=143)  # Ward قلب (10 پرسنل)
    year, month = 1405, 7
    
    context = ContextBuilder.build_for_main(ward, year, month)
    staff_list = list(context.staff.values())
    
    print("=" * 75)
    print(f"🏥 بخش: {ward.name} — {len(staff_list)} پرستار")
    print("=" * 75)
    
    # لیست پرسنل
    for s in staff_list:
        print(f"  id={s.id}: {s.name}")
    
    # ✅ پرامپت ترکیبی
    name1 = staff_list[0].last_name  # غیاثی نوش آبادی
    name2 = staff_list[1].last_name  # مشیدی
    
    prompt = (
        f"خانم {name1} از روز 5 تا 10 صبح باشد. "
        f"خانم {name2} از روز 15 تا 20 شب باشد. "
        f"حداکثر 2 شب متوالی"
    )
    
    print(f"\n📝 پرامپت:\n   {prompt}")
    
    # تفسیر
    interpreter = PromptInterpreter(context)
    interp = interpreter.interpret(prompt)
    
    print(f"\n🔍 تفسیر:")
    print(f"   نرخ تطبیق: {interp.match_rate:.1f}% ({interp.matched_sentences}/{interp.total_sentences})")
    print(f"   قوانین تولیدشده: {len(interp.rules)}")
    for rule in interp.rules:
        print(f"     ✅ {rule.code}: {rule.params}")
    
    if interp.unmatched_sentences:
        print(f"   ⚠️ تطبیق‌نشده:")
        for s in interp.unmatched_sentences:
            print(f"     ❌ {s}")
    
    # قوانین پایه + پرامپت
    registry = get_rule_registry()
    base_rules = [
        registry.create('max_consecutive_nights', max_nights=2),
        registry.create('no_work_after_night'),
        registry.create('minimum_staff_coverage'),
        registry.create('fair_shift_distribution', min_shift_per_staff=15, max_shift_per_staff=45),
    ]
    
    all_rules = base_rules + interp.rules
    
    # تولید
    print(f"\n⏳ در حال تولید...")
    service = ScheduleService()
    result = service.generate(context, all_rules)
    schedule = result['schedule']
    
    print(f"✅ تولید شد در {result['stats']['elapsed_seconds']} ثانیه")
    
    # ✅ چک پرامپت ۱: آیا پرستار ۱ در روز ۵-۱۰ صبح گرفته؟
    print("\n" + "=" * 75)
    print("🎯 چک پرامپت‌ها:")
    print("=" * 75)
    
    target1 = next(r for r in schedule if r['staff_id'] == staff_list[0].id)
    target2 = next(r for r in schedule if r['staff_id'] == staff_list[1].id)
    
    # پرامپت ۱
    days_5_10 = [d for d in target1['days'] if 5 <= d['day'] <= 10]
    matched_1 = sum(1 for d in days_5_10 if d['shift'] == 'M')
    print(f"\n📌 پرامپت ۱: {target1['staff_name']} از روز ۵ تا ۱۰ صبح")
    print(f"   نتیجه: {matched_1}/6 روز صبح گرفته")
    for d in days_5_10:
        status = "✅" if d['shift'] == 'M' else "❌"
        print(f"     {status} روز {d['day']}: {d['shift']}")
    
    # پرامپت ۲
    days_15_20 = [d for d in target2['days'] if 15 <= d['day'] <= 20]
    matched_2 = sum(1 for d in days_15_20 if 'N' in d['shift'])
    print(f"\n📌 پرامپت ۲: {target2['staff_name']} از روز ۱۵ تا ۲۰ شب")
    print(f"   نتیجه: {matched_2}/6 روز شب گرفته")
    for d in days_15_20:
        status = "✅" if 'N' in d['shift'] else "❌"
        print(f"     {status} روز {d['day']}: {d['shift']}")
    
    # ✅ توزیع عادلانه
    print("\n" + "=" * 75)
    print("📊 توزیع عادلانه:")
    print("=" * 75)
    
    nights = [r['total_n'] for r in schedule]
    offs = [r['total_off'] + r['total_off_after_night'] for r in schedule]
    shifts = [r['total_m'] + r['total_e'] + r['total_n'] for r in schedule]
    
    print(f"شب‌ها:   min={min(nights):2d}, max={max(nights):2d}, diff={max(nights)-min(nights)}")
    print(f"آف‌ها:   min={min(offs):2d}, max={max(offs):2d}, diff={max(offs)-min(offs)}")
    print(f"کل:     min={min(shifts):2d}, max={max(shifts):2d}, diff={max(shifts)-min(shifts)}")
    
    print(f"\nمیانگین شب: {statistics.mean(nights):.1f} (±{statistics.stdev(nights):.2f})")
    print(f"میانگین آف: {statistics.mean(offs):.1f} (±{statistics.stdev(offs):.2f})")
    
    # ✅ گزارش نهایی
    print("\n" + "=" * 75)
    print("📋 گزارش قوانین:")
    print("=" * 75)
    
    report = result['report']
    print(f"امتیاز کلی: {report['overall_score']}")
    print(f"نقض‌های بحرانی: {report['critical_violations']}")
    print(f"نقض‌های مهم: {report['high_violations']}")
    print(f"کل نقض‌ها: {report['total_violations']}")
    
    for res in report['results']:
        status = "✅" if res['violation_count'] == 0 else "⚠️"
        print(f"  {status} {res['rule_code']:35s} نقض={res['violation_count']:3d}, امتیاز={res['score']:.1f}")
    
    # ✅ جدول کامل
    print("\n" + "=" * 75)
    print("📊 جدول نهایی:")
    print("=" * 75)
    print(f"{'نام':<28s} {'شب':>4s} {'صبح':>5s} {'عصر':>5s} {'کل':>5s} {'آف':>4s} {'لانگ':>5s}")
    print("-" * 75)
    for r in sorted(schedule, key=lambda x: x['staff_name']):
        off = r['total_off'] + r['total_off_after_night']
        total = r['total_m'] + r['total_e'] + r['total_n']
        name = r['staff_name'][:26]
        print(f"{name:<28s} {r['total_n']:>4d} {r['total_m']:>5d} {r['total_e']:>5d} {total:>5d} {off:>4d} {r['total_longs']:>5d}")

    print("\n" + "=" * 75)
    print("👥 تعادل تجربه در شب‌ها:")
    print("=" * 75)
    
    ward_avg = sum(s.work_experience for s in context.staff.values()) / len(context.staff)
    print(f"میانگین سابقه کل بخش: {ward_avg:.1f} سال\n")
    
    for day in range(1, min(11, context.days_in_month + 1)):
        night_exps = []
        for r in result['schedule']:
            day_shift = next((d['shift'] for d in r['days'] if d['day'] == day), '')
            if 'N' in day_shift:
                staff_info = context.staff.get(r['staff_id'])
                if staff_info:
                    night_exps.append(staff_info.work_experience)
        
        if night_exps:
            night_avg = sum(night_exps) / len(night_exps)
            diff = abs(night_avg - ward_avg)
            status = "✅" if diff < 2 else ("🟡" if diff < 3 else "⚠️")
            print(f"  {status} روز {day:2d}: شب‌کارها={len(night_exps)}, "
                  f"میانگین سابقه={night_avg:.1f}, اختلاف={diff:.1f}")


if __name__ == '__main__':
    run_test()