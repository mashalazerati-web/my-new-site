// src/utils/dateHelpers.js
import { format } from 'date-fns-jalali';
import { MONTH_NAMES } from '../constants/persianCalendar';

/**
 * دریافت تاریخ جاری شمسی
 */
export function getCurrentJalaliDate() {
    const now = new Date();
    return {
        year: parseInt(format(now, 'yyyy')),
        month: parseInt(format(now, 'M')),
        day: parseInt(format(now, 'd')),
    };
}

/**
 * بررسی آیا (سال، ماه) قبل از ماه جاری است
 */
export function isPastMonth(year, month) {
    const current = getCurrentJalaliDate();
    if (year < current.year) return true;
    if (year > current.year) return false;
    return month < current.month;
}

/**
 * بررسی آیا (سال، ماه) برابر ماه جاری است
 */
export function isCurrentMonth(year, month) {
    const current = getCurrentJalaliDate();
    return year === current.year && month === current.month;
}

/**
 * بررسی آیا (سال، ماه) بعد از ماه جاری است
 */
export function isFutureMonth(year, month) {
    const current = getCurrentJalaliDate();
    if (year > current.year) return true;
    if (year < current.year) return false;
    return month > current.month;
}

/**
 * بررسی آیا (سال، ماه) قابل مشاهده است (گذشته یا جاری)
 */
export function isViewableMonth(year, month) {
    return isPastMonth(year, month) || isCurrentMonth(year, month);
}

/**
 * تولید لیست ۱۰ سال گذشته (شامل سال جاری)
 * خروجی: [1405, 1404, 1403, ...]
 */
export function getPastYears(yearsBack = 10) {
    const current = getCurrentJalaliDate();
    const years = [];
    for (let i = 0; i < yearsBack; i++) {
        years.push(current.year - i);
    }
    return years;
}

/**
 * تولید لیست ماه‌های قابل مشاهده برای یک سال خاص
 * @param {number} selectedYear - سال انتخاب‌شده
 * @returns {Array<{month: number, name: string}>}
 */
export function getViewableMonthsForYear(selectedYear) {
    const current = getCurrentJalaliDate();
    const months = [];

    // اگر سال انتخاب‌شده، سال جاری است → فقط ماه‌های تا ماه جاری
    if (selectedYear === current.year) {
        for (let m = 1; m <= current.month; m++) {
            months.push({ month: m, name: MONTH_NAMES[m] });
        }
    } else if (selectedYear < current.year) {
        // سال‌های گذشته → همه ۱۲ ماه
        for (let m = 1; m <= 12; m++) {
            months.push({ month: m, name: MONTH_NAMES[m] });
        }
    }
    // سال‌های آینده → لیست خالی

    return months;
}

/**
 * دریافت ماه قبل از ماه جاری (برای مقدار پیش‌فرض)
 */
export function getPreviousMonth() {
    const current = getCurrentJalaliDate();
    let year = current.year;
    let month = current.month - 1;
    if (month < 1) {
        month = 12;
        year -= 1;
    }
    return { year, month };
}

/**
 * دریافت ماه بعد از ماه جاری (برای حالت فعال)
 */
export function getNextMonth() {
    const current = getCurrentJalaliDate();
    let year = current.year;
    let month = current.month + 1;
    if (month > 12) {
        month = 1;
        year += 1;
    }
    return { year, month };
}