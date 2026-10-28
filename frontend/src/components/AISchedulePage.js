// src/components/AISchedulePage.js
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { createPortal } from 'react-dom';
import { MONTH_NAMES, WEEKDAYS, SHIFT_OPTIONS, SCHEDULE_TYPES } from '../constants/persianCalendar';
import StaffManagementModal from './StaffManagementModal';
import '../styles/index.css';

function AISchedulePage() {
    const navigate = useNavigate();
    const [user, setUser] = useState(null);
    const [siteSettings, setSiteSettings] = useState(null);

    const [wards, setWards] = useState([]);
    const [wardId, setWardId] = useState(null);
    const [wardName, setWardName] = useState('');

    const [scheduleType, setScheduleType] = useState('main');

    const [prompt, setPrompt] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [isCopying, setIsCopying] = useState(false);
    const [matchResults, setMatchResults] = useState(null);
    const [isCalculatingMatch, setIsCalculatingMatch] = useState(false);

    const [tableData, setTableData] = useState([]);
    const [daysInMonth, setDaysInMonth] = useState(0);
    const [weekdays, setWeekdays] = useState([]);
    const [offset, setOffset] = useState(0);
    const [monthName, setMonthName] = useState('');
    const [year, setYear] = useState(1405);
    const [month, setMonth] = useState(6);

    const [capacityAlert, setCapacityAlert] = useState(null);

    const [targetM, setTargetM] = useState(0);
    const [targetE, setTargetE] = useState(0);
    const [targetN, setTargetN] = useState(0);
    const [holidayTargetM, setHolidayTargetM] = useState(0);
    const [holidayTargetE, setHolidayTargetE] = useState(0);
    const [holidayTargetN, setHolidayTargetN] = useState(0);

    const [holidays, setHolidays] = useState({});

    const [overlayInput, setOverlayInput] = useState(null);
    const inputOverlayRef = useRef(null);
    const [shiftCodes, setShiftCodes] = useState([]);
    const [validShiftCodes, setValidShiftCodes] = useState([]);

    const [generationBlocked, setGenerationBlocked] = useState(null);
    const [blockedStatus, setBlockedStatus] = useState(null);

    const [validationReport, setValidationReport] = useState(null);
    const [promptInterpretation, setPromptInterpretation] = useState(null);
    const [showReportModal, setShowReportModal] = useState(false);
    const [generationStats, setGenerationStats] = useState(null);

    // ✅ استیت جدید: مدیریت پرسنل
    const [showStaffManagement, setShowStaffManagement] = useState(false);

    const isSavingRef = useRef(false);

    useEffect(() => {
        loadUser();
        loadWards();
        loadSiteSettings();
    }, []);

    useEffect(() => {
        if (wardId && year && month) {
            checkScheduleStatus();
        }
    }, [wardId, year, month, scheduleType]);

    useEffect(() => {
        if (wardId && year && month) {
            loadAISchedule();
        }
    }, [wardId, year, month, scheduleType]);

    const loadSiteSettings = async () => {
        try {
            const res = await api.get('/api/site-settings/');
            setSiteSettings(res.data);
        } catch (err) {
            console.error('خطا در دریافت تنظیمات سایت:', err);
        }
    };

    const loadUser = async () => {
        try {
            const res = await api.get('/api/users/me/');
            setUser(res.data);
        } catch (error) {
            console.error('خطا در بارگذاری کاربر:', error);
            if (error.response && error.response.status === 401) {
                navigate('/login');
            }
        }
    };

    const loadWards = async () => {
        try {
            const res = await api.get('/api/ai/wards/');
            setWards(res.data);
            if (res.data.length > 0) {
                setWardId(res.data[0].id);
                setWardName(res.data[0].name);
            }
        } catch (error) {
            console.error('خطا در دریافت لیست بخش‌ها:', error);
        }
    };

    const checkScheduleStatus = async () => {
        if (!wardId || !year || !month) return;

        try {
            const res = await api.get(
                `/api/monthly-status/?ward_id=${wardId}&year=${year}&month=${month}`
            );
            const statusInfo = res.data[scheduleType];

            if (!statusInfo) {
                setGenerationBlocked(null);
                setBlockedStatus(null);
                return;
            }

            if (statusInfo.can_generate) {
                setGenerationBlocked(null);
                setBlockedStatus(null);
            } else {
                setGenerationBlocked(
                    statusInfo.generation_error ||
                    'امکان تولید این برنامه در وضعیت فعلی وجود ندارد.'
                );
                setBlockedStatus(statusInfo.status);
            }
        } catch (err) {
            console.error('خطا در چک وضعیت:', err);
            setGenerationBlocked(null);
            setBlockedStatus(null);
        }
    };

    const loadShiftCodes = async () => {
        if (!wardId) return;
        try {
            const res = await api.get(`/api/shift-codes/?ward_id=${wardId}`);
            setShiftCodes(res.data);
            setValidShiftCodes(res.data.map(item => item.code));
        } catch (err) {
            console.error("خطا در دریافت کدهای شیفت بخش:", err);
            setValidShiftCodes(SHIFT_OPTIONS.map(s => s.code));
        }
    };

    useEffect(() => {
        if (wardId) {
            loadShiftCodes();
        }
    }, [wardId]);

    const loadAISchedule = async () => {
        if (!wardId || !year || !month) return;
        try {
            const res = await api.get(
                `/api/ai/schedule/?ward_id=${wardId}&year=${year}&month=${month}&schedule_type=${scheduleType}`
            );
            if (res.data.data) {
                setTableData(res.data.data.schedule_data || []);
                setDaysInMonth(res.data.days_in_month || 30);
                setWeekdays(res.data.weekdays || WEEKDAYS);
                setOffset(res.data.offset || 0);
                setMonthName(MONTH_NAMES[res.data.month] || '');
                setHolidays(res.data.holidays || {});

                setTargetM(res.data.target_m || 0);
                setTargetE(res.data.target_e || 0);
                setTargetN(res.data.target_n || 0);
                setHolidayTargetM(res.data.holiday_target_m || 0);
                setHolidayTargetE(res.data.holiday_target_e || 0);
                setHolidayTargetN(res.data.holiday_target_n || 0);

                if (res.data.data.report) {
                    setValidationReport(res.data.data.report);
                }
                if (res.data.data.prompt_interpretation) {
                    setPromptInterpretation(res.data.data.prompt_interpretation);
                }
                if (res.data.data.stats) {
                    setGenerationStats(res.data.data.stats);
                }
            }
        } catch (error) {
            console.error('خطا در بارگذاری برنامه پیشنهادی:', error);
            setTableData([]);
        }
    };

    const handleGenerate = async () => {
        if (!wardId || !year || !month) return;

        if (generationBlocked) {
            alert(`⛔ ${generationBlocked}`);
            return;
        }

        setIsGenerating(true);
        setMatchResults(null);
        setTableData([]);
        setCapacityAlert(null);
        setValidationReport(null);
        setPromptInterpretation(null);

        try {
            const res = await api.post('/api/ai/generate/', {
                ward_id: wardId,
                year: year,
                month: month,
                schedule_type: scheduleType,
                prompt: prompt
            });

            if (res.data.alert_message) {
                setCapacityAlert({
                    type: res.data.alert_status || 'info',
                    message: res.data.alert_message
                });
            }

            if (res.data.report) {
                setValidationReport(res.data.report);
            }
            if (res.data.prompt_interpretation) {
                setPromptInterpretation(res.data.prompt_interpretation);
            }
            if (res.data.stats) {
                setGenerationStats(res.data.stats);
            }

            await loadAISchedule();
        } catch (error) {
            console.error('خطا در تولید برنامه:', error);
            const errMsg = error.response?.data?.error || 'خطا در تولید برنامه. لطفاً دوباره تلاش کنید.';
            alert(`❌ ${errMsg}`);
        } finally {
            setIsGenerating(false);
        }
    };

    const handleCalculateMatch = async () => {
        if (!tableData || tableData.length === 0) return;
        setIsCalculatingMatch(true);
        try {
            const res = await api.post('/api/ai/calculate-match/', {
                ward_id: wardId,
                year: year,
                month: month,
                schedule_type: scheduleType
            });
            setMatchResults(res.data);
            alert(`📊 درصد تطابق کلی: ${res.data.overall_percent}%`);
        } catch (error) {
            console.error('خطا در محاسبه درصد تطابق:', error);
            alert('❌ خطا در محاسبه درصد تطابق.');
        } finally {
            setIsCalculatingMatch(false);
        }
    };

    const handleCopyToMain = async () => {
        if (!tableData || tableData.length === 0) return;
        if (!window.confirm('⚠️ آیا مطمئن هستید؟ این عمل برنامه‌ی فعلی این ماه را به طور کامل با برنامه‌ی پیشنهادی جایگزین می‌کند.')) {
            return;
        }
        setIsCopying(true);
        try {
            const dataToCopy = {
                schedule_data: tableData
            };
            await api.post('/api/ai/copy-to-main/', {
                ward_id: wardId,
                year: year,
                month: month,
                schedule_type: scheduleType,
                data: dataToCopy
            });
            alert('✅ برنامه پیشنهادی با موفقیت روی برنامه اصلی کپی شد!');
            navigate('/head-schedule');
        } catch (error) {
            console.error('خطا در کپی برنامه:', error);
            alert('❌ خطا در کپی برنامه. لطفاً دوباره تلاش کنید.');
        } finally {
            setIsCopying(false);
        }
    };

    const handleBackToDashboard = () => {
        if (window.confirm('آیا می‌خواهید به داشبورد سرپرستار بازگردید؟')) {
            navigate('/head-schedule');
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        navigate('/login');
    };

    const handleCellClick = (staffId, day, rowIndex, event) => {
        if (!day) return;
        const rect = event.currentTarget.getBoundingClientRect();

        const currentStaff = tableData[rowIndex];
        let currentValue = '';
        const dayData = currentStaff.days.find(d => d.day === day);
        currentValue = dayData?.shift || '';

        setOverlayInput({ staffId, day, rowIndex, rect, value: currentValue });
        setTimeout(() => {
            if (inputOverlayRef.current) {
                inputOverlayRef.current.focus();
                inputOverlayRef.current.select();
                inputOverlayRef.current.click();
            }
        }, 10);
    };

    const moveToNextDay = () => {
        if (!overlayInput) return;
        const currentDay = overlayInput.day;
        const currentRowIndex = overlayInput.rowIndex;
        const totalDaysInRow = daysInMonth;

        let nextDay = currentDay + 1;
        let nextRowIndex = currentRowIndex;

        if (nextDay > totalDaysInRow) {
            nextDay = 1;
            nextRowIndex = nextRowIndex + 1;
        }

        if (nextRowIndex >= tableData.length) return;

        const nextStaffId = tableData[nextRowIndex]?.staff_id;
        if (nextStaffId) {
            setTimeout(() => {
                const tdElement = document.querySelector(`td[data-staff="${nextStaffId}"][data-day="${nextDay}"]`);
                if (tdElement) {
                    tdElement.click();
                }
            }, 100);
        }
    };

    const saveOverlayShift = (value, moveToNext = false) => {
        if (isSavingRef.current) return;
        if (!overlayInput || !inputOverlayRef.current) return;

        isSavingRef.current = true;

        try {
            const rawValue = value.trim().toUpperCase();

            if (!rawValue) {
                setOverlayInput(null);
                if (moveToNext) {
                    moveToNextDay();
                }
                return;
            }

            const isCodeValid = validShiftCodes.some(code => code.toUpperCase() === rawValue);
            if (!isCodeValid) {
                alert(`❌ کد شیفت نامعتبر است! کدهای مجاز برای این بخش: ${validShiftCodes.join(' , ')}`);
            } else {
                const exactCode = validShiftCodes.find(code => code.toUpperCase() === rawValue);

                const { day, rowIndex } = overlayInput;

                setTableData(prev => {
                    const newData = [...prev];
                    const staff = { ...newData[rowIndex] };
                    const newDays = staff.days.map(d => {
                        if (d.day === day) {
                            return { ...d, shift: exactCode };
                        }
                        return d;
                    });
                    staff.days = newDays;
                    newData[rowIndex] = staff;
                    return newData;
                });

                setOverlayInput(null);

                if (moveToNext) {
                    moveToNextDay();
                }
            }
        } finally {
            isSavingRef.current = false;
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveOverlayShift(e.target.value, true);
        } else if (e.key === 'Escape') {
            setOverlayInput(null);
        }
    };

    const calculateStaffStats = (days) => {
        let m = 0, e = 0, n = 0, h = 0, off = 0, offAfterNight = 0;
        let longs = 0;

        const dayShiftMap = {};
        days.forEach(d => {
            dayShiftMap[d.day] = d.shift || '-';
        });

        days.forEach(d => {
            const shift = d.shift || '-';
            const day = d.day;

            if (shift === 'H') {
                h++;
                return;
            }

            if (shift === '-') {
                const prevShift = dayShiftMap[day - 1];
                if (prevShift && prevShift.includes('N')) {
                    offAfterNight++;
                } else {
                    off++;
                }
                return;
            }

            const letters = shift.split('').filter(c => c === 'M' || c === 'E' || c === 'N');
            if (letters.length > 1) {
                longs++;
            }

            if (shift.includes('M')) m++;
            if (shift.includes('E')) e++;
            if (shift.includes('N')) n++;
        });

        return { m, e, n, h, off, offAfterNight, longs };
    };

    const calculateDailyStats = () => {
        const mArr = Array(daysInMonth).fill(0).map((_, i) => ({ day: i + 1, count: 0 }));
        const eArr = Array(daysInMonth).fill(0).map((_, i) => ({ day: i + 1, count: 0 }));
        const nArr = Array(daysInMonth).fill(0).map((_, i) => ({ day: i + 1, count: 0 }));

        tableData.forEach(row => {
            if (row.days) {
                row.days.forEach((dayCell, idx) => {
                    const shift = dayCell.shift || '-';
                    if (shift.includes('M')) mArr[idx].count += 1;
                    if (shift.includes('E')) eArr[idx].count += 1;
                    if (shift.includes('N')) nArr[idx].count += 1;
                });
            }
        });

        return { dailyM: mArr, dailyE: eArr, dailyN: nArr };
    };

    const isHolidayDay = (day) => {
        const dateKey = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        return !!holidays[dateKey];
    };

    const monthDaysArray = Array.from({ length: daysInMonth }, (_, i) => i + 1);

    const scheduleTypeLabel = scheduleType === 'main' ? 'اصلی' : scheduleType === 'oncall' ? 'آنکالی' : scheduleType === 'crisis' ? 'بحران' : 'کمک پرستار';

    const showMatchColumns = scheduleType === 'main';

    return (
        <div className="dashboard-container role-head">
            <header className="header role-head">
                <div className="header-info">
                    <h1>🤖 زیرسامانه هوش مصنوعی</h1>
                    <p>👤 {user?.first_name || ''} {user?.last_name || ''} - برنامه‌ریزی هوشمند شیفت</p>
                </div>

                <div className="header-buttons">
                    <button
                        className="header-btn"
                        onClick={handleBackToDashboard}
                    >
                        ↩️ بازگشت به داشبورد سرپرستار
                    </button>
                    <button
                        className="header-btn logout"
                        onClick={handleLogout}
                    >
                        🚪 خروج
                    </button>
                </div>
            </header>

            {generationBlocked && (
                <div style={{
                    padding: '16px 20px',
                    background: 'linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%)',
                    border: '2px solid #FCA5A5',
                    borderRadius: '12px',
                    marginBottom: '16px',
                    color: '#991B1B',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px'
                }}>
                    <span style={{ fontSize: '28px' }}>🔒</span>
                    <div>
                        <div style={{ fontSize: '16px', marginBottom: '4px' }}>
                            امکان تولید برنامه {scheduleTypeLabel} هوش مصنوعی وجود ندارد
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: '600' }}>
                            {generationBlocked}
                        </div>
                    </div>
                </div>
            )}

            <div className="ai-section-card">
                <h3 className="ai-section-title">📅 انتخاب بخش، ماه و نوع برنامه</h3>
                <div className="ai-form-row">
                    <div className="ai-form-group">
                        <label>🏥 بخش:</label>
                        <select
                            value={wardId || ''}
                            onChange={(e) => {
                                const selectedWardId = parseInt(e.target.value);
                                setWardId(selectedWardId);
                                const selectedWard = wards.find(w => w.id === selectedWardId);
                                if (selectedWard) {
                                    setWardName(selectedWard.name);
                                }
                            }}
                            className="input-small"
                        >
                            <option value="">انتخاب بخش...</option>
                            {wards.map(ward => (
                                <option key={ward.id} value={ward.id}>{ward.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="ai-form-group">
                        <label>📆 سال:</label>
                        <select value={year} onChange={(e) => setYear(parseInt(e.target.value))} className="input-small">
                            {Array.from({ length: 11 }, (_, i) => 1405 + i).map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                    </div>
                    <div className="ai-form-group">
                        <label>🗓️ ماه:</label>
                        <select value={month} onChange={(e) => setMonth(parseInt(e.target.value))} className="input-small">
                            {MONTH_NAMES.slice(1).map((m, idx) => (
                                <option key={idx + 1} value={idx + 1}>{m}</option>
                            ))}
                        </select>
                    </div>
                    <div className="ai-form-group">
                        <label>📋 نوع برنامه:</label>
                        <select
                            value={scheduleType}
                            onChange={(e) => setScheduleType(e.target.value)}
                            className="input-small"
                        >
                            {SCHEDULE_TYPES.map(t => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* ✅ کارت اطلاع‌رسانی قوانین پیش‌فرض */}
            <div className="ai-section-card" style={{
                background: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)',
                border: '2px solid #93C5FD',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '28px' }}>ℹ️</span>
                    <div>
                        <div style={{
                            fontWeight: '800',
                            fontSize: '14px',
                            color: '#1E40AF',
                            marginBottom: '4px',
                        }}>
                            قوانین پیش‌فرض فعال
                        </div>
                        <div style={{
                            fontSize: '12px',
                            color: '#3730A3',
                            lineHeight: '1.7',
                            fontWeight: '600',
                        }}>
                            سیستم به‌صورت خودکار ۴ قانون را اعمال می‌کند:
                            <br />
                            • حداکثر ۲ شب متوالی
                            <br />
                            • آف اجباری بعد از شب
                            <br />
                            • حداقل پوشش پرسنل
                            <br />
                            • توزیع عادلانه شیفت‌ها
                        </div>
                    </div>
                </div>
            </div>

            <div className="ai-section-card">
                <h3 className="ai-section-title">✍️ دستورات لحظه‌ای (پرامپت)</h3>
                <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="مثلاً: شیفت‌های خانم علیمحمدی را تا حد امکان صبح بگذارید..."
                    className="textarea"
                />
                <div className="ai-actions-row">
                    <button
                        onClick={handleGenerate}
                        disabled={isGenerating || !wardId || generationBlocked !== null}
                        className="btn btn-primary"
                        title={generationBlocked || ''}
                    >
                        {isGenerating ? (
                            <>
                                <span className="spinner"></span>
                                در حال تولید...
                            </>
                        ) : (
                            <>🚀 تولید برنامه {scheduleTypeLabel}</>
                        )}
                    </button>

                    {/* ✅ دکمه مدیریت پرسنل */}
                    {wardId && (
                        <button
                            onClick={() => setShowStaffManagement(true)}
                            className="btn"
                            style={{
                                background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                                color: 'white',
                                border: 'none',
                                padding: '10px 18px',
                                borderRadius: '10px',
                                fontWeight: '700',
                                fontFamily: 'inherit',
                                cursor: 'pointer',
                                fontSize: '14px',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                            }}
                            title="حذف یا بازگرداندن پرسنل به برنامه"
                        >
                            👥 مدیریت پرسنل
                        </button>
                    )}

                    {tableData.length > 0 && (
                        <>
                            {showMatchColumns && (
                                <button
                                    onClick={handleCalculateMatch}
                                    disabled={isCalculatingMatch}
                                    className="btn btn-warning"
                                >
                                    {isCalculatingMatch ? '⏳ در حال محاسبه...' : '📊 محاسبه درصد تطابق'}
                                </button>
                            )}
                            {validationReport && (
                                <button
                                    onClick={() => setShowReportModal(true)}
                                    className="btn btn-info"
                                    style={{
                                        background: validationReport.is_acceptable
                                            ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)'
                                            : 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)'
                                    }}
                                >
                                    📋 گزارش اعتبارسنجی ({validationReport.overall_score})
                                </button>
                            )}
                            <button
                                onClick={handleCopyToMain}
                                disabled={isCopying}
                                className="btn btn-success"
                            >
                                {isCopying ? '⏳ در حال کپی...' : `📋 کپی روی برنامه ${scheduleTypeLabel}`}
                            </button>
                        </>
                    )}
                </div>

                {promptInterpretation && promptInterpretation.total_sentences > 0 && (
                    <div style={{
                        marginTop: '16px',
                        padding: '12px 16px',
                        background: '#F0F9FF',
                        borderRadius: '10px',
                        border: '1px solid #BAE6FD',
                    }}>
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '8px',
                        }}>
                            <span style={{
                                fontWeight: '800',
                                fontSize: '13px',
                                color: '#0C4A6E',
                            }}>
                                🔍 تفسیر پرامپت
                            </span>
                            <span style={{
                                padding: '3px 10px',
                                background: promptInterpretation.match_rate === 100 ? '#D1FAE5' : '#FEF3C7',
                                color: promptInterpretation.match_rate === 100 ? '#065F46' : '#92400E',
                                borderRadius: '10px',
                                fontWeight: '700',
                                fontSize: '11px',
                            }}>
                                تطبیق: {promptInterpretation.matched_sentences}/{promptInterpretation.total_sentences}
                                {' '}
                                ({promptInterpretation.match_rate}%)
                            </span>
                        </div>

                        {promptInterpretation.matched_entities?.map((entity, idx) => (
                            <div key={idx} style={{
                                fontSize: '12px',
                                color: '#1E3A8A',
                                padding: '6px 10px',
                                background: 'white',
                                borderRadius: '6px',
                                marginTop: '6px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                            }}>
                                <span style={{ color: '#10B981' }}>✅</span>
                                <span style={{ flex: 1 }}>{entity.sentence}</span>
                                <span style={{
                                    padding: '2px 8px',
                                    background: '#E0E7FF',
                                    color: '#4338CA',
                                    borderRadius: '6px',
                                    fontSize: '10px',
                                    fontWeight: '700',
                                }}>
                                    {entity.rule_code}
                                </span>
                            </div>
                        ))}

                        {promptInterpretation.unmatched_sentences?.length > 0 && (
                            <div style={{ marginTop: '8px' }}>
                                {promptInterpretation.unmatched_sentences.map((s, idx) => (
                                    <div key={idx} style={{
                                        fontSize: '12px',
                                        color: '#991B1B',
                                        padding: '6px 10px',
                                        background: '#FEF2F2',
                                        borderRadius: '6px',
                                        marginTop: '6px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                    }}>
                                        <span>❌</span>
                                        <span>{s} — قابل تفسیر نبود</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {capacityAlert && (
                <div className={`ai-capacity-alert ${capacityAlert.type === 'warning' ? 'warning' : 'success'}`}>
                    {capacityAlert.message}
                </div>
            )}

            {validationReport && tableData.length > 0 && (
                <div style={{
                    padding: '12px 16px',
                    background: validationReport.is_acceptable
                        ? 'linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)'
                        : 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)',
                    borderRadius: '12px',
                    marginBottom: '16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                    border: validationReport.is_acceptable
                        ? '2px solid #86EFAC'
                        : '2px solid #FCD34D',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontSize: '28px' }}>
                            {validationReport.is_acceptable ? '✅' : '⚠️'}
                        </span>
                        <div>
                            <div style={{
                                fontWeight: '800',
                                fontSize: '15px',
                                color: validationReport.is_acceptable ? '#065F46' : '#92400E',
                            }}>
                                {validationReport.is_acceptable
                                    ? 'برنامه قابل قبول است'
                                    : 'برنامه دارای نقض است'}
                            </div>
                            <div style={{
                                fontSize: '12px',
                                color: validationReport.is_acceptable ? '#047857' : '#B45309',
                                marginTop: '2px',
                            }}>
                                امتیاز: <b>{validationReport.overall_score}</b>
                                {' '}| نقض‌ها: <b>{validationReport.total_violations}</b>
                                {generationStats?.elapsed_seconds !== undefined && (
                                    <> | زمان: <b>{generationStats.elapsed_seconds}s</b></>
                                )}
                            </div>
                        </div>
                    </div>

                    {validationReport.total_violations > 0 && (
                        <button
                            onClick={() => setShowReportModal(true)}
                            style={{
                                padding: '8px 16px',
                                background: 'white',
                                border: '1px solid #D1D5DB',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: '700',
                                fontSize: '13px',
                                fontFamily: 'inherit',
                            }}
                        >
                            👁️ مشاهده جزئیات
                        </button>
                    )}
                </div>
            )}

            {tableData.length > 0 ? (
                <div className="ai-table-container">
                    <div className="ai-table-header">
                        <h2>📋 برنامه {scheduleTypeLabel} - {wardName} - {monthName} {year}</h2>
                    </div>

                    <div className="ai-table-scroll">
                        <table className="ai-table">
                            <thead>
                                <tr>
                                    <th className="ai-th-fixed">#</th>
                                    <th className="ai-th-fixed name-col">نام و نام خانوادگی</th>
                                    <th className="ai-th-fixed position-col">سمت</th>
                                    {monthDaysArray.map((day) => {
                                        const dayIndex = offset + (day - 1);
                                        const isHoliday = isHolidayDay(day);
                                        const isFriday = dayIndex % 7 === 6;
                                        return (
                                            <th
                                                key={day}
                                                className={`ai-th-day ${isHoliday ? 'holiday' : ''} ${isFriday ? 'weekend' : ''}`}
                                            >
                                                <div className="ai-th-day-num">{day}</div>
                                                <div className="ai-th-day-name">{weekdays[dayIndex % 7]}</div>
                                            </th>
                                        );
                                    })}
                                    <th className="ai-th-stat">M</th>
                                    <th className="ai-th-stat">E</th>
                                    <th className="ai-th-stat">N</th>
                                    <th className="ai-th-stat">H</th>
                                    <th className="ai-th-stat">آف</th>
                                    <th className="ai-th-stat" style={{ background: '#FEF3C7', color: '#92400E' }}>لانگ</th>
                                    {showMatchColumns && (
                                        <>
                                            <th className="ai-th-match" title="درصد تطابق کلی">📊</th>
                                            <th className="ai-th-match" title="تطابق با درخواست پرستار">👤</th>
                                            <th className="ai-th-match" title="تطابق با پیش‌نویس سرپرستار">✍️</th>
                                        </>
                                    )}
                                </tr>
                            </thead>
                            <tbody>
                                {tableData.map((row, rowIndex) => {
                                    const matchInfo = matchResults?.details?.find(m => m.staff_id === row.staff_id);
                                    const stats = calculateStaffStats(row.days);
                                    return (
                                        <tr key={row.staff_id}>
                                            <td className="ai-td-fixed">{rowIndex + 1}</td>
                                            <td className="ai-td-name">{row.staff_name}</td>
                                            <td className="ai-td-fixed">{row.position_label || '-'}</td>
                                            {monthDaysArray.map((day) => {
                                                const dayData = row.days.find(d => d.day === day);
                                                const dayIndex = offset + (day - 1);
                                                const isHoliday = isHolidayDay(day);
                                                const isFriday = dayIndex % 7 === 6;
                                                return (
                                                    <td
                                                        key={day}
                                                        data-staff={row.staff_id}
                                                        data-day={day}
                                                        onClick={(e) => handleCellClick(row.staff_id, day, rowIndex, e)}
                                                        className={`ai-td-cell ${isHoliday || isFriday ? 'holiday-cell' : ''}`}
                                                    >
                                                        {dayData?.shift || '-'}
                                                    </td>
                                                );
                                            })}
                                            <td className="ai-td-stat">{stats.m}</td>
                                            <td className="ai-td-stat">{stats.e}</td>
                                            <td className="ai-td-stat">{stats.n}</td>
                                            <td className="ai-td-stat">{stats.h}</td>
                                            <td className="ai-td-stat">{stats.off}</td>
                                            <td className="ai-td-stat" style={{
                                                background: stats.longs > 0 ? '#FEF3C7' : '#F9FAFB',
                                                color: stats.longs > 0 ? '#92400E' : '#9CA3AF',
                                                fontWeight: '800',
                                            }}>
                                                {stats.longs}
                                            </td>
                                            {showMatchColumns && (
                                                <>
                                                    <td className="ai-td-match">
                                                        <span style={{ color: matchInfo?.overall_percent >= 70 ? '#10B981' : '#EF4444' }}>
                                                            {matchInfo ? `${matchInfo.overall_percent}%` : '---'}
                                                        </span>
                                                    </td>
                                                    <td className="ai-td-match">
                                                        <span style={{ color: matchInfo?.request_match_percent >= 70 ? '#10B981' : '#EF4444' }}>
                                                            {matchInfo ? `${matchInfo.request_match_percent}%` : '---'}
                                                        </span>
                                                    </td>
                                                    <td className="ai-td-match">
                                                        <span style={{ color: matchInfo?.draft_match_percent >= 70 ? '#10B981' : '#EF4444' }}>
                                                            {matchInfo ? `${matchInfo.draft_match_percent}%` : '---'}
                                                        </span>
                                                    </td>
                                                </>
                                            )}
                                        </tr>
                                    );
                                })}

                                <tr className="schedule-stat-row schedule-stat-m">
                                    <td colSpan="3" className="schedule-stat-label">☀️ صبح (M) عادی: {targetM} / تعطیل: {holidayTargetM}</td>
                                    {calculateDailyStats().dailyM.map((item, idx) => {
                                        const day = idx + 1;
                                        const isHoliday = isHolidayDay(day);
                                        const isFriday = weekdays[(offset + idx) % 7] === 'جمعه';
                                        const isHolidayOrFriday = isHoliday || isFriday;
                                        const target = isHolidayOrFriday ? holidayTargetM : targetM;

                                        let bgColor = '#d1fae5';
                                        if (item.count < target) bgColor = '#fee2e2';
                                        else if (item.count > target) bgColor = '#ffedd5';

                                        return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                                    })}
                                    <td className="schedule-stat-total">{calculateDailyStats().dailyM.reduce((sum, i) => sum + i.count, 0)}</td>
                                    <td colSpan={showMatchColumns ? 7 : 4}></td>
                                </tr>

                                <tr className="schedule-stat-row schedule-stat-e">
                                    <td colSpan="3" className="schedule-stat-label">🌅 عصر (E) عادی: {targetE} / تعطیل: {holidayTargetE}</td>
                                    {calculateDailyStats().dailyE.map((item, idx) => {
                                        const day = idx + 1;
                                        const isHoliday = isHolidayDay(day);
                                        const isFriday = weekdays[(offset + idx) % 7] === 'جمعه';
                                        const isHolidayOrFriday = isHoliday || isFriday;
                                        const target = isHolidayOrFriday ? holidayTargetE : targetE;

                                        let bgColor = '#d1fae5';
                                        if (item.count < target) bgColor = '#fee2e2';
                                        else if (item.count > target) bgColor = '#ffedd5';

                                        return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                                    })}
                                    <td className="schedule-stat-total">{calculateDailyStats().dailyE.reduce((sum, i) => sum + i.count, 0)}</td>
                                    <td colSpan={showMatchColumns ? 7 : 4}></td>
                                </tr>

                                <tr className="schedule-stat-row schedule-stat-n">
                                    <td colSpan="3" className="schedule-stat-label">🌙 شب (N) عادی: {targetN} / تعطیل: {holidayTargetN}</td>
                                    {calculateDailyStats().dailyN.map((item, idx) => {
                                        const day = idx + 1;
                                        const isHoliday = isHolidayDay(day);
                                        const isFriday = weekdays[(offset + idx) % 7] === 'جمعه';
                                        const isHolidayOrFriday = isHoliday || isFriday;
                                        const target = isHolidayOrFriday ? holidayTargetN : targetN;

                                        let bgColor = '#d1fae5';
                                        if (item.count < target) bgColor = '#fee2e2';
                                        else if (item.count > target) bgColor = '#ffedd5';

                                        return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                                    })}
                                    <td className="schedule-stat-total">{calculateDailyStats().dailyN.reduce((sum, i) => sum + i.count, 0)}</td>
                                    <td colSpan={showMatchColumns ? 7 : 4}></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                <div className="ai-empty-state">
                    <div className="ai-empty-icon">📭</div>
                    <p>برنامه‌ای تولید نشده است. لطفاً دستورات را وارد کرده و دکمه "تولید برنامه" را بزنید.</p>
                </div>
            )}

            {siteSettings?.footer_text && (
                <footer className="site-footer">
                    {siteSettings.footer_text}
                </footer>
            )}

            {showReportModal && validationReport && createPortal(
                <ValidationReportModal
                    report={validationReport}
                    onClose={() => setShowReportModal(false)}
                />,
                document.body
            )}

            {/* ✅ Modal مدیریت پرسنل */}
            {showStaffManagement && wardId && (
                <StaffManagementModal
                    wardId={wardId}
                    year={year}
                    month={month}
                    scheduleType={scheduleType}
                    wardName={wardName}
                    onClose={() => setShowStaffManagement(false)}
                    onUpdate={() => {
                        loadAISchedule();
                    }}
                />
            )}

            {overlayInput && createPortal(
                <div style={{
                    position: 'fixed',
                    top: overlayInput.rect.top,
                    left: overlayInput.rect.left,
                    width: overlayInput.rect.width,
                    height: overlayInput.rect.height,
                    zIndex: 9999,
                    boxSizing: 'border-box',
                    padding: 0, margin: 0
                }}>
                    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                        <input
                            ref={inputOverlayRef}
                            type="text"
                            defaultValue={overlayInput.value}
                            onKeyDown={handleKeyDown}
                            onBlur={(e) => saveOverlayShift(e.target.value)}
                            list="shift-code-list"
                            className="overlay-input"
                        />
                        <datalist id="shift-code-list">
                            {shiftCodes
                                .filter(code =>
                                    overlayInput.value ?
                                    code.code.toUpperCase().startsWith(overlayInput.value.toUpperCase()) :
                                    true
                                )
                                .map(code => (
                                    <option key={code.id} value={code.code} />
                                ))}
                        </datalist>
                    </div>
                </div>,
                document.body
            )}
        </div>
    );
}

// ============================================================
// Modal گزارش اعتبارسنجی
// ============================================================
function ValidationReportModal({ report, onClose }) {
    const getScoreColor = (score) => {
        if (score >= 90) return '#10B981';
        if (score >= 70) return '#F59E0B';
        return '#EF4444';
    };

    const getSeverityInfo = (severity) => {
        const map = {
            'critical': { label: '🚨 بحرانی', bg: '#FEE2E2', color: '#991B1B' },
            'high': { label: '🔴 مهم', bg: '#FEE2E2', color: '#991B1B' },
            'medium': { label: '🟡 متوسط', bg: '#FEF3C7', color: '#92400E' },
            'low': { label: '🟢 جزئی', bg: '#D1FAE5', color: '#065F46' },
            'info': { label: 'ℹ️ اطلاعات', bg: '#DBEAFE', color: '#1E40AF' },
        };
        return map[severity] || map['info'];
    };

    return (
        <div
            onClick={onClose}
            style={{
                position: 'fixed',
                top: 0, left: 0, right: 0, bottom: 0,
                background: 'rgba(0,0,0,0.6)',
                zIndex: 99999,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
                overflow: 'auto',
            }}
        >
            <div
                onClick={(e) => e.stopPropagation()}
                style={{
                    background: 'white',
                    borderRadius: '16px',
                    maxWidth: '800px',
                    width: '100%',
                    maxHeight: '90vh',
                    overflow: 'auto',
                }}
            >
                <div style={{
                    padding: '20px 24px',
                    background: `linear-gradient(135deg, ${getScoreColor(report.overall_score)} 0%, ${getScoreColor(report.overall_score)} 100%)`,
                    color: 'white',
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                }}>
                    <div>
                        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '800' }}>
                            📋 گزارش اعتبارسنجی برنامه
                        </h2>
                        <div style={{ marginTop: '8px', display: 'flex', gap: '16px', fontSize: '13px', fontWeight: '600' }}>
                            <span>امتیاز کلی: <b>{report.overall_score}</b></span>
                            <span>نقض‌ها: <b>{report.total_violations}</b></span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            width: '36px', height: '36px',
                            borderRadius: '50%',
                            background: 'rgba(255,255,255,0.2)',
                            border: '2px solid white',
                            color: 'white',
                            cursor: 'pointer',
                            fontSize: '20px',
                            fontWeight: 'bold',
                            fontFamily: 'inherit',
                            lineHeight: 1,
                        }}
                    >
                        ×
                    </button>
                </div>

                <div style={{ padding: '24px' }}>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                        gap: '12px',
                        marginBottom: '24px',
                    }}>
                        <ReportStat
                            label="قابل قبول"
                            value={report.is_acceptable ? '✅ بله' : '❌ خیر'}
                            color={report.is_acceptable ? '#10B981' : '#EF4444'}
                        />
                        <ReportStat
                            label="نقض‌های بحرانی"
                            value={report.critical_violations}
                            color={report.critical_violations > 0 ? '#EF4444' : '#10B981'}
                        />
                        <ReportStat
                            label="نقض‌های مهم"
                            value={report.high_violations}
                            color={report.high_violations > 0 ? '#F59E0B' : '#10B981'}
                        />
                        <ReportStat
                            label="زمان اجرا"
                            value={`${report.total_execution_time_ms?.toFixed(0)}ms`}
                            color="#3B82F6"
                        />
                    </div>

                    <h3 style={{ fontSize: '16px', fontWeight: '800', marginBottom: '12px' }}>
                        🔍 نتیجه هر قانون ({report.results?.length || 0})
                    </h3>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {report.results?.map((ruleResult, idx) => {
                            const isOk = ruleResult.violation_count === 0;
                            return (
                                <div key={idx} style={{
                                    padding: '12px 16px',
                                    background: isOk ? '#F0FDF4' : '#FEF2F2',
                                    borderRadius: '10px',
                                    border: `2px solid ${isOk ? '#86EFAC' : '#FCA5A5'}`,
                                }}>
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        marginBottom: isOk ? 0 : '8px',
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                            <span style={{ fontSize: '20px' }}>
                                                {isOk ? '✅' : '⚠️'}
                                            </span>
                                            <span style={{
                                                fontWeight: '700',
                                                fontSize: '14px',
                                                color: isOk ? '#065F46' : '#991B1B',
                                            }}>
                                                {ruleResult.rule_code}
                                            </span>
                                        </div>
                                        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                                            <span style={{
                                                fontSize: '12px',
                                                color: '#6B7280',
                                                fontWeight: '600',
                                            }}>
                                                امتیاز: {ruleResult.score}
                                            </span>
                                            {!isOk && (
                                                <span style={{
                                                    padding: '2px 8px',
                                                    background: '#DC2626',
                                                    color: 'white',
                                                    borderRadius: '10px',
                                                    fontSize: '11px',
                                                    fontWeight: '700',
                                                }}>
                                                    {ruleResult.violation_count} نقض
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {!isOk && ruleResult.violations?.slice(0, 5).map((v, vIdx) => {
                                        const sev = getSeverityInfo(v.severity);
                                        return (
                                            <div key={vIdx} style={{
                                                padding: '6px 10px',
                                                background: 'white',
                                                borderRadius: '6px',
                                                marginTop: '4px',
                                                fontSize: '12px',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px',
                                            }}>
                                                <span style={{
                                                    padding: '2px 8px',
                                                    background: sev.bg,
                                                    color: sev.color,
                                                    borderRadius: '6px',
                                                    fontSize: '10px',
                                                    fontWeight: '700',
                                                }}>
                                                    {sev.label}
                                                </span>
                                                <span style={{ flex: 1, color: '#374151' }}>{v.message}</span>
                                            </div>
                                        );
                                    })}

                                    {!isOk && ruleResult.violation_count > 5 && (
                                        <div style={{
                                            marginTop: '6px',
                                            fontSize: '11px',
                                            color: '#6B7280',
                                            fontStyle: 'italic',
                                        }}>
                                            ... و {ruleResult.violation_count - 5} نقض دیگر
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

function ReportStat({ label, value, color }) {
    return (
        <div style={{
            padding: '12px',
            background: '#F9FAFB',
            borderRadius: '10px',
            border: `1px solid ${color}20`,
            textAlign: 'center',
        }}>
            <div style={{ fontSize: '20px', fontWeight: '800', color }}>
                {value}
            </div>
            <div style={{
                fontSize: '11px',
                color: '#6B7280',
                fontWeight: '600',
                marginTop: '4px',
            }}>
                {label}
            </div>
        </div>
    );
}

export default AISchedulePage;