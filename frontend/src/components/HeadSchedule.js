// src/components/HeadSchedule.js
import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ScheduleBase from './ScheduleBase';
import Announcements from './Announcements';
import ProfileMenu from './ProfileMenu';
import api from '../services/api';
import { format } from 'date-fns-jalali';
import { MONTH_NAMES, SCHEDULE_TYPE_META } from '../constants/persianCalendar';
import {
    getCurrentJalaliDate,
    getPastYears,
    getViewableMonthsForYear,
    getPreviousMonth,
    getNextMonth,
    isFutureMonth,
} from '../utils/dateHelpers';
import '../styles/index.css';

function HeadSchedule() {
    const location = useLocation();
    const navigate = useNavigate();
    const queryParams = new URLSearchParams(location.search);
    const wardId = queryParams.get('ward_id');
    const urlYear = queryParams.get('year');
    const urlMonth = queryParams.get('month');

    const [user, setUser] = useState(null);
    const [userProfile, setUserProfile] = useState(null);   // ✅ جدید
    const [siteSettings, setSiteSettings] = useState(null);
    const [wards, setWards] = useState([]);
    const [loadingWards, setLoadingWards] = useState(false);

    const [activePage, setActivePage] = useState('home');
    const [selectedYear, setSelectedYear] = useState(null);
    const [selectedMonth, setSelectedMonth] = useState(null);
    const [selectedWardId, setSelectedWardId] = useState(null);

    const [lockedSchedules, setLockedSchedules] = useState([]);
    const [isViewingLocked, setIsViewingLocked] = useState(false);

    useEffect(() => {
        loadUser();
        loadSiteSettings();

        const current = getCurrentJalaliDate();

        const next = getNextMonth();
        let year = next.year;
        let month = next.month;

        if (urlYear) year = parseInt(urlYear);
        if (urlMonth) month = parseInt(urlMonth);

        setSelectedYear(year);
        setSelectedMonth(month);

        if (wardId) {
            setActivePage('approve');
        }
    }, [wardId, location.search]);

    useEffect(() => {
        if (selectedYear && selectedMonth && !wardId && activePage === 'home') {
            loadWards();
        }
    }, [selectedYear, selectedMonth, activePage, wardId]);

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

            const profileRes = await api.get('/api/profiles/');
            const profile = profileRes.data.find(p => p.user?.username === res.data.username);

            const userWithAvatar = {
                ...res.data,
                avatar_url: profile?.avatar_url || null,
                position_label: profile?.position_label || '',
            };

            setUser(userWithAvatar);
            setUserProfile(profile);   // ✅ ذخیره profile

            if (profile && profile.ward) {
                setSelectedWardId(profile.ward);
            }
        } catch (error) {
            console.error('خطا در دریافت اطلاعات کاربر:', error);
        }
    };

    const loadWards = async () => {
        if (!selectedYear || !selectedMonth) return;
        setLoadingWards(true);
        try {
            const res = await api.get(
                `/api/head-schedule/?year=${selectedYear}&month=${selectedMonth}`
            );
            if (res.data.mode === 'list') {
                setWards(res.data.wards || []);
            } else {
                setWards([]);
            }
        } catch (error) {
            console.error('خطا در دریافت لیست بخش‌ها:', error);
            setWards([]);
        } finally {
            setLoadingWards(false);
        }
    };

const loadLockedSchedules = async () => {
    if (!selectedYear || !selectedMonth) {
        alert('لطفاً سال و ماه مورد نظر را انتخاب کنید.');
        return;
    }

    // ✅ فقط از ماه‌های گذشته و جاری (ماه‌های آینده غیرمجاز)
    if (isFutureMonth(selectedYear, selectedMonth)) {
        alert('⚠️ فقط برنامه‌های ماه‌های گذشته و جاری قابل مشاهده هستند.');
        return;
    }

    setIsViewingLocked(true);
    setLoadingWards(true);
    try {
        const res = await api.get(
            `/api/head-schedule/?year=${selectedYear}&month=${selectedMonth}`
        );

        if (res.data.mode === 'list') {
            let filtered = res.data.wards || [];

            // ✅ فیلتر ۱: فقط بخش‌های با حداقل یک برنامه قفل‌شده
            filtered = filtered.filter(ward => {
                const statuses = ward.schedule_statuses || {};
                return ['main', 'oncall', 'crisis', 'assistant'].some(
                    st => statuses[st]?.status === 'LOCKED'
                );
            });

            // ✅ فیلتر ۲: اگه بخش انتخابی مشخصه، فقط همون
            if (selectedWardId) {
                filtered = filtered.filter(w => w.id === selectedWardId);
            }

            setLockedSchedules(filtered);
        } else {
            setLockedSchedules([]);
        }
    } catch (error) {
        console.error('خطا در دریافت برنامه‌ها:', error);
        setLockedSchedules([]);
    } finally {
        setLoadingWards(false);
    }
};

    const handleEnterSchedule = (wardIdParam, scheduleType = 'main') => {
        navigate(
            `/head-schedule?ward_id=${wardIdParam}&schedule_type=${scheduleType}&year=${selectedYear}&month=${selectedMonth}`
        );
    };

    const canEnterScheduleType = (ward, scheduleType) => {
        if (!ward.schedule_statuses) {
            return scheduleType === 'main';
        }

        const statusInfo = ward.schedule_statuses[scheduleType];
        if (!statusInfo) {
            return scheduleType === 'main';
        }

        if (statusInfo.has_schedule) {
            return true;
        }

        if (scheduleType === 'oncall' || scheduleType === 'crisis') {
            const mainStatus = ward.schedule_statuses['main']?.status;
            const allowedMainStatuses = ['PENDING_SUPERVISOR', 'PENDING_MATRON', 'LOCKED'];
            if (!allowedMainStatuses.includes(mainStatus)) {
                return false;
            }
        }

        return true;
    };

    const getEnterButtonStatus = (scheduleType, statusInfo, canEnter) => {
        if (statusInfo?.has_schedule) {
            return '✅ موجود';
        }
        if (!canEnter) {
            return '🔒 قفل';
        }
        return '➕ ساخت';
    };

    const getEnterButtonColor = (scheduleType) => {
        const meta = SCHEDULE_TYPE_META[scheduleType];
        return {
            bg: meta?.color || '#3B82F6',
            hoverBg: meta?.text || '#2563EB',
        };
    };

    const hasAnySchedule = (ward) => {
        if (!ward.schedule_statuses) return false;
        return ['main', 'oncall', 'crisis', 'assistant'].some(
            st => ward.schedule_statuses[st]?.has_schedule
        );
    };

    const pastYears = getPastYears(10);
    const viewableMonths = getViewableMonthsForYear(selectedYear);

    const scheduleTypesToRender = ['main', 'oncall', 'crisis', 'assistant'];

    return (
        <div className="dashboard-container role-head">
            <header className="header role-head">
                <div className="header-info">
                    {/* ✅ عنوان جدید */}
                    <h1>📋 داشبورد تایید اولیه</h1>
                    <p>
                        👤 {user?.first_name || ''} {user?.last_name || ''}
                        {user?.position_label && (
                            <> | 💼 {user.position_label}</>
                        )}
                    </p>
                </div>

                <div className="header-buttons">
                    <button
                        className={`header-btn ${activePage === 'home' ? 'active' : ''}`}
                        onClick={() => {
                            setActivePage('home');
                            setIsViewingLocked(false);
                            const next = getNextMonth();
                            setSelectedYear(next.year);
                            setSelectedMonth(next.month);
                            if (wardId) navigate('/head-schedule');
                        }}
                    >
                        🏠 صفحه اصلی
                    </button>
                    <button
                        className={`header-btn ${activePage === 'list' ? 'active' : ''}`}
                        onClick={() => {
                            setActivePage('list');
                            setIsViewingLocked(false);
                            const current = getCurrentJalaliDate();
                            setSelectedYear(current.year);
                            setSelectedMonth(current.month);
                            if (wardId) navigate('/head-schedule');
                        }}
                    >
                        📅 لیست برنامه‌ها
                    </button>
                    <button
                        className="header-btn"
                        onClick={() => navigate('/ai-schedule')}
                    >
                        🤖 هوش مصنوعی
                    </button>
                    <button
                        className="header-btn"
                        onClick={() => navigate('/reports')}
                        style={{ background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)' }}
                    >
                        📊 گزارش‌گیری
                    </button>
                    <button
                        className={`header-btn ${activePage === 'news' ? 'active' : ''}`}
                        onClick={() => setActivePage('news')}
                    >
                        📢 اخبار
                    </button>

                    <button
                        className="header-btn"
                        onClick={() => navigate('/tutorial')}
                        style={{
                            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                            color: 'white',
                        }}
                        title="راهنمای استفاده از سیستم"
                    >
                        📚 آموزش
                    </button>

                    <ProfileMenu
                        user={user}
                        onUserUpdate={(newUser) => setUser(newUser)}
                    />
                </div>
            </header>

            {activePage === 'home' && !wardId && (
                <div>
                    <div style={{
                        display: 'flex',
                        gap: '10px',
                        alignItems: 'center',
                        marginBottom: '20px',
                        flexWrap: 'wrap',
                    }}>
                        <h2 className="section-title" style={{ margin: 0 }}>
                            بخش‌های شما:
                        </h2>
                        <select
                            value={selectedYear || ''}
                            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                            className="input-small"
                        >
                            {Array.from({ length: 11 }, (_, i) => {
                                const current = getCurrentJalaliDate();
                                return current.year + i;
                            }).map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                        <select
                            value={selectedMonth || ''}
                            onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                            className="input-small"
                        >
                            {MONTH_NAMES.slice(1).map((m, idx) => (
                                <option key={idx + 1} value={idx + 1}>{m}</option>
                            ))}
                        </select>
                        <button onClick={loadWards} className="btn btn-primary btn-sm">
                            🔄 به‌روزرسانی
                        </button>
                    </div>

                    <div className="wards-grid">
                        {loadingWards ? (
                            <div className="empty-state">
                                <div className="spinner-large"></div>
                                <p>در حال بارگذاری بخش‌ها...</p>
                            </div>
                        ) : wards.length === 0 ? (
                            <div className="empty-state">
                                <p>📭 بخش‌های فعالی برای نمایش وجود ندارد.</p>
                            </div>
                        ) : (
                            wards.map((ward) => (
                                <div key={ward.id} className="ward-card-four-schedules">
                                    <div className="ward-card-header">
                                        <div className="ward-card-title">
                                            <h3>🏥 {ward.name}</h3>
                                            <div className="ward-card-tags">
                                                <span className="tag">👤 {ward.staff_count} پرسنل</span>
                                                <span className="tag head-tag">
                                                    👨‍⚕️ سرپرستار: {ward.head_name}
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="schedule-buttons-row-4">
                                        {scheduleTypesToRender.map(st => {
                                            const statusInfo = ward.schedule_statuses?.[st];
                                            const canEnter = canEnterScheduleType(ward, st);
                                            const meta = SCHEDULE_TYPE_META[st];
                                            const colors = getEnterButtonColor(st);

                                            return (
                                                <button
                                                    key={st}
                                                    onClick={() => handleEnterSchedule(ward.id, st)}
                                                    disabled={!canEnter}
                                                    className={`schedule-btn-large ${st}`}
                                                    style={{
                                                        background: canEnter
                                                            ? `linear-gradient(135deg, ${colors.bg} 0%, ${colors.hoverBg} 100%)`
                                                            : '#9CA3AF'
                                                    }}
                                                    title={
                                                        !canEnter
                                                            ? (st === 'oncall' || st === 'crisis'
                                                                ? 'ابتدا برنامه اصلی را تأیید کنید'
                                                                : 'دسترسی ندارید')
                                                            : `${meta.label}${statusInfo?.has_schedule ? ' (دارای برنامه)' : ''}`
                                                    }
                                                >
                                                    <span className="btn-label">
                                                        {meta.emoji} {meta.shortLabel}
                                                    </span>
                                                    <span className="btn-status">
                                                        {getEnterButtonStatus(st, statusInfo, canEnter)}
                                                    </span>
                                                </button>
                                            );
                                        })}
                                    </div>

                                    {ward.schedule_statuses && hasAnySchedule(ward) && (
                                        <div className="ward-status-list">
                                            {scheduleTypesToRender.map(st => {
                                                const info = ward.schedule_statuses[st];
                                                if (!info || !info.has_schedule) return null;

                                                const meta = SCHEDULE_TYPE_META[st];

                                                return (
                                                    <div
                                                        key={st}
                                                        className={`status-item status-${st}`}
                                                    >
                                                        <span className="status-label">
                                                            {meta.label}:
                                                        </span>
                                                        <span className="status-value">
                                                            {info.status_display || info.status}
                                                        </span>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}

            {activePage === 'list' && !wardId && (
                <div>
                    <div className="filter-bar">
                        <h3 className="filter-title">📊 مشاهده برنامه‌های ماهانه بخش‌ها</h3>

                        <div className="filter-controls">
                            <select
                                value={selectedYear || ''}
                                onChange={(e) => {
                                    const newYear = parseInt(e.target.value);
                                    setSelectedYear(newYear);
                                    const months = getViewableMonthsForYear(newYear);
                                    if (months.length > 0 && selectedMonth > months[months.length - 1].month) {
                                        setSelectedMonth(months[months.length - 1].month);
                                    }
                                }}
                                className="input-small"
                            >
                                {pastYears.map(y => (
                                    <option key={y} value={y}>{y}</option>
                                ))}
                            </select>

                            <select
                                value={selectedMonth || ''}
                                onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                                className="input-small"
                            >
                                {viewableMonths.map(m => (
                                    <option key={m.month} value={m.month}>{m.name}</option>
                                ))}
                            </select>

                            <button
                                onClick={loadLockedSchedules}
                                className="btn btn-primary"
                            >
                                🔍 نمایش برنامه‌ها
                            </button>
                        </div>
                    </div>

                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>بخش</th>
                                    <th>سرپرستار</th>
                                    <th>تعداد پرسنل</th>
                                    <th>وضعیت برنامه اصلی</th>
                                    <th>عملیات</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loadingWards ? (
                                    <tr>
                                        <td colSpan="6" style={{ padding: '20px', textAlign: 'center' }}>
                                            <div className="spinner-large"></div>
                                            در حال بارگذاری برنامه‌ها...
                                        </td>
                                    </tr>
                                ) : !isViewingLocked ? (
                                    <tr>
                                        <td colSpan="6" style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                                            👈 لطفاً سال و ماه را انتخاب کرده و دکمه "نمایش برنامه‌ها" را بزنید.
                                        </td>
                                    </tr>
                                ) : lockedSchedules.length === 0 ? (
                                    <tr>
                                        <td colSpan="6" style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                                            📭 برای این ماه، هیچ برنامه‌ای وجود ندارد.
                                        </td>
                                    </tr>
                                ) : (
                                    lockedSchedules.map((item, index) => {
                                        const mainStatus = item.schedule_statuses?.main;
                                        return (
                                            <tr key={item.id}>
                                                <td style={{ fontWeight: 'bold', color: '#6B7280' }}>{index + 1}</td>
                                                <td style={{ fontWeight: 'bold' }}>
                                                    🏥 {item.name}
                                                    {item.is_sub && (
                                                        <span style={{ fontSize: '11px', color: '#6B7280', marginRight: '6px' }}>
                                                            (زیربخش)
                                                        </span>
                                                    )}
                                                </td>
                                                <td>{item.head_name || '-'}</td>
                                                <td style={{ fontWeight: 'bold' }}>{item.staff_count || 0}</td>
                                                <td>
                                                    <span className={`badge ${
                                                        mainStatus?.status === 'LOCKED' ? 'badge-locked' :
                                                        mainStatus?.status === 'RETURNED_TO_HEAD' ? 'badge-returned' :
                                                        mainStatus?.status === 'RETURNED_TO_SUPERVISOR' ? 'badge-returned' :
                                                        'badge-pending'
                                                    }`}>
                                                        {mainStatus?.status_display || '⏳ در گردش کار'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                                        {scheduleTypesToRender.map(st => {
                                                            const info = item.schedule_statuses?.[st];
                                                            const hasSchedule = info?.has_schedule;

                                                            if (!hasSchedule) return null;

                                                            const meta = SCHEDULE_TYPE_META[st];
                                                            const colors = getEnterButtonColor(st);

                                                            return (
                                                                <button
                                                                    key={st}
                                                                    onClick={() => handleEnterSchedule(item.id, st)}
                                                                    className="btn btn-primary btn-sm"
                                                                    style={{
                                                                        background: colors.bg,
                                                                        color: 'white',
                                                                        padding: '4px 8px',
                                                                        fontSize: '11px',
                                                                    }}
                                                                    title={meta.label}
                                                                >
                                                                    {meta.emoji} {meta.shortLabel}
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {wardId && (
                <div className="schedule-zoom-wrapper">
                    <ScheduleBase
                        key={`${wardId}-${selectedYear}-${selectedMonth}`}
                        title="📋 برنامه ماهانه - سرپرستار"
                        mode="head"
                        hideToolbar={true}
                        renderActions={null}
                        extraProps={{
                            wardId: wardId,
                            userRole: 'head',
                            initialYear: urlYear ? parseInt(urlYear) : selectedYear,
                            initialMonth: urlMonth ? parseInt(urlMonth) : selectedMonth,
                        }}
                    />
                </div>
            )}

            {activePage === 'news' && !wardId && (
                <div style={{ marginTop: '20px' }}>
                    <Announcements />
                </div>
            )}

            {siteSettings?.footer_text && (
                <footer className="site-footer">
                    {siteSettings.footer_text}
                </footer>
            )}
        </div>
    );
}

export default HeadSchedule;