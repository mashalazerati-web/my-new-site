# ai_module/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from api.models import Ward, FinalSchedule, Profile, ShiftCode, Holiday, ShiftRequest, DraftSchedule
from .models import AIRule, AIPrompt, AISchedule, SpecialScheduleConfig
from .adaptive_scheduler import AdaptiveScheduler
from .ai_engine_ortools import ORToolsShiftSchedulingEngine


# ==========================================================
# ثابت‌ها
# ==========================================================
ALL_SCHEDULE_TYPES = ['main', 'oncall', 'crisis', 'assistant']

SCHEDULE_TYPE_LABELS = {
    'main': 'اصلی',
    'oncall': 'آنکالی',
    'crisis': 'بحران',
    'assistant': 'کمک پرستار',
}

# ✅ انواعی که نیاز به SpecialScheduleConfig دارن
DEPENDENT_SCHEDULE_TYPES = ['oncall', 'crisis', 'assistant']


# ==========================================================
# ۱. ویو مدیریت قوانین
# ==========================================================
class AIRuleListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        schedule_type = request.query_params.get('schedule_type', 'main')
        rules = AIRule.objects.filter(schedule_type=schedule_type).order_by('-created_at')
        data = []
        for rule in rules:
            data.append({
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'is_active': rule.is_active,
                'schedule_type': rule.schedule_type,
            })
        return Response(data, status=status.HTTP_200_OK)


class AIRuleToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        rule_id = request.data.get('rule_id')
        is_active = request.data.get('is_active')
        if rule_id is None or is_active is None:
            return Response({'error': 'شناسه قانون و وضعیت الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rule = AIRule.objects.get(id=rule_id)
            rule.is_active = is_active
            rule.save()
            return Response({'message': f'قانون "{rule.name}" به روزرسانی شد.'}, status=status.HTTP_200_OK)
        except AIRule.DoesNotExist:
            return Response({'error': 'قانون یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)


# ==========================================================
# ویو دریافت لیست بخش‌های سرپرستار
# ==========================================================
class AIGetWardsView(APIView):
    """
    دریافت لیست بخش‌هایی که سرپرستار می‌تواند برنامه بنویسد.
    شامل بخش اصلی + بخش‌های زیرمجموعه.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {'error': 'پروفایل کاربر یافت نشد.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ✅ بخش‌های قابل دسترسی برای هر نقش
        if profile.role == 'head':
            if profile.ward:
                wards = [profile.ward] + list(profile.ward.get_sub_wards())
            else:
                wards = []

        elif profile.role == 'admin':
            wards = list(Ward.objects.all())

        elif profile.role == 'supervisor':
            wards = list(request.user.supervised_wards.all())

        else:
            wards = []

        # ✅ ساخت نتیجه
        result = []
        for ward in wards:
            has_requests = ShiftRequest.objects.filter(ward=ward).exists()
            has_drafts = DraftSchedule.objects.filter(ward=ward).exists()

            staff_count = Profile.objects.filter(
                ward=ward, role='staff'
            ).count()

            result.append({
                'id': ward.id,
                'name': ward.name,
                'staff_count': staff_count,
                'has_requests': has_requests,
                'has_drafts': has_drafts,
                'head_name': ward.get_head_name(),
                'is_sub': ward.parent is not None,
                'parent_name': ward.parent.name if ward.parent else None,
            })

        return Response(result, status=status.HTTP_200_OK)


# ==========================================================
# ویو دریافت تنظیمات چینش آنکالی/بحران/کمک پرستار
# ==========================================================
class AIGetSpecialConfigView(APIView):
    """
    دریافت تنظیمات چینش استاندارد آنکالی/بحران/کمک پرستار برای یک بخش.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ward_id = request.query_params.get('ward_id')
        schedule_type = request.query_params.get('schedule_type', 'oncall')

        if not ward_id:
            return Response({'error': 'شناسه بخش الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ شامل assistant
        if schedule_type not in DEPENDENT_SCHEDULE_TYPES:
            return Response(
                {'error': 'فقط برنامه‌های آنکالی، بحران و کمک پرستار تنظیمات اختصاصی دارند.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return Response({'error': 'بخش مورد نظر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        config = SpecialScheduleConfig.objects.filter(
            ward=ward, schedule_type=schedule_type
        ).first()

        if not config:
            # ✅ پیش‌فرض
            if schedule_type == 'assistant':
                default_m = default_e = default_n = 1
            else:
                default_m = ward.min_staff_morning
                default_e = ward.min_staff_evening
                default_n = ward.min_staff_night

            default_holiday_m = ward.holiday_min_staff_morning
            default_holiday_e = ward.holiday_min_staff_evening
            default_holiday_n = ward.holiday_min_staff_night

            if schedule_type == 'assistant':
                default_holiday_m = default_holiday_e = default_holiday_n = 1

            return Response({
                'exists': False,
                'message': f'تنظیمات چینش {schedule_type} برای این بخش تعریف نشده است.',
                'ward_id': ward.id,
                'ward_name': ward.name,
                'schedule_type': schedule_type,
                'min_staff_morning': default_m,
                'min_staff_evening': default_e,
                'min_staff_night': default_n,
                'holiday_min_staff_morning': default_holiday_m,
                'holiday_min_staff_evening': default_holiday_e,
                'holiday_min_staff_night': default_holiday_n,
                'description': '',
            }, status=status.HTTP_200_OK)

        return Response({
            'exists': True,
            'id': config.id,
            'ward_id': ward.id,
            'ward_name': ward.name,
            'schedule_type': config.schedule_type,
            'min_staff_morning': config.min_staff_morning,
            'min_staff_evening': config.min_staff_evening,
            'min_staff_night': config.min_staff_night,
            'holiday_min_staff_morning': config.holiday_min_staff_morning,
            'holiday_min_staff_evening': config.holiday_min_staff_evening,
            'holiday_min_staff_night': config.holiday_min_staff_night,
            'description': config.description,
        }, status=status.HTTP_200_OK)


# ==========================================================
# ۲. ویو تولید برنامه (با پشتیبانی کامل از پرامپت و قوانین)
# ==========================================================
from ai_module.services import ContextBuilder, ScheduleService
from ai_module.prompt import PromptInterpreter
from ai_module.rules import get_rule_registry


class AIGenerateScheduleView(APIView):
    """
    تولید برنامه با Rule Engine + Prompt Interpreter + Schedule Service
    - قوانین پیش‌فرض همیشه فعال هستند
    - قوانین پرامپت به‌صورت داینامیک اضافه می‌شوند
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # ============================================================
        # ۱. اعتبارسنجی ورودی
        # ============================================================
        ward_id = request.data.get('ward_id')
        year = request.data.get('year')
        month = request.data.get('month')
        schedule_type = request.data.get('schedule_type', 'main')
        prompt = request.data.get('prompt', '').strip()

        if not ward_id or not year or not month:
            return Response(
                {'error': 'شناسه بخش، سال و ماه الزامی است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if schedule_type not in ['main', 'oncall', 'crisis', 'assistant']:
            return Response(
                {'error': 'نوع برنامه نامعتبر است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return Response(
                {'error': 'بخش مورد نظر یافت نشد.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ============================================================
        # ۲. چک‌های Workflow
        # ============================================================
        from api.workflow import WorkflowEngine

        can_gen, error_msg, missing_prereq = WorkflowEngine.can_generate(
            ward, int(year), int(month), schedule_type
        )

        if not can_gen:
            return Response({
                'error': error_msg,
                'missing_prerequisite': missing_prereq,
            }, status=status.HTTP_400_BAD_REQUEST)

        # ============================================================
        # ۳. برای oncall/crisis/assistant: چک تنظیمات
        # ============================================================
        DEPENDENT_SCHEDULE_TYPES = ['oncall', 'crisis', 'assistant']
        if schedule_type in DEPENDENT_SCHEDULE_TYPES:
            special_config = SpecialScheduleConfig.objects.filter(
                ward=ward, schedule_type=schedule_type
            ).first()

            if not special_config:
                type_label = {
                    'oncall': 'آنکالی',
                    'crisis': 'بحران',
                    'assistant': 'کمک پرستار',
                }.get(schedule_type, schedule_type)

                return Response({
                    'error': f'تنظیمات چینش استاندارد {type_label} تعریف نشده است.',
                }, status=status.HTTP_400_BAD_REQUEST)

        # ============================================================
        # ۴. ساخت Context
        # ============================================================
        try:
            if schedule_type == 'main':
                context = ContextBuilder.build_for_main(
                    ward=ward,
                    year=int(year),
                    month=int(month),
                )

            elif schedule_type == 'assistant':
                context = ContextBuilder.build_for_assistant(
                    ward=ward,
                    year=int(year),
                    month=int(month),
                )

            else:
                # برای oncall/crisis: main_schedule را بارگذاری کن
                main_schedule_data = ContextBuilder.extract_main_schedule_from_final(
                    ward=ward,
                    year=int(year),
                    month=int(month),
                )
                main_schedule_status = ContextBuilder.get_main_schedule_status(
                    ward=ward,
                    year=int(year),
                    month=int(month),
                )

                main_ai = AISchedule.objects.filter(
                    ward=ward,
                    year=int(year),
                    month=int(month),
                    schedule_type='main',
                ).first()

                if schedule_type == 'oncall':
                    context = ContextBuilder.build_for_oncall(
                        ward=ward,
                        year=int(year),
                        month=int(month),
                        main_schedule_data=main_schedule_data,
                        main_schedule_status=main_schedule_status,
                        main_schedule_id=main_ai.id if main_ai else None,
                    )
                else:
                    context = ContextBuilder.build_for_crisis(
                        ward=ward,
                        year=int(year),
                        month=int(month),
                        main_schedule_data=main_schedule_data,
                        main_schedule_status=main_schedule_status,
                        main_schedule_id=main_ai.id if main_ai else None,
                    )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': f'خطا در ساخت Context: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ============================================================
        # ۵. بارگذاری قوانین پیش‌فرض (همیشه فعال)
        # ============================================================
        registry = get_rule_registry()

        # ✅ قوانین پیش‌فرض — همیشه اعمال می‌شوند
        base_rules = [
            registry.create('max_consecutive_nights', max_nights=2),
            registry.create('no_work_after_night'),
            registry.create('minimum_staff_coverage'),
            registry.create('fair_shift_distribution',
                            min_shift_per_staff=15,
                            max_shift_per_staff=45),
        ]

        # ============================================================
        # ۶. تفسیر پرامپت
        # ============================================================
        prompt_rules = []
        prompt_interpretation = None

        if prompt:
            try:
                interpreter = PromptInterpreter(context)
                interp_result = interpreter.interpret(prompt)

                prompt_rules = interp_result.rules
                prompt_interpretation = interp_result.to_dict()

                print(f"✅ پرامپت: {interp_result.matched_sentences}/"
                      f"{interp_result.total_sentences} "
                      f"({interp_result.match_rate:.0f}%)")
                print(f"   قوانین: {len(prompt_rules)}")

            except Exception as e:
                print(f"⚠️ خطا در تفسیر پرامپت: {e}")
                import traceback
                traceback.print_exc()

        all_rules = base_rules + prompt_rules

        # ============================================================
        # ۷. تولید برنامه
        # ============================================================
        try:
            service = ScheduleService()
            result = service.generate(
                context=context,
                rules=all_rules,
                max_iterations=3,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': f'خطا در تولید برنامه: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ============================================================
        # ۸. ذخیره در AISchedule
        # ============================================================
        try:
            prompt_obj = None
            if prompt:
                prompt_obj = AIPrompt.objects.create(
                    user=request.user,
                    prompt_text=prompt,
                )

            ai_generated_data = {
                'ward_id': ward.id,
                'ward_name': ward.name,
                'year': int(year),
                'month': int(month),
                'schedule_type': schedule_type,
                'schedule_data': result['schedule'],
                'report': result['report'],
                'stats': result['stats'],
                'prompt': prompt,
                'prompt_interpretation': prompt_interpretation,
                'active_rules': [r.code for r in base_rules],   # ✅ کد قوانین
                'prompt_rules': [r.code for r in prompt_rules],
                'solver': 'greedy_rule_based',
            }

            ai_schedule, created = AISchedule.objects.update_or_create(
                ward=ward,
                year=int(year),
                month=int(month),
                schedule_type=schedule_type,
                defaults={
                    'status': 'generated',
                    'ai_generated_data': ai_generated_data,
                    'related_prompt': prompt_obj,
                },
            )

            type_label = {
                'main': 'اصلی',
                'oncall': 'آنکالی',
                'crisis': 'بحران',
                'assistant': 'کمک پرستار',
            }.get(schedule_type, schedule_type)

            return Response({
                'message': f'برنامه {type_label} با موفقیت تولید شد.',
                'schedule_id': ai_schedule.id,
                'schedule_type': schedule_type,
                'stats': result['stats'],
                'report': result['report'],
                'prompt_interpretation': prompt_interpretation,
                'data': ai_generated_data,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': f'خطا در ذخیره: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==========================================================
# ۳. ویو دریافت برنامه
# ==========================================================
class AIGetScheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ward_id = request.query_params.get('ward_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        schedule_type = request.query_params.get('schedule_type', 'main')

        if not ward_id or not year or not month:
            return Response({'error': 'شناسه بخش، سال و ماه الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        from api.views import get_persian_days_in_month, get_persian_weekday
        days_in_month = get_persian_days_in_month(int(year), int(month))
        weekdays = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
        offset = get_persian_weekday(int(year), int(month), 1)

        month_prefix = f"{year}-{str(month).zfill(2)}"
        holidays = Holiday.objects.filter(date__startswith=month_prefix).values('date', 'name')
        holidays_dict = {h['date']: h['name'] for h in holidays}

        try:
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return Response({'error': 'بخش مورد نظر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        # ✅ برای oncall/crisis/assistant، از تنظیمات چینش استفاده کن
        if schedule_type in DEPENDENT_SCHEDULE_TYPES:
            config = SpecialScheduleConfig.objects.filter(
                ward=ward, schedule_type=schedule_type
            ).first()

            if config:
                target_m = config.min_staff_morning
                target_e = config.min_staff_evening
                target_n = config.min_staff_night
                holiday_target_m = config.holiday_min_staff_morning
                holiday_target_e = config.holiday_min_staff_evening
                holiday_target_n = config.holiday_min_staff_night
            else:
                if schedule_type == 'assistant':
                    target_m = target_e = target_n = 1
                    holiday_target_m = holiday_target_e = holiday_target_n = 1
                else:
                    target_m = target_e = target_n = 0
                    holiday_target_m = holiday_target_e = holiday_target_n = 0
        else:
            target_m = ward.min_staff_morning
            target_e = ward.min_staff_evening
            target_n = ward.min_staff_night
            holiday_target_m = ward.holiday_min_staff_morning
            holiday_target_e = ward.holiday_min_staff_evening
            holiday_target_n = ward.holiday_min_staff_night

        try:
            ai_schedule = AISchedule.objects.get(
                ward_id=ward_id,
                year=int(year),
                month=int(month),
                schedule_type=schedule_type
            )
            return Response({
                'id': ai_schedule.id,
                'status': ai_schedule.status,
                'schedule_type': ai_schedule.schedule_type,
                'data': ai_schedule.ai_generated_data,
                'days_in_month': days_in_month,
                'weekdays': weekdays,
                'offset': offset,
                'year': year,
                'month': month,
                'holidays': holidays_dict,
                'target_m': target_m,
                'target_e': target_e,
                'target_n': target_n,
                'holiday_target_m': holiday_target_m,
                'holiday_target_e': holiday_target_e,
                'holiday_target_n': holiday_target_n,
                'solver': ai_schedule.ai_generated_data.get('solver', 'unknown'),
                'stats': ai_schedule.ai_generated_data.get('stats', {})
            }, status=status.HTTP_200_OK)
        except AISchedule.DoesNotExist:
            type_label = SCHEDULE_TYPE_LABELS.get(schedule_type, schedule_type)
            return Response({
                'error': f'برنامه {type_label} برای این ماه یافت نشد. ابتدا آن را تولید کنید.'
            }, status=status.HTTP_404_NOT_FOUND)


# ==========================================================
# ۴. ویو کپی برنامه پیشنهادی (به DraftSchedule)
# ==========================================================
class AICopyToMainScheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ward_id = request.data.get('ward_id')
        year = request.data.get('year')
        month = request.data.get('month')
        schedule_type = request.data.get('schedule_type', 'main')
        data = request.data.get('data')

        if not ward_id or not year or not month or not data:
            return Response({'error': 'شناسه بخش، سال، ماه و داده‌های برنامه الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ چک معتبر بودن نوع برنامه
        if schedule_type not in ALL_SCHEDULE_TYPES:
            return Response({'error': 'نوع برنامه نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return Response({'error': 'بخش مورد نظر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        month_prefix = f"{year}-{str(month).zfill(2)}"

        # ✅ پاک کردن DraftSchedule قبلی با همین schedule_type
        DraftSchedule.objects.filter(
            ward=ward,
            schedule_date__startswith=month_prefix,
            source='ai',
            schedule_type=schedule_type
        ).delete()

        new_schedules = []
        schedule_data = data.get('schedule_data', [])
        for staff_item in schedule_data:
            staff_id = staff_item.get('staff_id')
            try:
                user = User.objects.get(id=staff_id)
            except User.DoesNotExist:
                continue
            for day_item in staff_item.get('days', []):
                day = day_item.get('day')
                shift_code_str = day_item.get('shift')
                try:
                    shift_code_obj = ShiftCode.objects.get(code=shift_code_str)
                except ShiftCode.DoesNotExist:
                    continue
                schedule_date = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                new_schedules.append(
                    DraftSchedule(
                        ward=ward,
                        schedule_date=schedule_date,
                        shift_code=shift_code_obj,
                        assigned_staff=user,
                        source='ai',
                        schedule_type=schedule_type,
                        created_by=request.user
                    )
                )

        if new_schedules:
            DraftSchedule.objects.bulk_create(new_schedules)

            ai_schedule = AISchedule.objects.filter(
                ward=ward, year=year, month=month, schedule_type=schedule_type
            ).first()
            if ai_schedule:
                ai_schedule.status = 'ready_to_copy'
                ai_schedule.save()

            type_label = SCHEDULE_TYPE_LABELS.get(schedule_type, schedule_type)

            return Response({
                'message': f'برنامه {type_label} با موفقیت به برنامه پیش‌نویس (DraftSchedule) کپی شد.',
                'copied_count': len(new_schedules),
                'schedule_type': schedule_type,
            }, status=status.HTTP_200_OK)
        return Response({'error': 'هیچ داده‌ای برای کپی کردن یافت نشد.'}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================================
# ۵. ویو محاسبه درصد تطابق
# ==========================================================
class AICalculateMatchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            ward_id = request.data.get('ward_id')
            year = request.data.get('year')
            month = request.data.get('month')
            schedule_type = request.data.get('schedule_type', 'main')

            if not ward_id or not year or not month:
                return Response({'error': 'شناسه بخش، سال و ماه الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                ai_schedule = AISchedule.objects.get(
                    ward_id=ward_id, year=year, month=month, schedule_type=schedule_type
                )
                ai_data = ai_schedule.ai_generated_data
                month_prefix = f"{year}-{str(month).zfill(2)}"

                # 🔥 دریافت درخواست‌های شخصی پرستاران
                shift_requests = ShiftRequest.objects.filter(
                    ward_id=ward_id,
                    request_date__startswith=month_prefix
                ).select_related('user', 'shift_code')

                requests_dict = {}
                for req in shift_requests:
                    day = int(req.request_date.split('-')[2])
                    staff_id = req.user.id
                    if staff_id not in requests_dict:
                        requests_dict[staff_id] = {}
                    if req.shift_code:
                        requests_dict[staff_id][day] = req.shift_code.code
                    else:
                        requests_dict[staff_id][day] = 'off'

                # 🔥 دریافت برنامه پیش‌نویس سرپرستار
                draft_schedules = DraftSchedule.objects.filter(
                    ward_id=ward_id,
                    schedule_date__startswith=month_prefix,
                    source='manual'
                ).select_related('assigned_staff', 'shift_code')

                drafts_dict = {}
                for draft in draft_schedules:
                    day = int(draft.schedule_date.split('-')[2])
                    staff_id = draft.assigned_staff.id
                    if staff_id not in drafts_dict:
                        drafts_dict[staff_id] = {}
                    if draft.shift_code:
                        drafts_dict[staff_id][day] = draft.shift_code.code

                match_results = []
                total_match_percent = 0
                total_staff_with_data = 0

                for staff_item in ai_data.get('schedule_data', []):
                    staff_id = staff_item.get('staff_id')
                    staff_name = staff_item.get('staff_name')

                    # درصد تطابق با درخواست پرستار
                    staff_requests = requests_dict.get(staff_id, {})
                    request_match_percent = 100
                    request_match_count = 0
                    request_total = 0
                    request_mismatch = []

                    for day, requested_shift in staff_requests.items():
                        ai_shift = '-'
                        for day_item in staff_item.get('days', []):
                            if day_item.get('day') == day:
                                ai_shift = day_item.get('shift', '-')
                                break

                        request_total += 1
                        if requested_shift == 'off':
                            if ai_shift == '-' or ai_shift == 'H':
                                request_match_count += 1
                            else:
                                request_mismatch.append({
                                    'day': day,
                                    'requested': 'off',
                                    'ai_shift': ai_shift
                                })
                        else:
                            if requested_shift == ai_shift:
                                request_match_count += 1
                            elif set(requested_shift).issubset(set(ai_shift)):
                                if len(requested_shift) > len(ai_shift):
                                    request_match_count += 1
                                else:
                                    request_mismatch.append({
                                        'day': day,
                                        'requested': requested_shift,
                                        'ai_shift': ai_shift
                                    })
                            else:
                                request_mismatch.append({
                                    'day': day,
                                    'requested': requested_shift,
                                    'ai_shift': ai_shift
                                })

                    if request_total > 0:
                        request_match_percent = int((request_match_count / request_total) * 100)
                    else:
                        request_match_percent = 100

                    # درصد تطابق با پیش‌نویس سرپرستار
                    staff_drafts = drafts_dict.get(staff_id, {})
                    draft_match_percent = 100
                    draft_match_count = 0
                    draft_total = 0
                    draft_mismatch = []

                    for day, draft_shift in staff_drafts.items():
                        ai_shift = '-'
                        for day_item in staff_item.get('days', []):
                            if day_item.get('day') == day:
                                ai_shift = day_item.get('shift', '-')
                                break

                        draft_total += 1
                        if draft_shift == ai_shift:
                            draft_match_count += 1
                        elif set(draft_shift).issubset(set(ai_shift)):
                            if len(draft_shift) > len(ai_shift):
                                draft_match_count += 1
                            else:
                                draft_mismatch.append({
                                    'day': day,
                                    'draft': draft_shift,
                                    'ai_shift': ai_shift
                                })
                        else:
                            draft_mismatch.append({
                                'day': day,
                                'draft': draft_shift,
                                'ai_shift': ai_shift
                            })

                    if draft_total > 0:
                        draft_match_percent = int((draft_match_count / draft_total) * 100)
                    else:
                        draft_match_percent = 100

                    overall_percent = int((request_match_percent + draft_match_percent) / 2)

                    match_results.append({
                        'staff_id': staff_id,
                        'staff_name': staff_name,
                        'request_match_percent': request_match_percent,
                        'draft_match_percent': draft_match_percent,
                        'overall_percent': overall_percent,
                        'request_match_count': request_match_count,
                        'request_total': request_total,
                        'draft_match_count': draft_match_count,
                        'draft_total': draft_total,
                        'has_requests': request_total > 0,
                        'has_drafts': draft_total > 0,
                        'request_mismatch_days': request_mismatch,
                        'draft_mismatch_days': draft_mismatch
                    })

                    if request_total > 0 or draft_total > 0:
                        total_match_percent += overall_percent
                        total_staff_with_data += 1

                if total_staff_with_data > 0:
                    overall_percent = int(total_match_percent / total_staff_with_data)
                else:
                    overall_percent = 100

                return Response({
                    'overall_percent': overall_percent,
                    'schedule_type': schedule_type,
                    'details': match_results
                }, status=status.HTTP_200_OK)

            except AISchedule.DoesNotExist:
                type_label = SCHEDULE_TYPE_LABELS.get(schedule_type, schedule_type)
                return Response({
                    'error': f'برنامه {type_label} برای این ماه یافت نشد. ابتدا آن را تولید کنید.'
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': f'خطا در محاسبه تطابق: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================================
# ۶. ویو مقایسه الگوریتم‌ها
# ==========================================================
class AICompareSolversView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ward_id = request.data.get('ward_id')
        year = request.data.get('year')
        month = request.data.get('month')

        if not ward_id or not year or not month:
            return Response({'error': 'شناسه بخش، سال و ماه الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return Response({'error': 'بخش مورد نظر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        results = {}

        try:
            engine = ORToolsShiftSchedulingEngine(ward, int(year), int(month))
            greedy_schedule = engine.generate_schedule()
            results['greedy'] = {
                'schedule': greedy_schedule,
                'stats': {
                    'num_staff': len(greedy_schedule),
                    'solving_time': 0.5
                }
            }
        except Exception as e:
            results['greedy'] = {'error': str(e)}

        return Response(results, status=status.HTTP_200_OK)


# ==========================================================
# ۷. ویو مدیریت تنظیمات چینش آنکالی/بحران/کمک پرستار
# ==========================================================
class AISpecialConfigView(APIView):
    """
    مدیریت تنظیمات چینش استاندارد برنامه‌های آنکالی/بحران/کمک پرستار.
    - GET: دریافت تنظیمات موجود
    - POST: ایجاد یا به‌روزرسانی تنظیمات
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """دریافت تنظیمات چینش برای یک بخش و نوع برنامه"""
        ward_id = request.query_params.get('ward_id')
        schedule_type = request.query_params.get('schedule_type', 'oncall')

        if not ward_id:
            return Response({'error': 'شناسه بخش الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ شامل assistant
        if schedule_type not in DEPENDENT_SCHEDULE_TYPES:
            return Response(
                {'error': 'فقط برنامه‌های آنکالی، بحران و کمک پرستار تنظیمات اختصاصی دارند.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return Response({'error': 'بخش مورد نظر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        config = SpecialScheduleConfig.objects.filter(
            ward=ward, schedule_type=schedule_type
        ).first()

        if not config:
            if schedule_type == 'assistant':
                default_m = default_e = default_n = 1
                default_holiday_m = default_holiday_e = default_holiday_n = 1
            else:
                default_m = ward.min_staff_morning
                default_e = ward.min_staff_evening
                default_n = ward.min_staff_night
                default_holiday_m = ward.holiday_min_staff_morning
                default_holiday_e = ward.holiday_min_staff_evening
                default_holiday_n = ward.holiday_min_staff_night

            return Response({
                'exists': False,
                'ward_id': ward.id,
                'ward_name': ward.name,
                'schedule_type': schedule_type,
                'min_staff_morning': default_m,
                'min_staff_evening': default_e,
                'min_staff_night': default_n,
                'holiday_min_staff_morning': default_holiday_m,
                'holiday_min_staff_evening': default_holiday_e,
                'holiday_min_staff_night': default_holiday_n,
                'description': '',
            }, status=status.HTTP_200_OK)

        return Response({
            'exists': True,
            'id': config.id,
            'ward_id': ward.id,
            'ward_name': ward.name,
            'schedule_type': config.schedule_type,
            'min_staff_morning': config.min_staff_morning,
            'min_staff_evening': config.min_staff_evening,
            'min_staff_night': config.min_staff_night,
            'holiday_min_staff_morning': config.holiday_min_staff_morning,
            'holiday_min_staff_evening': config.holiday_min_staff_evening,
            'holiday_min_staff_night': config.holiday_min_staff_night,
            'description': config.description or '',
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """ایجاد یا به‌روزرسانی تنظیمات چینش"""
        ward_id = request.data.get('ward_id')
        schedule_type = request.data.get('schedule_type', 'oncall')

        if not ward_id:
            return Response({'error': 'شناسه بخش الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ شامل assistant
        if schedule_type not in DEPENDENT_SCHEDULE_TYPES:
            return Response(
                {'error': 'فقط برنامه‌های آنکالی، بحران و کمک پرستار تنظیمات اختصاصی دارند.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return Response({'error': 'بخش مورد نظر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.profile.role not in ['head', 'admin']:
            return Response(
                {'error': 'شما اجازه ویرایش تنظیمات را ندارید.'},
                status=status.HTTP_403_FORBIDDEN
            )

        config, created = SpecialScheduleConfig.objects.update_or_create(
            ward=ward,
            schedule_type=schedule_type,
            defaults={
                'min_staff_morning': int(request.data.get('min_staff_morning', 1)),
                'min_staff_evening': int(request.data.get('min_staff_evening', 1)),
                'min_staff_night': int(request.data.get('min_staff_night', 1)),
                'holiday_min_staff_morning': int(request.data.get('holiday_min_staff_morning', 1)),
                'holiday_min_staff_evening': int(request.data.get('holiday_min_staff_evening', 1)),
                'holiday_min_staff_night': int(request.data.get('holiday_min_staff_night', 1)),
                'description': request.data.get('description', ''),
            }
        )

        return Response({
            'status': 'success',
            'created': created,
            'message': f'تنظیمات {"ایجاد" if created else "به‌روزرسانی"} شد.',
            'id': config.id,
        }, status=status.HTTP_200_OK)