// src/components/PreviousSchedules.js
import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { getMediaUrl } from '../config';
import {
    getPastYears,
    getViewableMonthsForYear,
    getPreviousMonth,
    isFutureMonth,
} from '../utils/dateHelpers';

function PreviousSchedules() {
    // ✅ استیت‌های لیست بخش‌ها
    const [wards, setWards] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // ✅ استیت‌های انتخاب سال/ماه
    const [selectedYear, setSelectedYear] = useState(null);
    const [selectedMonth, setSelectedMonth] = useState(null);

    // ✅ استیت برای برنامه انتخاب‌شده (وقتی کاربر روی «ورود» کلیک می‌کند)
    const [selectedWard, setSelectedWard] = useState(null);
    const [scheduleData, setScheduleData] = useState([]);
    const [headSignature, setHeadSignature] = useState(null);
    const [matronSignature, setMatronSignature] = useState(null);
    const [loadingDetail, setLoadingDetail] = useState(false);

    const monthNames = ['', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد',
        'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];

    // ✅ لیست سال‌ها و ماه‌های قابل مشاهده
    const pastYears = getPastYears(10);
    const viewableMonths = getViewableMonthsForYear(selectedYear);

    // ============================================================
    // ✅ useEffect اولیه: مقدار پیش‌فرض = ماه قبل
    // ============================================================
    useEffect(() => {
        const prev = getPreviousMonth();
        setSelectedYear(prev.year);
        setSelectedMonth(prev.month);
    }, []);

    // ✅ بارگذاری لیست بخش‌ها
    const loadWards = async () => {
        if (!selectedYear || !selectedMonth) return;

        // ✅ چک امنیتی: آیا ماه انتخابی آینده است؟
        if (isFutureMonth(selectedYear, selectedMonth)) {
            alert('⚠️ فقط برنامه‌های ماه‌های گذشته و جاری قابل مشاهده هستند.');
            return;
        }

        setLoading(true);
        setError('');
        try {
            const res = await api.get(
                `/api/my-previous-schedules-wards/?year=${selectedYear}&month=${selectedMonth}`
            );
            setWards(res.data || []);
        } catch (err) {
            console.error('خطا در دریافت لیست بخش‌ها:', err);
            setError('❌ خطا در دریافت لیست برنامه‌ها');
            setWards([]);
        } finally {
            setLoading(false);
        }
    };

    // ✅ بارگذاری جزئیات یک بخش
    const loadWardDetail = async (wardId, year, month) => {
        setLoadingDetail(true);
        try {
            const res = await api.get(
                `/api/head-schedule/?ward_id=${wardId}&year=${year}&month=${month}&show_locked_only=true`
            );
            const data = res.data;

            // ✅ فیلتر کردن برنامه‌های قفل شده
            const filteredData = (data.table_data || []).filter(row => {
                return row.days.some(day => day.approval_status?.approved_by_matron === true);
            });

            setScheduleData(filteredData);
            setHeadSignature(data.head_signature || null);
            setMatronSignature(data.matron_signature || null);
        } catch (err) {
            console.error('خطا در دریافت جزئیات برنامه:', err);
            setScheduleData([]);
        } finally {
            setLoadingDetail(false);
        }
    };

    // ✅ کلیک روی «ورود»
    const handleEnterWard = (ward) => {
        setSelectedWard(ward);
        loadWardDetail(ward.ward_id, ward.year, ward.month);
    };

    // ✅ بازگشت به لیست
    const handleBackToList = () => {
        setSelectedWard(null);
        setScheduleData([]);
        setHeadSignature(null);
        setMatronSignature(null);
    };

    // ✅ افکت بارگذاری
    useEffect(() => {
        if (selectedYear && selectedMonth) {
            loadWards();
        }
    }, [selectedYear, selectedMonth]);

    // ============================================================
    // نمایش جزئیات یک بخش
    // ============================================================
    if (selectedWard) {
        const daysInMonth = scheduleData[0]?.days?.length || 30;
        const monthDaysArr = Array.from({ length: daysInMonth }, (_, i) => i + 1);

        return (
            <div style={{ border: '1px solid #ddd', borderRadius: '8px', background: '#fff', padding: '20px' }}>
                {/* هدر */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px', borderBottom: '2px solid #3498db', paddingBottom: '10px' }}>
                    <button
                        onClick={handleBackToList}
                        className="btn btn-secondary btn-sm"
                        style={{ background: '#6B7280', color: 'white', padding: '6px 12px', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
                    >
                        ↩️ بازگشت به لیست
                    </button>
                    <h2 style={{ margin: 0, color: '#2c3e50' }}>
                        📅 {selectedWard.ward_name} - {monthNames[selectedWard.month]} {selectedWard.year}
                    </h2>
                </div>

                {loadingDetail ? (
                    <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                        ⏳ در حال بارگذاری برنامه...
                    </div>
                ) : scheduleData.length === 0 ? (
                    <div style={{ padding: '40px', textAlign: 'center', color: '#95a5a6' }}>
                        📭 برنامه‌ای برای این بخش و ماه یافت نشد.
                    </div>
                ) : (
                    <>
                        <div style={{ overflowX: 'auto', maxWidth: '100%', WebkitOverflowScrolling: 'touch' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', minWidth: '1200px' }}>
                                <thead>
                                    <tr style={{ background: '#2c3e50', color: 'white' }}>
                                        <th style={{ padding: '8px 4px', border: '1px solid #34495e' }}>ردیف</th>
                                        <th style={{ padding: '8px 4px', border: '1px solid #34495e' }}>نام و نام خانوادگی</th>
                                        <th style={{ padding: '8px 4px', border: '1px solid #34495e' }}>سمت</th>
                                        <th style={{ padding: '8px 4px', border: '1px solid #34495e' }}>وضعیت</th>
                                        {monthDaysArr.map((day) => (
                                            <th key={day} style={{ padding: '4px', border: '1px solid #34495e', minWidth: '35px', textAlign: 'center' }}>
                                                {day}
                                            </th>
                                        ))}
                                        <th style={{ padding: '4px', border: '1px solid #34495e' }}>صبح</th>
                                        <th style={{ padding: '4px', border: '1px solid #34495e' }}>عصر</th>
                                        <th style={{ padding: '4px', border: '1px solid #34495e' }}>شب</th>
                                        <th style={{ padding: '4px', border: '1px solid #34495e' }}>مرخصی</th>
                                        <th style={{ padding: '4px', border: '1px solid #34495e' }}>آف</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {scheduleData.map((row, index) => (
                                        <tr key={row.staff_id}>
                                            <td style={{ border: '1px solid #ddd', padding: '4px', textAlign: 'center' }}>{index + 1}</td>
                                            <td style={{ border: '1px solid #ddd', padding: '4px 8px', textAlign: 'right', fontWeight: 'bold', whiteSpace: 'nowrap' }}>{row.staff_name}</td>
                                            <td style={{ border: '1px solid #ddd', padding: '4px', textAlign: 'center' }}>{row.position_label || '-'}</td>
                                            <td style={{ border: '1px solid #ddd', padding: '4px', textAlign: 'center' }}>{row.employment_status || '-'}</td>
                                            {row.days.map((day, dayIndex) => (
                                                <td key={dayIndex} style={{ border: '1px solid #ddd', padding: '2px', textAlign: 'center' }}>
                                                    {day.assigned_shifts && day.assigned_shifts.length > 0 ? (
                                                        day.assigned_shifts.map((shift, idx) => (
                                                            <span key={idx} style={{
                                                                display: 'inline-block', padding: '1px 4px', borderRadius: '3px', fontSize: '10px', fontWeight: 'bold', color: 'white', margin: '1px',
                                                                background: shift === 'M' ? '#3498db' : shift === 'E' ? '#f39c12' : shift === 'N' ? '#2c3e50' : shift === '-' ? '#95a5a6' : '#e74c3c'
                                                            }}>{shift}</span>
                                                        ))
                                                    ) : <span style={{ color: '#bdc3c7' }}>-</span>}
                                                </td>
                                            ))}
                                            <td style={{ border: '1px solid #ddd', padding: '4px', textAlign: 'center', background: '#f8f9fa' }}>{row.total_m}</td>
                                            <td style={{ border: '1px solid #ddd', padding: '4px', textAlign: 'center', background: '#f8f9fa' }}>{row.total_e}</td>
                                            <td style={{ border: '1px solid #ddd', padding: '4px', textAlign: 'center', background: '#f8f9fa' }}>{row.total_n}</td>
                                            <td style={{ border: '1px solid #ddd', padding: '4px', textAlign: 'center', background: '#f8f9fa' }}>{row.total_h}</td>
                                            <td style={{ border: '1px solid #ddd', padding: '4px', textAlign: 'center', background: '#f8f9fa' }}>{row.total_off}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* امضاها */}
                        <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: '30px', padding: '20px', borderTop: '2px solid #ddd' }}>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '5px' }}>سرپرستار</div>
                                {headSignature ? (
                                    <img src={getMediaUrl(headSignature)} alt="امضای سرپرستار" style={{ maxHeight: '60px', maxWidth: '150px', objectFit: 'contain' }} />
                                ) : (
                                    <div style={{ color: '#95a5a6', fontSize: '12px' }}>امضا ثبت نشده است</div>
                                )}
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '5px' }}>مدیر خدمات پرستاری</div>
                                {matronSignature ? (
                                    <img src={getMediaUrl(matronSignature)} alt="امضای مدیر خدمات پرستاری" style={{ maxHeight: '60px', maxWidth: '150px', objectFit: 'contain' }} />
                                ) : (
                                    <div style={{ color: '#95a5a6', fontSize: '12px' }}>امضا ثبت نشده است</div>
                                )}
                            </div>
                        </div>
                    </>
                )}
            </div>
        );
    }

    // ============================================================
    // نمایش لیست بخش‌ها
    // ============================================================
    return (
        <div style={{ border: '1px solid #ddd', borderRadius: '8px', background: '#fff', padding: '20px' }}>
            {/* هدر با انتخاب سال/ماه */}
            <div style={{ marginBottom: '15px', borderBottom: '2px solid #3498db', paddingBottom: '10px' }}>
                <h2 style={{ margin: '0 0 10px 0', color: '#2c3e50' }}>📅 برنامه‌های تایید شده قبلی</h2>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    {/* ✅ فقط ۱۰ سال گذشته */}
                    <select
                        value={selectedYear || ''}
                        onChange={(e) => {
                            const newYear = parseInt(e.target.value);
                            setSelectedYear(newYear);
                            // ✅ ریست ماه اگر خارج از بازه مجاز باشد
                            const months = getViewableMonthsForYear(newYear);
                            if (months.length > 0 && selectedMonth > months[months.length - 1].month) {
                                setSelectedMonth(months[months.length - 1].month);
                            }
                        }}
                        className="input-small"
                        style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #ddd' }}
                    >
                        {pastYears.map(y => (
                            <option key={y} value={y}>{y}</option>
                        ))}
                    </select>

                    {/* ✅ فقط ماه‌های قابل مشاهده (گذشته + جاری) */}
                    <select
                        value={selectedMonth || ''}
                        onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                        className="input-small"
                        style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #ddd' }}
                    >
                        {viewableMonths.map(m => (
                            <option key={m.month} value={m.month}>{m.name}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* محتوای اصلی */}
            {!selectedYear || !selectedMonth ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                    👈 لطفاً سال و ماه مورد نظر را انتخاب کنید.
                </div>
            ) : loading ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                    ⏳ در حال بارگذاری...
                </div>
            ) : error ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#e74c3c' }}>
                    {error}
                </div>
            ) : wards.length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#95a5a6' }}>
                    📭 برنامه تایید شده‌ای برای این ماه یافت نشد.
                </div>
            ) : (
                <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                        <thead>
                            <tr style={{ background: '#2c3e50', color: 'white' }}>
                                <th style={{ padding: '10px', border: '1px solid #34495e', textAlign: 'center' }}>#</th>
                                <th style={{ padding: '10px', border: '1px solid #34495e', textAlign: 'right' }}>بخش</th>
                                <th style={{ padding: '10px', border: '1px solid #34495e', textAlign: 'center' }}>سرپرستار</th>
                                <th style={{ padding: '10px', border: '1px solid #34495e', textAlign: 'center' }}>تعداد شیفت</th>
                                <th style={{ padding: '10px', border: '1px solid #34495e', textAlign: 'center' }}>ماه/سال</th>
                                <th style={{ padding: '10px', border: '1px solid #34495e', textAlign: 'center' }}>عملیات</th>
                            </tr>
                        </thead>
                        <tbody>
                            {wards.map((w, index) => (
                                <tr key={`${w.ward_id}-${w.year}-${w.month}`} style={{ background: index % 2 === 0 ? '#fff' : '#f8f9fa' }}>
                                    <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'center', fontWeight: 'bold' }}>{index + 1}</td>
                                    <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'right', fontWeight: 'bold' }}>🏥 {w.ward_name}</td>
                                    <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'center' }}>{w.head_name}</td>
                                    <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'center' }}>{w.count}</td>
                                    <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'center' }}>{monthNames[w.month]} {w.year}</td>
                                    <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'center' }}>
                                        <button
                                            onClick={() => handleEnterWard(w)}
                                            className="btn btn-primary btn-sm"
                                            style={{ padding: '6px 12px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
                                        >
                                            ورود ➜
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

export default PreviousSchedules;