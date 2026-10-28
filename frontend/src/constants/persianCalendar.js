// src/constants/persianCalendar.js

// ✅ ماه‌های شمسی
export const MONTH_NAMES = [
    '', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
];

// ✅ روزهای هفته (0=شنبه تا 6=جمعه)
export const WEEKDAYS = [
    'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'
];

// ✅ کدهای شیفت پیش‌فرض
export const SHIFT_OPTIONS = [
    { code: 'M', label: 'صبح (M)' },
    { code: 'E', label: 'عصر (E)' },
    { code: 'N', label: 'شب (N)' },
    { code: 'ME', label: 'صبح و عصر (ME)' },
    { code: 'MN', label: 'صبح و شب (MN)' },
    { code: 'EN', label: 'عصر و شب (EN)' },
    { code: 'MEN', label: 'صبح و عصر و شب (MEN)' },
    { code: '-', label: 'آف (-)' },
    { code: 'H', label: 'مرخصی (H)' },
];

// ✅ انواع برنامه‌ها — شامل assistant
export const SCHEDULE_TYPES = [
    { value: 'main', label: '🤖 برنامه اصلی' },
    { value: 'oncall', label: '📞 آنکالی' },
    { value: 'crisis', label: '🚨 بحران' },
    { value: 'assistant', label: '🧑‍⚕️ کمک پرستار' },  // ✅ جدید
];

// ✅ رنگ و آیکون هر نوع (برای استفاده در UI)
export const SCHEDULE_TYPE_META = {
    main: { 
        label: '🤖 اصلی', 
        shortLabel: 'اصلی',
        color: '#3B82F6', 
        bg: '#DBEAFE', 
        text: '#1E40AF',
        emoji: '🤖',
    },
    oncall: { 
        label: '📞 آنکالی', 
        shortLabel: 'آنکالی',
        color: '#F59E0B', 
        bg: '#FEF3C7', 
        text: '#92400E',
        emoji: '📞',
    },
    crisis: { 
        label: '🚨 بحران', 
        shortLabel: 'بحران',
        color: '#EF4444', 
        bg: '#FEE2E2', 
        text: '#991B1B',
        emoji: '🚨',
    },
    assistant: { 
        label: '🧑‍⚕️ کمک پرستار', 
        shortLabel: 'کمک پرستار',
        color: '#10B981', 
        bg: '#D1FAE5', 
        text: '#065F46',
        emoji: '🧑‍⚕️',
    },
};

// ✅ وضعیت‌های گردش کار
export const SCHEDULE_STATUSES = {
    DRAFT: 'DRAFT',
    PENDING_SUPERVISOR: 'PENDING_SUPERVISOR',
    PENDING_MATRON: 'PENDING_MATRON',
    LOCKED: 'LOCKED',
    RETURNED_TO_HEAD: 'RETURNED_TO_HEAD',
    RETURNED_TO_SUPERVISOR: 'RETURNED_TO_SUPERVISOR',
};

// ✅ پیام‌های وضعیت
export const STATUS_MESSAGES = {
    DRAFT: '⏳ در انتظار تنظیم و تایید سرپرستار',
    PENDING_SUPERVISOR: '⏳ در انتظار تایید سوپروایزر',
    PENDING_MATRON: '⏳ در انتظار تایید نهایی مترون',
    LOCKED: '🔒 قفل شده (تایید نهایی)',
    RETURNED_TO_HEAD: '🔄 بازگردانده شده به سرپرستار',
    RETURNED_TO_SUPERVISOR: '🔄 بازگردانده شده به سوپروایزر',
};