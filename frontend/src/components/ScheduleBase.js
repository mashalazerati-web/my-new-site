// src/components/ScheduleBase.js
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../services/api';
import { getMediaUrl } from '../config';
import '../styles/index.css';
import { createPortal } from 'react-dom';
import ScheduleActions from './ScheduleActions';
import { MONTH_NAMES, SCHEDULE_TYPE_META, SCHEDULE_TYPES } from '../constants/persianCalendar';
import StaffManagementModal from './StaffManagementModal';


function ScheduleBase({
    title,
    mode,
    renderActions,
    extraProps,
    hideToolbar
}) {
    const location = useLocation();
    const navigate = useNavigate();

    const wardId = React.useMemo(() => {
        return extraProps?.wardId || new URLSearchParams(location.search).get('ward_id') || null;
    }, [extraProps?.wardId, location.search]);

    const urlScheduleType = new URLSearchParams(location.search).get('schedule_type');
    const initialScheduleType = extraProps?.scheduleType || urlScheduleType || 'main';

    const urlYear = new URLSearchParams(location.search).get('year');
    const urlMonth = new URLSearchParams(location.search).get('month');
    const initialYear = extraProps?.initialYear || (urlYear ? parseInt(urlYear) : null);
    const initialMonth = extraProps?.initialMonth || (urlMonth ? parseInt(urlMonth) : null);

    const [tableData, setTableData] = useState([]);
    const [dailyM, setDailyM] = useState([]);
    const [dailyE, setDailyE] = useState([]);
    const [dailyN, setDailyN] = useState([]);

    const [targetM, setTargetM] = useState(0);
    const [targetE, setTargetE] = useState(0);
    const [targetN, setTargetN] = useState(0);
    const [holidayTargetM, setHolidayTargetM] = useState(0);
    const [holidayTargetE, setHolidayTargetE] = useState(0);
    const [holidayTargetN, setHolidayTargetN] = useState(0);

    const [headSignature, setHeadSignature] = useState(null);
    const [matronSignature, setMatronSignature] = useState(null);

    const [serverStatus, setServerStatus] = useState('DRAFT');

    const [approvedByHead, setApprovedByHead] = useState(false);
    const [isLocked, setIsLocked] = useState(false);
    const [returnedToHead, setReturnedToHead] = useState(false);
    const [returnedToSupervisor, setReturnedToSupervisor] = useState(false);

    const [matronFeedback, setMatronFeedback] = useState('');
    const [supervisorFeedback, setSupervisorFeedback] = useState('');
    const [matronFeedbackBy, setMatronFeedbackBy] = useState(null);
    const [supervisorFeedbackBy, setSupervisorFeedbackBy] = useState(null);

    const [anyApprovedByHead, setAnyApprovedByHead] = useState(false);
    const [anyApprovedBySupervisor, setAnyApprovedBySupervisor] = useState(false);

    const [forceRerender, setForceRerender] = useState(0);

    const [year, setYear] = useState(initialYear);
    const [month, setMonth] = useState(initialMonth);
    const [monthName, setMonthName] = useState('');
    const [daysInMonth, setDaysInMonth] = useState(0);
    const [weekdays, setWeekdays] = useState([]);
    const [offset, setOffset] = useState(0);
    const [loading, setLoading] = useState(false);
    const [apiError, setApiError] = useState(null);

    const [overlayInput, setOverlayInput] = useState(null);
    const inputOverlayRef = useRef(null);

    const lastInitializedRef = useRef({
        wardId: null,
        scheduleType: null,
    });

    const [localChanges, setLocalChanges] = useState({});

    const [shiftCodes, setShiftCodes] = useState([]);
    const [validShiftCodes, setValidShiftCodes] = useState([]);
    const [usedShiftCodes, setUsedShiftCodes] = useState([]);

    const [wardInfo, setWardInfo] = useState(null);
    const [wardNotes, setWardNotes] = useState('');
    const [scheduleSource, setScheduleSource] = useState('final');
    const [scheduleType, setScheduleType] = useState(initialScheduleType);

    // ✅ استیت مدیریت پرسنل
    const [showStaffManagement, setShowStaffManagement] = useState(false);

    const getRoleClass = () => {
        const userRole = extraProps?.userRole || '';
        if (userRole === 'head') return 'schedule-head';
        if (userRole === 'supervisor') return 'schedule-supervisor';
        if (userRole === 'admin') return 'schedule-matron';
        return 'schedule-default';
    };

    // ✅ استفاده از SCHEDULE_TYPE_META برای label
    const getScheduleTypeLabel = () => {
        const meta = SCHEDULE_TYPE_META[scheduleType];
        if (meta) {
            return ` - ${meta.label}`;
        }
        return ' - 🤖 اصلی';
    };

    // ✅ گرفتن shortLabel برای استفاده در سلکتور دوم
    const getScheduleTypeShortLabel = () => {
        return SCHEDULE_TYPE_META[scheduleType]?.shortLabel || '';
    };

    const calculateDailyStats = (data, daysCount) => {
        const mArr = Array(daysCount).fill(0).map((_, i) => ({ day: i + 1, count: 0 }));
        const eArr = Array(daysCount).fill(0).map((_, i) => ({ day: i + 1, count: 0 }));
        const nArr = Array(daysCount).fill(0).map((_, i) => ({ day: i + 1, count: 0 }));

        data.forEach(row => {
            if (row.days) {
                row.days.forEach((dayCell, idx) => {
                    if (dayCell.assigned_shifts && dayCell.assigned_shifts.length > 0) {
                        dayCell.assigned_shifts.forEach(shiftCode => {
                            const upperCode = shiftCode.toUpperCase();
                            if (upperCode.includes('M')) mArr[idx].count += 1;
                            if (upperCode.includes('E')) eArr[idx].count += 1;
                            if (upperCode.includes('N')) nArr[idx].count += 1;
                        });
                    }
                });
            }
        });
        return { dailyM: mArr, dailyE: eArr, dailyN: nArr };
    };

    const calculateRowStats = (days) => {
        let total_m = 0, total_e = 0, total_n = 0, total_h = 0;
        let total_off = 0;
        let total_off_after_night = 0;

        days.forEach((dayCell, idx) => {
            if (dayCell.assigned_shifts && dayCell.assigned_shifts.length > 0) {
                dayCell.assigned_shifts.forEach(shiftCode => {
                    const upperCode = shiftCode.toUpperCase();

                    if (upperCode.includes('M')) total_m += 1;
                    if (upperCode.includes('E')) total_e += 1;
                    if (upperCode.includes('N')) total_n += 1;
                    if (upperCode === 'H') total_h += 1;

                    if (upperCode === '-' || upperCode === '') {
                        const prevDay = days[idx - 1];
                        const prevShift = prevDay?.assigned_shifts?.[0] || '';
                        if (prevShift.toUpperCase().includes('N')) {
                            total_off_after_night += 1;
                        } else {
                            total_off += 1;
                        }
                    }
                });
            }
        });

        return { total_m, total_e, total_n, total_h, total_off, total_off_after_night };
    };

    const loadShiftCodes = async () => {
        try {
            const res = await api.get('/api/shift-codes/');
            setShiftCodes(res.data);
            setValidShiftCodes(res.data.map(item => item.code));
        } catch (err) {
            console.error("خطا در دریافت کدهای شیفت", err);
        }
    };

    const loadSchedule = async () => {
        setLoading(true);
        setApiError(null);
        try {
            let apiUrl = '';
            if (mode === 'head') {
                apiUrl = `/api/head-schedule/?year=${year || ''}&month=${month || ''}&source=${scheduleSource}&schedule_type=${scheduleType}`;
            } else if (mode === 'supervisor') {
                apiUrl = `/api/supervisor-schedule/?year=${year || ''}&month=${month || ''}&schedule_type=${scheduleType}`;
            } else if (mode === 'matron') {
                apiUrl = `/api/matron-schedule/?year=${year || ''}&month=${month || ''}&schedule_type=${scheduleType}`;
            }

            if (wardId) apiUrl += `&ward_id=${wardId}`;

            const res = await api.get(apiUrl);

            if (res.data.ward_info) setWardInfo(res.data.ward_info);

            const shouldReinitialize =
                lastInitializedRef.current.wardId !== wardId ||
                lastInitializedRef.current.scheduleType !== scheduleType;

            if (shouldReinitialize) {
                const serverYear = res.data.year;
                const serverMonth = res.data.month;

                if (serverYear && serverYear > 0 && serverMonth && serverMonth > 0) {
                    setYear(serverYear);
                    setMonth(serverMonth);
                } else {
                    console.warn('⚠️ year/month از سرور معتبر نیستند:', {
                        year: serverYear,
                        month: serverMonth,
                    });
                }

                lastInitializedRef.current = {
                    wardId: wardId,
                    scheduleType: scheduleType,
                };
            }

            setMonthName(MONTH_NAMES[res.data.month] || '');
            setWeekdays(res.data.weekdays || []);
            setDaysInMonth(res.data.days_in_month || 30);
            setOffset(res.data.offset || 0);

            setTargetM(res.data.target_m || 0);
            setTargetE(res.data.target_e || 0);
            setTargetN(res.data.target_n || 0);
            setHolidayTargetM(res.data.holiday_target_m || 0);
            setHolidayTargetE(res.data.holiday_target_e || 0);
            setHolidayTargetN(res.data.holiday_target_n || 0);
            setHeadSignature(res.data.head_signature || null);
            setMatronSignature(res.data.matron_signature || null);

            setAnyApprovedByHead(res.data.any_approved_by_head || false);
            setAnyApprovedBySupervisor(res.data.any_approved_by_supervisor || false);

            setMatronFeedback(res.data.matron_feedback || '');
            setSupervisorFeedback(res.data.supervisor_feedback || '');
            setMatronFeedbackBy(res.data.matron_feedback_by || null);
            setSupervisorFeedbackBy(res.data.supervisor_feedback_by || null);

            setWardNotes(res.data.ward_notes || '');

            const statusFromServer = res.data.status || 'DRAFT';
            setServerStatus(statusFromServer);

            setApprovedByHead(
                ['PENDING_SUPERVISOR', 'PENDING_MATRON', 'LOCKED'].includes(statusFromServer)
            );
            setIsLocked(statusFromServer === 'LOCKED');
            setReturnedToHead(statusFromServer === 'RETURNED_TO_HEAD');
            setReturnedToSupervisor(statusFromServer === 'RETURNED_TO_SUPERVISOR');

            const correctedTableData = (res.data.table_data || []).map(row => {
                const newDays = (row.days || []).map(dayCell => {
                    return {
                        ...dayCell,
                        is_weekend: dayCell.is_weekend || false,
                        is_holiday: dayCell.is_holiday || false,
                        holiday_name: dayCell.holiday_name || '',
                        assigned_shifts: dayCell.assigned_shifts && dayCell.assigned_shifts.length > 0
                            ? dayCell.assigned_shifts
                            : (dayCell.requested_shift ? [dayCell.requested_shift] : [])
                    };
                });

                const stats = calculateRowStats(newDays);

                return {
                    ...row,
                    days: newDays,
                    total_m: stats.total_m,
                    total_e: stats.total_e,
                    total_n: stats.total_n,
                    total_h: stats.total_h,
                    total_off: stats.total_off,
                    total_off_after_night: stats.total_off_after_night,
                };
            });

            setTableData(correctedTableData);

            const usedShiftCodesSet = new Set();
            correctedTableData.forEach(row => {
                (row.days || []).forEach(dayCell => {
                    if (dayCell.assigned_shifts && dayCell.assigned_shifts.length > 0) {
                        dayCell.assigned_shifts.forEach(shiftCode => {
                            usedShiftCodesSet.add(shiftCode);
                        });
                    }
                });
            });
            setUsedShiftCodes(Array.from(usedShiftCodesSet).sort());

            const daysCount = res.data.days_in_month || 30;
            const calculatedStats = calculateDailyStats(correctedTableData, daysCount);

            setDailyM(calculatedStats.dailyM);
            setDailyE(calculatedStats.dailyE);
            setDailyN(calculatedStats.dailyN);

            setLocalChanges({});
        } catch (err) {
            console.error('❌ خطای بحرانی در دریافت برنامه:', err);
            setApiError({
                status: err.response?.status || 500,
                message: err.response?.data?.error || 'خطای ناشناخته در دریافت اطلاعات از سرور.'
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadSchedule();
        loadShiftCodes();
    }, [year, month, wardId, forceRerender, scheduleSource, scheduleType]);

    const showLoadingModal = (message = 'در حال تولید فایل...') => {
        const existing = document.getElementById('export-loading-overlay');
        if (existing) existing.remove();

        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'export-loading-overlay';
        loadingDiv.className = 'modal-overlay';
        loadingDiv.innerHTML = `
            <div class="modal-card">
                <div class="modal-icon" style="font-size: 48px;">⏳</div>
                <div class="modal-title">${message}</div>
                <div class="modal-message">لطفاً صبر کنید، این عملیات ممکن است چند ثانیه طول بکشد...</div>
            </div>
        `;
        document.body.appendChild(loadingDiv);
    };

    const showSuccessModal = (message = 'فایل با موفقیت ایجاد شد!') => {
        const existing = document.getElementById('export-loading-overlay');
        if (existing) existing.remove();

        const successDiv = document.createElement('div');
        successDiv.id = 'export-success-overlay';
        successDiv.className = 'modal-overlay';
        successDiv.innerHTML = `
            <div class="modal-card">
                <div class="modal-icon" style="font-size: 48px;">✅</div>
                <div class="modal-title">${message}</div>
                <button class="btn btn-primary" onclick="document.getElementById('export-success-overlay').remove();">
                    باشه
                </button>
            </div>
        `;
        document.body.appendChild(successDiv);
    };

    const showErrorModal = (message = 'خطا در تولید فایل') => {
        const existing = document.getElementById('export-loading-overlay');
        if (existing) existing.remove();

        const errorDiv = document.createElement('div');
        errorDiv.id = 'export-error-overlay';
        errorDiv.className = 'modal-overlay';
        errorDiv.innerHTML = `
            <div class="modal-card">
                <div class="modal-icon" style="font-size: 48px;">❌</div>
                <div class="modal-title">${message}</div>
                <button class="btn btn-primary" onclick="document.getElementById('export-error-overlay').remove();">
                    باشه
                </button>
            </div>
        `;
        document.body.appendChild(errorDiv);
    };

    const handleExportExcel = async () => {
        showLoadingModal('📊 در حال تولید فایل Excel...');

        try {
            const response = await api.get(
                `/api/export-excel/?ward_id=${wardId}&year=${year}&month=${month}&schedule_type=${scheduleType}`,
                { responseType: 'blob' }
            );

            if (response.data && response.data.type === 'application/json') {
                const text = await response.data.text();
                const errorData = JSON.parse(text);
                showErrorModal(errorData.error || 'خطا در تولید فایل Excel');
                return;
            }

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `برنامه_${wardInfo?.name || 'بخش'}_${monthName}_${year}.xlsx`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);

            showSuccessModal('✅ فایل Excel با موفقیت ایجاد شد!');
        } catch (error) {
            console.error('خطا در خروجی اکسل:', error);
            let errMsg = 'خطا در تولید فایل Excel';
            if (error.response?.data) {
                if (error.response.data instanceof Blob) {
                    try {
                        const text = await error.response.data.text();
                        const errorData = JSON.parse(text);
                        errMsg = errorData.error || errMsg;
                    } catch (e) {}
                } else if (typeof error.response.data === 'object') {
                    errMsg = error.response.data.error || errMsg;
                }
            }
            showErrorModal(`❌ ${errMsg}`);
        }
    };

    const handleExportPDF = async () => {
        showLoadingModal('📄 در حال تولید فایل PDF...');

        try {
            const response = await api.get(
                `/api/export-pdf/?ward_id=${wardId}&year=${year}&month=${month}&schedule_type=${scheduleType}`,
                { responseType: 'blob' }
            );

            if (response.data && response.data.type === 'application/json') {
                const text = await response.data.text();
                const errorData = JSON.parse(text);
                showErrorModal(errorData.error || 'خطا در تولید فایل PDF');
                return;
            }

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `برنامه_${wardInfo?.name || 'بخش'}_${monthName}_${year}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);

            showSuccessModal('✅ فایل PDF با موفقیت ایجاد شد!');
        } catch (error) {
            console.error('خطا در خروجی PDF:', error);
            let errMsg = 'خطا در تولید فایل PDF';
            if (error.response?.data) {
                if (error.response.data instanceof Blob) {
                    try {
                        const text = await error.response.data.text();
                        const errorData = JSON.parse(text);
                        errMsg = errorData.error || errMsg;
                    } catch (e) {}
                } else if (typeof error.response.data === 'object') {
                    errMsg = error.response.data.error || errMsg;
                }
            }
            showErrorModal(`❌ ${errMsg}`);
        }
    };

    const applyLocalUpdate = (staffId, dayIndex, newShift) => {
        const key = `${staffId}-${dayIndex}`;
        setLocalChanges(prev => ({ ...prev, [key]: newShift }));

        setTableData(prevData => {
            const newData = [...prevData];
            const rowIndex = newData.findIndex(r => r.staff_id === staffId);
            if (rowIndex === -1) return prevData;

            const row = { ...newData[rowIndex] };
            const days = [...row.days];
            const cell = { ...days[dayIndex] };

            cell.assigned_shifts = [newShift];
            cell.draft_shift = newShift;
            cell.requested_shift = '';

            days[dayIndex] = cell;
            row.days = days;

            const stats = calculateRowStats(days);
            row.total_m = stats.total_m;
            row.total_e = stats.total_e;
            row.total_n = stats.total_n;
            row.total_h = stats.total_h;
            row.total_off = stats.total_off;
            row.total_off_after_night = stats.total_off_after_night;

            newData[rowIndex] = row;

            const daysCount = daysInMonth || 30;
            const updatedStats = calculateDailyStats(newData, daysCount);
            setDailyM(updatedStats.dailyM);
            setDailyE(updatedStats.dailyE);
            setDailyN(updatedStats.dailyN);

            return newData;
        });
    };

    const handleCellClick = (staffId, day, rowIndex, event) => {
        if (!day) return;
        if (mode === 'supervisor' || mode === 'matron') return;
        if (anyApprovedByHead && !returnedToHead) return;
        if (isLocked) return;

        const rect = event.currentTarget.getBoundingClientRect();
        const changeKey = `${staffId}-${day - 1}`;
        const localValue = localChanges[changeKey];

        let currentValue = '';
        if (localValue) {
            currentValue = localValue;
        } else {
            const currentShifts = tableData[rowIndex]?.days[day - 1]?.assigned_shifts || [];
            currentValue = currentShifts.length > 0 ? currentShifts[0] : '';
        }

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
        const currentDayNum = overlayInput.day;
        const totalDaysInMonth = daysInMonth;

        let nextDayNum = currentDayNum + 1;
        let nextRowIndex = overlayInput.rowIndex;

        if (nextDayNum > totalDaysInMonth) {
            nextDayNum = 1;
            nextRowIndex = nextRowIndex + 1;
        }

        if (nextRowIndex >= tableData.length) return;

        const nextStaffId = tableData[nextRowIndex]?.staff_id;
        if (nextStaffId) {
            setTimeout(() => {
                const tdElement = document.querySelector(`td[data-staff="${nextStaffId}"][data-day="${nextDayNum}"]`);
                if (tdElement) tdElement.click();
            }, 100);
        }
    };

    const saveOverlayShift = (value, moveToNext = false) => {
        if (!overlayInput || !inputOverlayRef.current) return;

        const rawValue = value.trim();
        if (!rawValue) {
            setOverlayInput(null);
            if (moveToNext) moveToNextDay();
            return;
        }

        const isCodeValid = validShiftCodes.some(
            validCode => validCode.toUpperCase() === rawValue.toUpperCase()
        );

        if (!isCodeValid) {
            alert(`❌ کد شیفت نامعتبر است! کدهای مجاز: ${validShiftCodes.join(' , ')}`);
            setOverlayInput(null);
            return;
        }

        const exactCode = validShiftCodes.find(
            validCode => validCode.toUpperCase() === rawValue.toUpperCase()
        );

        const { staffId, day, rowIndex } = overlayInput;

        applyLocalUpdate(staffId, day - 1, exactCode);
        setOverlayInput(null);

        if (moveToNext) {
            const currentRow = tableData[rowIndex];
            const totalDaysInRow = currentRow.days.length;
            const currentDayIndex = day - 1;
            let nextStaffId = null;
            let nextDay = null;
            let nextRowIndex = null;

            if (currentDayIndex + 1 < totalDaysInRow) {
                nextStaffId = staffId;
                nextDay = day + 1;
                nextRowIndex = rowIndex;
            } else if (rowIndex + 1 < tableData.length) {
                nextStaffId = tableData[rowIndex + 1].staff_id;
                nextDay = 1;
                nextRowIndex = rowIndex + 1;
            }

            if (nextStaffId && nextDay && nextRowIndex !== null) {
                setTimeout(() => {
                    const tdElement = document.querySelector(`td[data-staff="${nextStaffId}"][data-day="${nextDay}"]`);
                    if (tdElement) tdElement.click();
                }, 100);
            }
        }
    };

    const handleOverlayKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveOverlayShift(e.target.value, true);
        } else if (e.key === 'Escape') {
            setOverlayInput(null);
        }
    };

    const actionRender = () => {
        if (loading) return null;

        const scheduleStatus = serverStatus;
        const userRole = extraProps?.userRole || '';

        return (
            <ScheduleActions
                scheduleStatus={scheduleStatus}
                userRole={userRole}
                scheduleType={scheduleType}
                onAction={async (action, reason) => {
                    if (action === 'save_draft') {
                        try {
                            const formattedData = tableData.map(row => ({
                                staff_id: row.staff_id,
                                days: row.days.map((day, idx) => {
                                    const key = `${row.staff_id}-${idx}`;
                                    const change = localChanges[key];
                                    return {
                                        day: idx + 1,
                                        shift: change ? change : (day.assigned_shifts && day.assigned_shifts.length > 0 ? day.assigned_shifts[0] : '-')
                                    };
                                })
                            }));

                            await api.post('/api/save-schedule/', {
                                ward_id: wardId,
                                data: formattedData,
                                year: year,
                                month: month,
                                schedule_type: scheduleType,
                                ward_notes: wardNotes
                            });

                            const successDiv = document.createElement('div');
                            successDiv.id = 'schedule-success-overlay';
                            successDiv.className = 'modal-overlay';
                            successDiv.innerHTML = `
                                <div class="modal-card">
                                    <div class="modal-icon">💾</div>
                                    <div class="modal-title">برنامه با موفقیت به عنوان پیش‌نویس ذخیره شد!</div>
                                    <button class="btn btn-primary" onclick="document.getElementById('schedule-success-overlay').remove();">
                                        باشه
                                    </button>
                                </div>
                            `;
                            document.body.appendChild(successDiv);

                            await loadSchedule();
                            setForceRerender(prev => prev + 1);
                        } catch (err) {
                            console.error('خطا در ذخیره موقت:', err);
                            alert(err.response?.data?.error || 'خطا در ذخیره موقت');
                        }
                        return;
                    }

                    if (action === 'approve' && userRole === 'head') {
                        try {
                            const formattedData = tableData.map(row => ({
                                staff_id: row.staff_id,
                                days: row.days.map((day, idx) => {
                                    const key = `${row.staff_id}-${idx}`;
                                    const change = localChanges[key];
                                    return {
                                        day: idx + 1,
                                        shift: change ? change : (day.assigned_shifts && day.assigned_shifts.length > 0 ? day.assigned_shifts[0] : '-')
                                    };
                                })
                            }));

                            await api.post('/api/save-schedule/', {
                                ward_id: wardId,
                                data: formattedData,
                                year: year,
                                month: month,
                                schedule_type: scheduleType,
                                ward_notes: wardNotes
                            });

                            setLocalChanges({});
                        } catch (err) {
                            console.error('خطا در ذخیره تغییرات:', err);
                            alert('❌ خطا در ذخیره تغییرات. عملیات تایید لغو شد.');
                            return;
                        }

                        const loadingDiv = document.createElement('div');
                        loadingDiv.id = 'schedule-saving-overlay';
                        loadingDiv.className = 'modal-overlay';
                        loadingDiv.innerHTML = `
                            <div class="modal-card">
                                <div class="modal-icon">⏳</div>
                                <div class="modal-title">در حال ارسال برنامه به سوپروایزر...</div>
                                <div class="modal-message">لطفاً صبر کنید</div>
                            </div>
                        `;
                        document.body.appendChild(loadingDiv);
                    }

                    try {
                        if (action === 'approve' && userRole === 'head') {
                            await api.post('/api/finalize-schedule/', {
                                ward_id: wardId,
                                year: year,
                                month: month,
                                schedule_type: scheduleType,
                                ward_notes: wardNotes
                            });
                        }

                        const res = await api.post('/api/transition-status/', {
                            ward_id: wardId,
                            year: year,
                            month: month,
                            schedule_type: scheduleType,
                            action: action,
                            reason: reason || ''
                        });

                        const loadingOverlay = document.getElementById('schedule-saving-overlay');
                        if (loadingOverlay) loadingOverlay.remove();

                        let successMessage = '';
                        let successIcon = '';

                        // ✅ استفاده از SCHEDULE_TYPE_META
                        const typeLabel = SCHEDULE_TYPE_META[scheduleType]?.shortLabel || 'اصلی';

                        if (action === 'approve' && userRole === 'head') {
                            successMessage = `برنامه ${typeLabel} با موفقیت به سوپروایزر ارسال شد!`;
                            successIcon = '✅';
                        } else if (action === 'approve' && userRole === 'supervisor') {
                            successMessage = `برنامه ${typeLabel} با موفقیت به مترون ارسال شد!`;
                            successIcon = '✅';
                        } else if (action === 'approve' && userRole === 'admin') {
                            successMessage = `برنامه ${typeLabel} با موفقیت قفل شد!`;
                            successIcon = '🔒';
                        } else if (action === 'reject' && userRole === 'supervisor') {
                            successMessage = `برنامه ${typeLabel} با موفقیت به سرپرستار بازگردانده شد!`;
                            successIcon = '🔄';
                        } else if (action === 'reject' && userRole === 'admin') {
                            successMessage = `برنامه ${typeLabel} با موفقیت به سوپروایزر بازگردانده شد!`;
                            successIcon = '🔄';
                        } else if (action === 'reset' && userRole === 'admin') {
                            successMessage = `برنامه ${typeLabel} با موفقیت به حالت اولیه بازگردانده شد!`;
                            successIcon = '♻️';
                        } else {
                            successMessage = res.data.message || 'عملیات با موفقیت انجام شد!';
                            successIcon = '✅';
                        }

                        const successDiv = document.createElement('div');
                        successDiv.id = 'schedule-success-overlay';
                        successDiv.className = 'modal-overlay';
                        successDiv.innerHTML = `
                            <div class="modal-card">
                                <div class="modal-icon">${successIcon}</div>
                                <div class="modal-title">${successMessage}</div>
                                <button class="btn btn-primary" onclick="document.getElementById('schedule-success-overlay').remove();">
                                    باشه
                                </button>
                            </div>
                        `;
                        document.body.appendChild(successDiv);

                        if (action === 'approve' && userRole === 'head') {
                            setScheduleSource('final');
                        }

                        await loadSchedule();
                        setForceRerender(prev => prev + 1);
                    } catch (err) {
                        const loadingOverlay = document.getElementById('schedule-saving-overlay');
                        if (loadingOverlay) loadingOverlay.remove();

                        console.error('خطا در تغییر وضعیت:', err);
                        alert(err.response?.data?.error || 'خطا در تغییر وضعیت');
                    }
                }}
            />
        );
    };

    const renderApiError = () => {
        if (!apiError) return null;

        return (
            <div style={{
                padding: '20px 24px',
                background: 'linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%)',
                border: '2px solid #FCA5A5',
                borderRadius: '12px',
                margin: '16px 0',
                color: '#991B1B',
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                flexWrap: 'wrap',
                boxShadow: '0 4px 12px rgba(220, 38, 38, 0.1)',
            }}>
                <span style={{ fontSize: '36px', flexShrink: 0 }}>❌</span>
                <div style={{ flex: 1, minWidth: '200px' }}>
                    <div style={{
                        fontSize: '16px',
                        fontWeight: '800',
                        marginBottom: '6px',
                    }}>
                        خطا در دریافت اطلاعات از سرور
                    </div>
                    <div style={{
                        fontSize: '13px',
                        fontWeight: '600',
                        opacity: 0.85,
                        lineHeight: '1.6',
                    }}>
                        {apiError.message}
                        {apiError.status && (
                            <span style={{
                                marginRight: '8px',
                                padding: '2px 8px',
                                background: '#991B1B',
                                color: 'white',
                                borderRadius: '6px',
                                fontSize: '11px',
                                fontWeight: '700',
                            }}>
                                کد خطا: {apiError.status}
                            </span>
                        )}
                    </div>
                </div>
                <button
                    onClick={() => {
                        setApiError(null);
                        setForceRerender(prev => prev + 1);
                    }}
                    style={{
                        padding: '10px 20px',
                        background: '#991B1B',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontWeight: '700',
                        fontSize: '14px',
                        transition: 'background 0.15s',
                        fontFamily: 'inherit',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#7F1D1D'}
                    onMouseLeave={(e) => e.currentTarget.style.background = '#991B1B'}
                >
                    🔄 تلاش مجدد
                </button>
            </div>
        );
    };

    if (loading) {
        return (
            <div className={`schedule-container ${getRoleClass()}`}>
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: '60vh',
                    padding: '80px 20px',
                    gap: '24px',
                }}>
                    <div
                        style={{
                            width: '70px',
                            height: '70px',
                            border: '6px solid #E5E7EB',
                            borderTop: '6px solid #3B82F6',
                            borderRadius: '50%',
                            animation: 'spin 0.8s linear infinite',
                        }}
                    ></div>

                    <div style={{
                        fontSize: '18px',
                        fontWeight: '700',
                        color: '#374151',
                        textAlign: 'center',
                    }}>
                        ⏳ در حال بارگذاری برنامه...
                    </div>

                    <div style={{
                        fontSize: '13px',
                        color: '#6B7280',
                        fontWeight: '600',
                        textAlign: 'center',
                        maxWidth: '400px',
                        lineHeight: '1.6',
                    }}>
                        لطفاً چند لحظه صبر کنید
                    </div>
                </div>

                <style>{`
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        );
    }

    if (isLocked) {
        return (
            <div className={`schedule-container ${getRoleClass()}`}>
                <div className="schedule-lock-warning">
                    🔒 برنامه {SCHEDULE_TYPE_META[scheduleType]?.shortLabel || 'اصلی'} {monthName} {year} توسط مترون تایید نهایی شده و <u>قفل</u> شده است.
                    <br />
                    <span>امکان ثبت یا تغییر هیچ شیفتی وجود ندارد.</span>
                </div>

                <div className="schedule-header">
                    <div style={{ width: '150px' }}></div>
                    <h1 className="schedule-title">
                        {title}{getScheduleTypeLabel()}
                    </h1>
                    <div className="schedule-header-actions">
                        <button onClick={handleExportExcel} className="btn btn-success btn-sm">📊 اکسل</button>
                        <button onClick={handleExportPDF} className="btn btn-danger btn-sm">📄 PDF</button>
                    </div>
                </div>

                {wardInfo && (
                    <div className="schedule-ward-info">
                        <div className="schedule-ward-info-left">
                            {wardInfo.hospital_logo && (
                                <img src={getMediaUrl(wardInfo.hospital_logo)} alt="آرم بیمارستان" />
                            )}
                            <div>
                                <div className="schedule-ward-name">{wardInfo.hospital_name || 'نام بیمارستان'}</div>
                            </div>
                        </div>

                        <div className="schedule-ward-info-center">
                            <div className="schedule-ward-hospital">{wardInfo.hospital_name || 'نام بیمارستان'}</div>
                            <div className="schedule-ward-details">
                                <span className="schedule-ward-title">{wardInfo.name}</span>
                                {wardInfo.sub_ward_name && <span> - {wardInfo.sub_ward_name}</span>}
                                <span> | {monthName} {year}</span>
                            </div>
                        </div>

                        <div className="schedule-ward-info-right">
                            <div>
                                <div className="schedule-ward-university">{wardInfo.university_name || 'نام دانشگاه'}</div>
                            </div>
                            {wardInfo.university_logo && (
                                <img src={getMediaUrl(wardInfo.university_logo)} alt="آرم دانشگاه" />
                            )}
                        </div>
                    </div>
                )}

                {renderApiError()}

                <div className="schedule-table-wrapper">
                    <table
                        className="schedule-table"
                        style={{ borderCollapse: 'separate', borderSpacing: 0, width: '100%', minWidth: '1200px' }}
                    >
                        <thead>
                            <tr>
                                <th className="schedule-th-sticky">ردیف</th>
                                <th className="schedule-th-sticky">نام و نام خانوادگی</th>
                                <th className="schedule-th-sticky">سمت</th>
                                <th className="schedule-th-sticky">وضعیت استخدام</th>
                                {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => {
                                    const dayIndex = offset + (day - 1);
                                    return (
                                        <th key={day} className="schedule-th-day">
                                            <div>{day}</div>
                                            <div className="schedule-th-day-name">{weekdays[dayIndex % 7] || '-'}</div>
                                        </th>
                                    );
                                })}
                                <th className="schedule-th-stat">صبح</th>
                                <th className="schedule-th-stat">عصر</th>
                                <th className="schedule-th-stat">شب</th>
                                <th className="schedule-th-stat">مرخصی</th>
                                <th className="schedule-th-stat">آف</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tableData.map((row, rowIndex) => {
                                const isHead = row.is_head === true;
                                return (
                                <tr
                                    key={row.staff_id}
                                    style={isHead ? {
                                        background: 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)',
                                        borderBottom: '3px solid #F59E0B',
                                    } : {}}
                                >
                                    <td className="schedule-td-sticky" style={isHead ? { fontWeight: '800', fontSize: '16px' } : {}}>
                                        {isHead ? '👑' : rowIndex + 1}
                                    </td>
                                    <td className="schedule-td-name" style={isHead ? { fontWeight: '800', color: '#92400E' } : {}}>
                                        {isHead && '👨‍⚕️ '}
                                        {row.staff_name}
                                        {isHead && (
                                            <span style={{
                                                marginRight: '8px',
                                                padding: '2px 8px',
                                                background: '#F59E0B',
                                                color: 'white',
                                                borderRadius: '10px',
                                                fontSize: '10px',
                                                fontWeight: '700',
                                            }}>
                                                سرپرستار
                                            </span>
                                        )}
                                    </td>
                                    <td className="schedule-td-sticky">{row.position_label || '-'}</td>
                                    <td className="schedule-td-sticky">{row.employment_status || '-'}</td>
                                    {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => {
                                        const cell = row.days[day - 1];
                                        if (!cell) return <td key={day} className="schedule-td-cell">-</td>;

                                        return (
                                            <td key={day} className="schedule-td-cell">
                                                {cell.assigned_shifts && cell.assigned_shifts.length > 0 ? (
                                                    cell.assigned_shifts.map((shift, idx) => (
                                                        <span key={idx} className={`schedule-shift-badge shift-${shift}`}>
                                                            {shift}
                                                        </span>
                                                    ))
                                                ) : (
                                                    <span className="schedule-empty">-</span>
                                                )}
                                            </td>
                                        );
                                    })}
                                    <td className="schedule-td-stat">{row.total_m}</td>
                                    <td className="schedule-td-stat">{row.total_e}</td>
                                    <td className="schedule-td-stat">{row.total_n}</td>
                                    <td className="schedule-td-stat">{row.total_h}</td>
                                    <td className="schedule-td-stat">{row.total_off}</td>
                                </tr>
                                );
                            })}

                            <tr className="schedule-stat-row schedule-stat-m">
                                <td colSpan="4" className="schedule-stat-label">☀️ صبح (M) عادی: {targetM} / تعطیل: {holidayTargetM}</td>
                                {dailyM.map((item, idx) => {
                                    const dayData = tableData.length > 0 ? tableData[0].days[idx] : null;
                                    const isHolidayOrFriday = dayData?.is_holiday || (weekdays[(offset + idx) % 7] === 'جمعه');
                                    const target = isHolidayOrFriday ? holidayTargetM : targetM;
                                    let bgColor = '#ffffff';
                                    if (item.count < target) bgColor = '#fee2e2';
                                    else if (item.count > target) bgColor = '#ffedd5';
                                    return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                                })}
                                <td className="schedule-stat-total">{tableData.reduce((sum, row) => sum + (row.total_m || 0), 0)}</td>
                                <td colSpan="4"></td>
                            </tr>

                            <tr className="schedule-stat-row schedule-stat-e">
                                <td colSpan="4" className="schedule-stat-label">🌅 عصر (E) عادی: {targetE} / تعطیل: {holidayTargetE}</td>
                                {dailyE.map((item, idx) => {
                                    const dayData = tableData.length > 0 ? tableData[0].days[idx] : null;
                                    const isHolidayOrFriday = dayData?.is_holiday || (weekdays[(offset + idx) % 7] === 'جمعه');
                                    const target = isHolidayOrFriday ? holidayTargetE : targetE;
                                    let bgColor = '#ffffff';
                                    if (item.count < target) bgColor = '#fee2e2';
                                    else if (item.count > target) bgColor = '#ffedd5';
                                    return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                                })}
                                <td className="schedule-stat-total">{tableData.reduce((sum, row) => sum + (row.total_e || 0), 0)}</td>
                                <td colSpan="4"></td>
                            </tr>

                            <tr className="schedule-stat-row schedule-stat-n">
                                <td colSpan="4" className="schedule-stat-label">🌙 شب (N) عادی: {targetN} / تعطیل: {holidayTargetN}</td>
                                {dailyN.map((item, idx) => {
                                    const dayData = tableData.length > 0 ? tableData[0].days[idx] : null;
                                    const isHolidayOrFriday = dayData?.is_holiday || (weekdays[(offset + idx) % 7] === 'جمعه');
                                    const target = isHolidayOrFriday ? holidayTargetN : targetN;
                                    let bgColor = '#ffffff';
                                    if (item.count < target) bgColor = '#fee2e2';
                                    else if (item.count > target) bgColor = '#ffedd5';
                                    return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                                })}
                                <td className="schedule-stat-total">{tableData.reduce((sum, row) => sum + (row.total_n || 0), 0)}</td>
                                <td colSpan="4"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div className="schedule-codes-card">
                    <h4 className="schedule-codes-title">کدهای شیفت استفاده شده در این برنامه:</h4>
                    <div className="schedule-codes-list">
                        {usedShiftCodes.length > 0 ? (
                            usedShiftCodes.map(code => {
                                const codeInfo = shiftCodes.find(sc => sc.code === code);
                                return (
                                    <span key={code} className="schedule-code-badge">
                                        {code} {codeInfo ? `(${codeInfo.label})` : ''}
                                    </span>
                                );
                            })
                        ) : (
                            <span className="schedule-codes-empty">هیچ کدی در این برنامه استفاده نشده است.</span>
                        )}
                    </div>
                </div>

                <div className="schedule-notes-card">
                    <h4 className="schedule-notes-title">📋 نکات مهم بخش:</h4>
                    <div className="schedule-notes-content">
                        {wardNotes || 'نکته‌ای ثبت نشده است'}
                    </div>
                </div>

                <div className="schedule-signatures">
                    <div className="schedule-signature-box">
                        <div className="schedule-signature-title">سرپرستار</div>
                        {headSignature ? (
                            <img src={getMediaUrl(headSignature)} alt="امضای سرپرستار" />
                        ) : (
                            <div className="schedule-signature-empty">امضا ثبت نشده است</div>
                        )}
                    </div>
                    <div className="schedule-signature-box">
                        <div className="schedule-signature-title">مدیر خدمات پرستاری</div>
                        {matronSignature ? (
                            <img src={getMediaUrl(matronSignature)} alt="امضای مدیر خدمات پرستاری" />
                        ) : (
                            <div className="schedule-signature-empty">امضا ثبت نشده است</div>
                        )}
                    </div>
                </div>

                <div className="schedule-actions-wrapper">
                    {actionRender()}
                </div>

                {(matronFeedback || supervisorFeedback) && (
                    <div className="schedule-feedback-card">
                        <strong className="schedule-feedback-title">🔔 برنامه بازگردانده شده است!</strong>

                        {supervisorFeedback && (
                            <div className="schedule-feedback-item">
                                <div className="schedule-feedback-author">
                                    👤 بازگردانی توسط سوپروایزر: {supervisorFeedbackBy ? `(${supervisorFeedbackBy})` : ''}
                                </div>
                                <div className="schedule-feedback-text">{supervisorFeedback}</div>
                            </div>
                        )}

                        {matronFeedback && (
                            <div className="schedule-feedback-item">
                                <div className="schedule-feedback-author">
                                    👤 بازگردانی توسط مترون: {matronFeedbackBy ? `(${matronFeedbackBy})` : ''}
                                </div>
                                <div className="schedule-feedback-text">{matronFeedback}</div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className={`schedule-container ${getRoleClass()}`}>
            <div className="schedule-header">
                <div style={{ width: '150px' }}></div>
                <h1 className="schedule-title">
                    {title}{getScheduleTypeLabel()}
                </h1>
                <div className="schedule-header-actions">
                    {mode === 'head' && !isLocked && (
                        <button
                            onClick={() => setShowStaffManagement(true)}
                            className="btn btn-sm"
                            style={{
                                background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                                color: 'white',
                                border: 'none',
                                padding: '8px 14px',
                                borderRadius: '8px',
                                fontWeight: '700',
                                fontFamily: 'inherit',
                                cursor: 'pointer',
                                fontSize: '13px',
                            }}
                            title="حذف یا بازگرداندن پرسنل به برنامه"
                        >
                            👥 مدیریت پرسنل
                        </button>
                    )}

                    {isLocked && (
                        <>
                            <button onClick={handleExportExcel} className="btn btn-success btn-sm">📊 اکسل</button>
                            <button onClick={handleExportPDF} className="btn btn-danger btn-sm">📄 PDF</button>
                        </>
                    )}
                </div>
            </div>

            {wardInfo && (
                <div className="schedule-ward-info">
                    <div className="schedule-ward-info-left">
                        {wardInfo.hospital_logo && (
                            <img src={getMediaUrl(wardInfo.hospital_logo)} alt="آرم بیمارستان" />
                        )}
                        <div>
                            <div className="schedule-ward-name">{wardInfo.hospital_name || 'نام بیمارستان'}</div>
                        </div>
                    </div>

                    <div className="schedule-ward-info-center">
                        <div className="schedule-ward-hospital">{wardInfo.hospital_name || 'نام بیمارستان'}</div>
                        <div className="schedule-ward-details">
                            <span className="schedule-ward-title">{wardInfo.name}</span>
                            {wardInfo.sub_ward_name && <span> - {wardInfo.sub_ward_name}</span>}
                            <span> | {monthName} {year}</span>
                        </div>
                    </div>

                    <div className="schedule-ward-info-right">
                        <div>
                            <div className="schedule-ward-university">{wardInfo.university_name || 'نام دانشگاه'}</div>
                        </div>
                        {wardInfo.university_logo && (
                            <img src={getMediaUrl(wardInfo.university_logo)} alt="آرم دانشگاه" />
                        )}
                    </div>
                </div>
            )}

            {mode === 'head' && (
                <div className="schedule-source-selector" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label>📋 نوع برنامه:</label>
                        <select
                            value={scheduleType}
                            onChange={(e) => {
                                const newType = e.target.value;
                                setScheduleType(newType);
                                // ✅ فقط main سورس staff_request داره
                                if (newType !== 'main' && scheduleSource === 'staff_request') {
                                    setScheduleSource('final');
                                }
                            }}
                            className="input"
                        >
                            {SCHEDULE_TYPES.map(t => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                        </select>
                    </div>

                    {/* ✅ سلکتور دوم با لیبل پویا بر اساس نوع برنامه */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label>📂 نوع پیش‌نویس:</label>
                        <select
                            value={scheduleSource}
                            onChange={(e) => setScheduleSource(e.target.value)}
                            className="input"
                        >
                            {scheduleType === 'main' ? (
                                <>
                                    <option value="final">📋 برنامه نهایی (Final)</option>
                                    <option value="staff_request">📝 برنامه درخواستی پرستار</option>
                                    <option value="head_draft">✍️ پیش‌نویس سرپرستار</option>
                                    <option value="ai_draft">🤖 پیش‌نویس هوش مصنوعی</option>
                                </>
                            ) : (
                                <>
                                    <option value="final">
                                        📋 برنامه نهایی {getScheduleTypeShortLabel()} (Final)
                                    </option>
                                    <option value="head_draft">
                                        ✍️ پیش‌نویس {getScheduleTypeShortLabel()} سرپرستار
                                    </option>
                                    <option value="ai_draft">
                                        🤖 پیش‌نویس {getScheduleTypeShortLabel()} هوش مصنوعی
                                    </option>
                                </>
                            )}
                        </select>
                    </div>
                </div>
            )}

            {renderApiError()}

            <div className="schedule-table-wrapper">
                <table
                    className="schedule-table"
                    style={{ borderCollapse: 'separate', borderSpacing: 0, width: '100%', minWidth: '1200px' }}
                >
                    <thead>
                        <tr>
                            <th className="schedule-th-sticky">ردیف</th>
                            <th className="schedule-th-sticky">نام و نام خانوادگی</th>
                            <th className="schedule-th-sticky">سمت</th>
                            <th className="schedule-th-sticky">وضعیت استخدام</th>
                            {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => {
                                const dayIndex = offset + (day - 1);
                                return (
                                    <th key={day} className="schedule-th-day">
                                        <div>{day}</div>
                                        <div className="schedule-th-day-name">{weekdays[dayIndex % 7] || '-'}</div>
                                    </th>
                                );
                            })}
                            <th className="schedule-th-stat">صبح</th>
                            <th className="schedule-th-stat">عصر</th>
                            <th className="schedule-th-stat">شب</th>
                            <th className="schedule-th-stat">مرخصی</th>
                            <th className="schedule-th-stat">آف</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tableData.map((row, rowIndex) => {
                            const isHead = row.is_head === true;
                            return (
                            <tr
                                key={row.staff_id}
                                style={isHead ? {
                                    background: 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)',
                                    borderBottom: '3px solid #F59E0B',
                                } : {}}
                            >
                                <td className="schedule-td-sticky" style={isHead ? { fontWeight: '800', fontSize: '16px' } : {}}>
                                    {isHead ? '👑' : rowIndex + 1}
                                </td>
                                <td className="schedule-td-name" style={isHead ? { fontWeight: '800', color: '#92400E' } : {}}>
                                    {isHead && '👨‍⚕️ '}
                                    {row.staff_name}
                                    {isHead && (
                                        <span style={{
                                            marginRight: '8px',
                                            padding: '2px 8px',
                                            background: '#F59E0B',
                                            color: 'white',
                                            borderRadius: '10px',
                                            fontSize: '10px',
                                            fontWeight: '700',
                                        }}>
                                            سرپرستار
                                        </span>
                                    )}
                                </td>
                                <td className="schedule-td-sticky">{row.position_label || '-'}</td>
                                <td className="schedule-td-sticky">{row.employment_status || '-'}</td>
                                {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => {
                                    const cell = row.days[day - 1];
                                    if (!cell) return <td key={day} className="schedule-td-cell">-</td>;

                                    const isViewOnly = (mode === 'supervisor' || mode === 'matron');
                                    const displayShift = (cell.assigned_shifts && cell.assigned_shifts.length > 0)
                                        ? cell.assigned_shifts[0]
                                        : '';

                                    return (
                                        <td
                                            key={day}
                                            data-staff={row.staff_id}
                                            data-day={day}
                                            className={`schedule-td-cell ${isViewOnly ? 'view-only' : 'clickable'} ${cell.is_weekend ? 'weekend' : ''} ${cell.is_holiday ? 'holiday' : ''} ${isHead ? 'head-row' : ''}`}
                                            onClick={isViewOnly ? undefined : (e) => handleCellClick(row.staff_id, day, rowIndex, e)}
                                        >
                                            {displayShift ? (
                                                <span className={`schedule-shift-badge shift-${displayShift}`}>
                                                    {displayShift}
                                                </span>
                                            ) : (
                                                <span className="schedule-empty">-</span>
                                            )}
                                        </td>
                                    );
                                })}
                                <td className="schedule-td-stat">{row.total_m}</td>
                                <td className="schedule-td-stat">{row.total_e}</td>
                                <td className="schedule-td-stat">{row.total_n}</td>
                                <td className="schedule-td-stat">{row.total_h}</td>
                                <td className="schedule-td-stat">{row.total_off}</td>
                            </tr>
                            );
                        })}

                        <tr className="schedule-stat-row schedule-stat-m">
                            <td colSpan="4" className="schedule-stat-label">☀️ صبح (M) عادی: {targetM} / تعطیل: {holidayTargetM}</td>
                            {dailyM.map((item, idx) => {
                                const dayData = tableData.length > 0 ? tableData[0].days[idx] : null;
                                const isHolidayOrFriday = dayData?.is_holiday || (weekdays[(offset + idx) % 7] === 'جمعه');
                                const target = isHolidayOrFriday ? holidayTargetM : targetM;
                                let bgColor = '#ffffff';
                                if (item.count < target) bgColor = '#fee2e2';
                                else if (item.count > target) bgColor = '#ffedd5';
                                return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                            })}
                            <td className="schedule-stat-total">{tableData.reduce((sum, row) => sum + (row.total_m || 0), 0)}</td>
                            <td colSpan="4"></td>
                        </tr>

                        <tr className="schedule-stat-row schedule-stat-e">
                            <td colSpan="4" className="schedule-stat-label">🌅 عصر (E) عادی: {targetE} / تعطیل: {holidayTargetE}</td>
                            {dailyE.map((item, idx) => {
                                const dayData = tableData.length > 0 ? tableData[0].days[idx] : null;
                                const isHolidayOrFriday = dayData?.is_holiday || (weekdays[(offset + idx) % 7] === 'جمعه');
                                const target = isHolidayOrFriday ? holidayTargetE : targetE;
                                let bgColor = '#ffffff';
                                if (item.count < target) bgColor = '#fee2e2';
                                else if (item.count > target) bgColor = '#ffedd5';
                                return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                            })}
                            <td className="schedule-stat-total">{tableData.reduce((sum, row) => sum + (row.total_e || 0), 0)}</td>
                            <td colSpan="4"></td>
                        </tr>

                        <tr className="schedule-stat-row schedule-stat-n">
                            <td colSpan="4" className="schedule-stat-label">🌙 شب (N) عادی: {targetN} / تعطیل: {holidayTargetN}</td>
                            {dailyN.map((item, idx) => {
                                const dayData = tableData.length > 0 ? tableData[0].days[idx] : null;
                                const isHolidayOrFriday = dayData?.is_holiday || (weekdays[(offset + idx) % 7] === 'جمعه');
                                const target = isHolidayOrFriday ? holidayTargetN : targetN;
                                let bgColor = '#ffffff';
                                if (item.count < target) bgColor = '#fee2e2';
                                else if (item.count > target) bgColor = '#ffedd5';
                                return <td key={idx} className="schedule-stat-cell" style={{ backgroundColor: bgColor }}>{item.count}</td>;
                            })}
                            <td className="schedule-stat-total">{tableData.reduce((sum, row) => sum + (row.total_n || 0), 0)}</td>
                            <td colSpan="4"></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div className="schedule-codes-card">
                <h4 className="schedule-codes-title">کدهای شیفت استفاده شده در این برنامه:</h4>
                <div className="schedule-codes-list">
                    {usedShiftCodes.length > 0 ? (
                        usedShiftCodes.map(code => {
                            const codeInfo = shiftCodes.find(sc => sc.code === code);
                            return (
                                <span key={code} className="schedule-code-badge">
                                    {code} {codeInfo ? `(${codeInfo.label})` : ''}
                                </span>
                            );
                        })
                    ) : (
                        <span className="schedule-codes-empty">هیچ کدی در این برنامه استفاده نشده است.</span>
                    )}
                </div>
            </div>

            <div className="schedule-notes-card">
                <h4 className="schedule-notes-title">📋 نکات مهم بخش:</h4>

                {mode === 'head' && !isLocked && !approvedByHead ? (
                    <textarea
                        value={wardNotes}
                        onChange={(e) => setWardNotes(e.target.value)}
                        placeholder="مثلاً: کنفرانس درون بخشی روز ۱۵، جلسه هماهنگی روز ۲۰، بیمار خاص در بخش..."
                        className="textarea"
                    />
                ) : (
                    <div className="schedule-notes-content">
                        {wardNotes || 'نکته‌ای ثبت نشده است'}
                    </div>
                )}
            </div>

            <div className="schedule-signatures">
                <div className="schedule-signature-box">
                    <div className="schedule-signature-title">سرپرستار</div>
                    {headSignature ? (
                        <img src={getMediaUrl(headSignature)} alt="امضای سرپرستار" />
                    ) : (
                        <div className="schedule-signature-empty">امضا ثبت نشده است</div>
                    )}
                </div>
                <div className="schedule-signature-box">
                    <div className="schedule-signature-title">مدیر خدمات پرستاری</div>
                    {matronSignature ? (
                        <img src={getMediaUrl(matronSignature)} alt="امضای مدیر خدمات پرستاری" />
                    ) : (
                        <div className="schedule-signature-empty">امضا ثبت نشده است</div>
                    )}
                </div>
            </div>

            {actionRender()}

            {(matronFeedback || supervisorFeedback) && (
                <div className="schedule-feedback-card">
                    <strong className="schedule-feedback-title">🔔 برنامه بازگردانده شده است!</strong>

                    {supervisorFeedback && (
                        <div className="schedule-feedback-item">
                            <div className="schedule-feedback-author">
                                👤 بازگردانی توسط سوپروایزر: {supervisorFeedbackBy ? `(${supervisorFeedbackBy})` : ''}
                            </div>
                            <div className="schedule-feedback-text">{supervisorFeedback}</div>
                        </div>
                    )}

                    {matronFeedback && (
                        <div className="schedule-feedback-item">
                            <div className="schedule-feedback-author">
                                👤 بازگردانی توسط مترون: {matronFeedbackBy ? `(${matronFeedbackBy})` : ''}
                            </div>
                            <div className="schedule-feedback-text">{matronFeedback}</div>
                        </div>
                    )}
                </div>
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
                            onKeyDown={handleOverlayKeyDown}
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

            {showStaffManagement && (
                <StaffManagementModal
                    wardId={wardId}
                    year={year}
                    month={month}
                    scheduleType={scheduleType}
                    wardName={wardInfo?.name || ''}
                    onClose={() => setShowStaffManagement(false)}
                    onUpdate={() => {
                        loadSchedule();
                        setForceRerender(prev => prev + 1);
                    }}
                />
            )}
        </div>
    );
}

export default ScheduleBase;