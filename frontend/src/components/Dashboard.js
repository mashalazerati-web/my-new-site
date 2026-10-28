// src/components/Dashboard.js
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import Announcements from './Announcements';
import PreviousSchedules from './PreviousSchedules';
import { MONTH_NAMES, WEEKDAYS } from '../constants/persianCalendar';
import '../styles/index.css';
import { createPortal } from 'react-dom';


function Dashboard() {
    const [user, setUser] = useState(null);
    const [userProfile, setUserProfile] = useState(null);   // ✅ جدید
    const [calendar, setCalendar] = useState([]);
    const [monthName, setMonthName] = useState('');
    const [year, setYear] = useState(null);
    const [month, setMonth] = useState(null);

    const [isMonthLocked, setIsMonthLocked] = useState(false);
    const [isUserLocked, setIsUserLocked] = useState(false);
    const [isNewUserAfterLock, setIsNewUserAfterLock] = useState(false);
    const [wardId, setWardId] = useState(null);

    const [userWards, setUserWards] = useState([]);
    const [selectedWardId, setSelectedWardId] = useState(null);

    const [activeTab, setActiveTab] = useState('request');

    const [overlayInput, setOverlayInput] = useState(null);
    const inputOverlayRef = useRef(null);
    const [shiftCodes, setShiftCodes] = useState([]);

    const [localChanges, setLocalChanges] = useState({});
    const [isSavingToServer, setIsSavingToServer] = useState(false);

    const navigate = useNavigate();
    const [filterText, setFilterText] = useState('');
    const [siteSettings, setSiteSettings] = useState(null);

    const isSavingRef = useRef(false);

    useEffect(() => {
        loadUser();
        loadSiteSettings();
    }, []);

    const loadSiteSettings = async () => {
        try {
            const res = await api.get('/api/site-settings/');
            setSiteSettings(res.data);
        } catch (err) {
            console.error('خطا در دریافت تنظیمات سایت:', err);
        }
    };

    useEffect(() => {
        if (year && month && selectedWardId) {
            if (activeTab === 'request') {
                loadShiftCodes(selectedWardId);
            }
            checkLockStatus();
        }
    }, [year, month, selectedWardId, activeTab]);

    const loadUser = async () => {
        try {
            const res = await api.get('/api/users/me/');
            setUser(res.data);

            const profileRes = await api.get('/api/profiles/');
            const profile = profileRes.data.find(p => p.user?.username === res.data.username);

            // ✅ ذخیره profile برای نمایش سمت
            if (profile) {
                setUserProfile(profile);
            }

            if (profile && profile.ward) {
                setWardId(profile.ward);

                try {
                    const wardsRes = await api.get('/api/my-wards/');
                    const wardsList = wardsRes.data || [];
                    setUserWards(wardsList);

                    if (wardsList.length > 0) {
                        const primaryWard = wardsList.find(w => w.is_primary) || wardsList[0];
                        setSelectedWardId(primaryWard.id);
                        await loadCalendar(null, null, primaryWard.id);
                        await loadShiftCodes(primaryWard.id);
                    } else {
                        setSelectedWardId(profile.ward);
                        await loadCalendar(null, null, profile.ward);
                        await loadShiftCodes(profile.ward);
                    }
                } catch (err) {
                    console.error('خطا در دریافت بخش‌ها:', err);
                    setSelectedWardId(profile.ward);
                    await loadCalendar(null, null, profile.ward);
                    await loadShiftCodes(profile.ward);
                }
            }
        } catch {
            navigate('/login');
        }
    };

    const loadCalendar = async (yearParam = null, monthParam = null, wardIdParam = null) => {
        const effectiveWardId = wardIdParam || selectedWardId || wardId;
        if (!effectiveWardId) return;

        try {
            let url = `/api/monthly/?ward_id=${effectiveWardId}`;
            if (yearParam && monthParam) {
                url += `&year=${yearParam}&month=${monthParam}`;
            }
            const res = await api.get(url);
            const data = res.data;

            setYear(data.year);
            setMonth(data.month);
            setMonthName(MONTH_NAMES[data.month] || '');

            const days = data.days || [];
            setCalendar(days);
            setLocalChanges({});

            setIsUserLocked(data.is_locked || false);
        } catch (err) {
            console.error('خطا در دریافت تقویم:', err);
            setCalendar([]);
            setIsUserLocked(false);
        }
    };

    const loadShiftCodes = async (wardIdParam = null) => {
        try {
            let url = '/api/shift-codes/';
            const effectiveWardId = wardIdParam || selectedWardId;
            if (effectiveWardId) {
                url += `?ward_id=${effectiveWardId}`;
            }
            const res = await api.get(url);
            setShiftCodes(res.data);
        } catch (err) {
            console.error("خطا در دریافت کدهای شیفت", err);
        }
    };

    const checkLockStatus = async () => {
        const effectiveWardId = selectedWardId || wardId;
        if (!effectiveWardId || !year || !month) return;
        try {
            const res = await api.get(`/api/head-schedule/?ward_id=${effectiveWardId}&year=${year}&month=${month}`);
            const data = res.data;
            const serverStatus = data.status || 'DRAFT';

            if (serverStatus === 'DRAFT') {
                setIsMonthLocked(false);
                setIsNewUserAfterLock(false);
                return;
            }

            setIsMonthLocked(true);
            setIsNewUserAfterLock(true);
        } catch (err) {
            console.error('خطا در بررسی وضعیت قفل:', err);
            setIsMonthLocked(false);
            setIsNewUserAfterLock(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        navigate('/login');
    };

    const handleWardChange = async (e) => {
        const newWardId = parseInt(e.target.value);
        setSelectedWardId(newWardId);
        await loadCalendar(null, null, newWardId);
        await loadShiftCodes(newWardId);
    };

    const getCurrentWardName = () => {
        if (!selectedWardId || !userWards.length) return '';
        const ward = userWards.find(w => w.id === selectedWardId);
        return ward ? ward.name : '';
    };

    const handleCellClick = (dayData, event) => {
        if (!dayData || dayData.day === 0) return;
        if (isMonthLocked || isUserLocked) return;

        const rect = event.currentTarget.getBoundingClientRect();
        const changeKey = `${dayData.day}`;
        let currentValue = localChanges[changeKey] || '';

        if (!currentValue) {
            const currentRequests = dayData.requests || [];
            currentValue = currentRequests.length > 0 ? currentRequests[0].shift_type : '';
        }

        setOverlayInput({ day: dayData, rect: rect, value: currentValue });
        setFilterText('');

        setTimeout(() => {
            if (inputOverlayRef.current) {
                inputOverlayRef.current.focus();
                inputOverlayRef.current.select();
            }
        }, 10);
    };

    const moveToNextDay = () => {
        if (!overlayInput) return;
        const currentDayNum = overlayInput.day.day;
        const totalDaysInMonth = calendar.filter(d => d.day > 0).length;

        let nextDayNum = currentDayNum + 1;

        if (nextDayNum > totalDaysInMonth) {
            setOverlayInput(null);
            alert('⚠️ شما قادر به ثبت شیفت در ماه بعد نیستید. لطفاً تا شروع ماه جدید صبر کنید.');
            return;
        }

        setTimeout(() => {
            const nextTd = document.querySelector(`div[data-day="${nextDayNum}"]`);
            if (nextTd) {
                nextTd.click();
            }
        }, 200);
    };

    const saveOverlayShift = async (value, moveToNext = false) => {
        if (isSavingRef.current) return;
        if (!overlayInput) return;
        if (isMonthLocked || isUserLocked) return;

        const rawValue = value.trim();

        if (!rawValue) {
            setOverlayInput(null);
            if (moveToNext) {
                moveToNextDay();
            }
            return;
        }

        const upperValue = rawValue.toUpperCase();
        isSavingRef.current = true;

        try {
            const isValidCode = shiftCodes.some(
                code => code.code.toUpperCase() === upperValue
            );

            if (!isValidCode) {
                alert(`❌ کد "${upperValue}" معتبر نیست. کدهای مجاز: ${shiftCodes.map(c => c.code).join(' , ')}`);

                setOverlayInput(null);
                return;
            }

            const changeKey = `${overlayInput.day.day}`;
            setLocalChanges(prev => ({
                ...prev,
                [changeKey]: upperValue
            }));

            setOverlayInput(null);

            const updatedCalendar = calendar.map(item => {
                if (item.day === overlayInput.day.day) {
                    return {
                        ...item,
                        requests: [{ id: `local-${Date.now()}`, shift_type: upperValue }]
                    };
                }
                return item;
            });
            setCalendar(updatedCalendar);

            if (moveToNext) {
                moveToNextDay();
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

    const handleSubmitAll = async () => {
        if (isUserLocked) {
            alert('برنامه شما توسط سرپرستار تنظیم شده و قابل ویرایش نیست.');
            return;
        }

        const changesCount = Object.keys(localChanges).length;
        if (changesCount === 0) {
            alert('هیچ تغییر جدیدی برای ثبت وجود ندارد.');
            return;
        }

        if (!window.confirm(`آیا از ثبت ${changesCount} تغییر در سیستم اطمینان دارید؟`)) {
            return;
        }

        setIsSavingToServer(true);

        const effectiveWardId = selectedWardId || wardId;
        if (!effectiveWardId) {
            alert('❌ خطا: شناسه بخش (wardId) یافت نشد.');
            setIsSavingToServer(false);
            return;
        }

        try {
            let successCount = 0;
            let failCount = 0;
            let errorMessages = [];
            let failedDays = [];

            for (const [day, shiftType] of Object.entries(localChanges)) {
                if (!shiftType || shiftType === '' || shiftType === 'None' || shiftType === 'null' || shiftType === 'undefined') {
                    continue;
                }

                try {
                    const payload = {
                        request_date: `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
                        shift_code: shiftType,
                        ward: parseInt(effectiveWardId, 10)
                    };

                    await api.post('/api/shift-requests/', payload);
                    successCount++;
                } catch (err) {
                    failCount++;
                    failedDays.push(parseInt(day));

                    let errorDetail = `خطای ناشناخته در روز ${day}`;
                    if (err.response && err.response.data) {
                        if (typeof err.response.data === 'object') {
                            const firstKey = Object.keys(err.response.data)[0];
                            if (firstKey && err.response.data[firstKey]) {
                                if (Array.isArray(err.response.data[firstKey])) {
                                    errorDetail = err.response.data[firstKey][0];
                                } else {
                                    errorDetail = err.response.data[firstKey];
                                }
                            } else {
                                errorDetail = JSON.stringify(err.response.data);
                            }
                        } else if (typeof err.response.data === 'string') {
                            errorDetail = err.response.data;
                        }
                    }
                    errorMessages.push(`روز ${day}: ${errorDetail}`);
                }
            }

            if (failCount > 0) {
                alert(`⚠️ از ${changesCount} درخواست، ${successCount} مورد با موفقیت ثبت شد و ${failCount} مورد با خطا مواجه شد.\n\nجزئیات خطاها:\n${errorMessages.join('\n')}`);

                const newLocalChanges = { ...localChanges };
                failedDays.forEach(day => {
                    delete newLocalChanges[day];
                });
                setLocalChanges(newLocalChanges);
            } else {
                const sentCount = successCount + failCount;
                if (sentCount > 0) {
                    alert(`✅ ${successCount} درخواست با موفقیت در سیستم ثبت شد.`);
                } else {
                    alert('⚠️ هیچ درخواست معتبری برای ارسال وجود نداشت.');
                }
                setLocalChanges({});
            }

            await loadCalendar(year, month, effectiveWardId);

        } catch (err) {
            console.error('خطای کلی در ثبت نهایی:', err);
            alert('❌ خطای غیرمنتظره در ثبت نهایی. لطفاً دوباره تلاش کنید.');
        } finally {
            setIsSavingToServer(false);
        }
    };

    const handleDeleteRequest = async (reqId, day, event) => {
        event.stopPropagation();

        if (isMonthLocked || isUserLocked) {
            alert('برنامه شما قابل ویرایش نیست.');
            return;
        }

        if (!window.confirm(`آیا از حذف درخواست روز ${day} اطمینان دارید؟`)) {
            return;
        }

        try {
            await api.patch(`/api/shift-requests/${reqId}/`, {
                action: 'delete'
            });

            const newLocalChanges = { ...localChanges };
            delete newLocalChanges[day];
            setLocalChanges(newLocalChanges);

            await loadCalendar(year, month, selectedWardId || wardId);

            alert('✅ درخواست با موفقیت حذف شد.');
        } catch (err) {
            console.error('خطا در حذف درخواست:', err);
            const errorMsg = err.response?.data?.error
                || err.response?.data?.detail
                || 'خطا در حذف درخواست';
            alert(`❌ ${errorMsg}`);
        }
    };

    const renderContent = () => {
        switch (activeTab) {
            case 'request':
                return (
                    <div className="dashboard-tab-content">
                        <div className="tab-header">
                            <h2 className="tab-title">📝 ثبت درخواست شیفت جدید</h2>
                            <div className="month-badge">{monthName} {year}</div>
                        </div>

                        {isUserLocked && (
                            <div className="lock-warning" style={{ marginBottom: '15px' }}>
                                <div className="lock-warning-content">
                                    <span className="lock-icon">🔒</span>
                                    <div>
                                        <strong>برنامه شما توسط سرپرستار تنظیم شده است</strong>
                                        <p>برای تغییر درخواست‌ها با سرپرستار تماس بگیرید</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="submit-button-container">
                            <button
                                onClick={handleSubmitAll}
                                disabled={
                                    isSavingToServer ||
                                    Object.keys(localChanges).length === 0 ||
                                    isMonthLocked ||
                                    isUserLocked
                                }
                                className="btn btn-success btn-lg"
                            >
                                {isSavingToServer ? (
                                    <>
                                        <span className="spinner"></span>
                                        در حال ثبت...
                                    </>
                                ) : (
                                    <>📤 ثبت {Object.keys(localChanges).length} تغییر در سیستم</>
                                )}
                            </button>
                        </div>

                        {calendar.length === 0 ? (
                            <div className="empty-state" style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                                <div style={{ fontSize: '48px', marginBottom: '10px' }}>📭</div>
                                <p>در حال بارگذاری تقویم...</p>
                                <p style={{ fontSize: '12px', marginTop: '10px' }}>
                                    اگر این پیام باقی ماند، با سرپرستار تماس بگیرید.
                                </p>
                            </div>
                        ) : (
                            <div className="calendar-grid">
                                {WEEKDAYS.map(d => (
                                    <div key={d} className="weekday">{d}</div>
                                ))}

                                {calendar.map((day, index) => {
                                    if (day.day === 0) return <div key={`empty-${index}`} className="day-cell empty"></div>;

                                    let className = 'day-cell';
                                    if (day.is_weekend) className += ' weekend';
                                    if (day.is_holiday) className += ' holiday';
                                    if (isMonthLocked || isUserLocked) className += ' locked';

                                    const hasLocalChange = localChanges[day.day];
                                    if (hasLocalChange) className += ' local-change';

                                    const canDelete = !isMonthLocked && !isUserLocked;

                                    return (
                                        <div
                                            key={day.day}
                                            className={className}
                                            data-day={day.day}
                                            onClick={(e) => handleCellClick(day, e)}
                                        >
                                            <span className="day-number">{day.day}</span>

                                            {day.is_holiday && (
                                                <div className="holiday-name">{day.holiday_name}</div>
                                            )}

                                            {day.requests && day.requests.length > 0 && (
                                                <div className="requests-container">
                                                    {day.requests.map(req => (
                                                        <span
                                                            key={req.id}
                                                            className="shift-badge-wrapper"
                                                        >
                                                            <span className="shift-badge">
                                                                {req.shift_type}
                                                            </span>
                                                            {canDelete && !req.is_approved && (
                                                                <button
                                                                    className="badge-delete-btn"
                                                                    onClick={(e) => handleDeleteRequest(req.id, day.day, e)}
                                                                    title="حذف درخواست"
                                                                    type="button"
                                                                >
                                                                    ×
                                                                </button>
                                                            )}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        <div className="shift-codes-legend">
                            <h4 className="legend-title">راهنمای کدهای شیفت:</h4>
                            <div className="legend-items">
                                {shiftCodes.length === 0 ? (
                                    <span style={{ color: '#6B7280' }}>هیچ کد شیفتی برای این بخش فعال نشده است.</span>
                                ) : (
                                    shiftCodes.map(code => (
                                        <span key={code.id} className="legend-item">
                                            {code.code} ({code.label})
                                        </span>
                                    ))
                                )}
                            </div>
                            {Object.keys(localChanges).length > 0 && (
                                <div className="unsaved-warning">
                                    ⚠️ {Object.keys(localChanges).length} تغییر ثبت نشده در سیستم وجود دارد.
                                </div>
                            )}
                        </div>
                    </div>
                );
            case 'history':
                return (
                    <div className="dashboard-tab-content">
                        <PreviousSchedules />
                    </div>
                );
            case 'news':
                return <Announcements />;
            default:
                return <div>صفحه مورد نظر یافت نشد.</div>;
        }
    };

    return (
        <div className="dashboard-container role-nurse">
            <header className="header role-nurse">
                <div className="header-info">
                    {/* ✅ عنوان جدید */}
                    <h1>📋 داشبورد درخواست شیفت</h1>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        flexWrap: 'wrap',
                        marginTop: '6px',
                    }}>
                        {/* ✅ نام و نام خانوادگی */}
                        <p style={{ margin: 0 }}>
                            👤 {user?.first_name || ''} {user?.last_name || ''}
                        </p>

                        {/* ✅ سمت */}
                        {userProfile?.position_label && (
                            <>
                                <span style={{ color: '#d1fae5' }}>|</span>
                                <span style={{ fontSize: '14px', color: '#d1fae5' }}>
                                    💼 {userProfile.position_label}
                                </span>
                            </>
                        )}

                        {/* ✅ بخش */}
                        {userWards.length > 1 ? (
                            <>
                                <span style={{ color: '#d1fae5' }}>|</span>
                                <span style={{ fontSize: '14px', color: '#d1fae5' }}>
                                    🏥 بخش:
                                </span>
                                <select
                                    value={selectedWardId || ''}
                                    onChange={handleWardChange}
                                    style={{
                                        padding: '4px 10px',
                                        borderRadius: '6px',
                                        border: '1px solid rgba(255,255,255,0.3)',
                                        background: 'rgba(255,255,255,0.15)',
                                        color: 'white',
                                        fontSize: '13px',
                                        fontWeight: '700',
                                        fontFamily: 'inherit',
                                        cursor: 'pointer',
                                        outline: 'none',
                                    }}
                                    title="انتخاب بخش برای ثبت درخواست"
                                >
                                    {userWards.map(w => (
                                        <option
                                            key={w.id}
                                            value={w.id}
                                            style={{ color: '#0F172A', background: 'white' }}
                                        >
                                            {w.name} {w.is_primary ? '(اصلی)' : ''}
                                        </option>
                                    ))}
                                </select>
                            </>
                        ) : userWards.length === 1 ? (
                            <>
                                <span style={{ color: '#d1fae5' }}>|</span>
                                <span style={{ fontSize: '14px', color: '#d1fae5' }}>
                                    🏥 {userWards[0].name}
                                </span>
                            </>
                        ) : null}
                    </div>
                </div>

                <div className="header-buttons">
                    <button
                        className={`header-btn ${activeTab === 'request' ? 'active' : ''}`}
                        onClick={() => setActiveTab('request')}
                    >
                        📝 ثبت درخواست
                    </button>
                    <button
                        className={`header-btn ${activeTab === 'history' ? 'active' : ''}`}
                        onClick={() => setActiveTab('history')}
                    >
                        📅 برنامه‌های قبلی
                    </button>
                    <button
                        className={`header-btn ${activeTab === 'news' ? 'active' : ''}`}
                        onClick={() => setActiveTab('news')}
                    >
                        📢 اخبار
                    </button>

                    <button
                        className="header-btn"
                        onClick={() => navigate('/tutorial')}
                        style={{
                            background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                            color: 'white',
                        }}
                        title="راهنمای استفاده از سیستم"
                    >
                        📚 آموزش
                    </button>

                    <button
                        className="header-btn logout"
                        onClick={handleLogout}
                    >
                        🚪 خروج
                    </button>
                </div>
            </header>

            {isNewUserAfterLock && (
                <div className="lock-warning">
                    <div className="lock-warning-content">
                        <span className="lock-icon">🔒</span>
                        <div>
                            <strong>برنامه ماه قفل شده است</strong>
                            <p>برای ثبت شیفت با دفتر پرستاری تماس بگیرید</p>
                        </div>
                    </div>
                </div>
            )}

            {renderContent()}

            {siteSettings?.footer_text && (
                <footer className="site-footer">
                    {siteSettings.footer_text}
                </footer>
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
                            placeholder=""
                            defaultValue={overlayInput.value || ''}
                            onKeyDown={handleKeyDown}
                            onBlur={(e) => saveOverlayShift(e.target.value)}
                            onInput={(e) => setFilterText(e.target.value)}
                            list="shift-code-list"
                            className="overlay-input"
                        />
                        <datalist id="shift-code-list">
                            {shiftCodes
                                .filter(code =>
                                    filterText ?
                                    code.code.toUpperCase().startsWith(filterText.toUpperCase()) :
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

export default Dashboard;