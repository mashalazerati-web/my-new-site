// src/components/SupervisorSchedule.js
import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../services/api';
import ScheduleBase from './ScheduleBase';
import Announcements from './Announcements';
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
import ProfileMenu from './ProfileMenu';


const SCHEDULE_TYPES_RENDER = ['main', 'oncall', 'crisis', 'assistant'];


function SupervisorSchedule() {
    const location = useLocation();
    const navigate = useNavigate();
    const queryParams = new URLSearchParams(location.search);
    const wardId = queryParams.get('ward_id');
    const scheduleTypeFromUrl = queryParams.get('schedule_type') || 'main';
    const urlYear = queryParams.get('year');
    const urlMonth = queryParams.get('month');

    const [wards, setWards] = useState([]);
    const [loadingWards, setLoadingWards] = useState(false);
    const [user, setUser] = useState(null);
    const [siteSettings, setSiteSettings] = useState(null);

    const [activePage, setActivePage] = useState('home');

    const [filterYear, setFilterYear] = useState(null);
    const [filterMonth, setFilterMonth] = useState(null);
    const [filterWard, setFilterWard] = useState('');
    const [filterScheduleType, setFilterScheduleType] = useState('');

    const [listYear, setListYear] = useState(null);
    const [listMonth, setListMonth] = useState(null);
    const [lockedSchedules, setLockedSchedules] = useState([]);
    const [loadingLocked, setLoadingLocked] = useState(false);
    const [isViewingLocked, setIsViewingLocked] = useState(false);

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
        } catch (error) {
            console.error('خطا در دریافت اطلاعات کاربر:', error);
        }
    };

    const loadWards = async () => {
        if (!filterYear || !filterMonth) return;

        setLoadingWards(true);
        try {
            const res = await api.get(
                `/api/supervisor-dashboard/?year=${filterYear}&month=${filterMonth}`
            );
            if (Array.isArray(res.data)) {
                setWards(res.data);
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
    if (!listYear || !listMonth) {
        alert('لطفاً سال و ماه مورد نظر را انتخاب کنید.');
        return;
    }

    if (isFutureMonth(listYear, listMonth)) {
        alert('⚠️ فقط برنامه‌های ماه‌های گذشته و جاری قابل مشاهده هستند.');
        return;
    }

    setIsViewingLocked(true);
    setLoadingLocked(true);
    try {
        const res = await api.get(
            `/api/supervisor-dashboard/?year=${listYear}&month=${listMonth}`
        );
        if (Array.isArray(res.data)) {
            // ✅ فیلتر قطعی: فقط برنامه‌هایی که واقعاً LOCKED هستن
            const lockedOnly = res.data.filter(item => {
                const status = item.status || '';
                const statusText = item.status_text || '';
                return status === 'LOCKED' || statusText.includes('قفل');
            });
            setLockedSchedules(lockedOnly);
        } else {
            setLockedSchedules([]);
        }
    } catch (error) {
        console.error('خطا در دریافت برنامه‌ها:', error);
        setLockedSchedules([]);
    } finally {
        setLoadingLocked(false);
    }
};


    useEffect(() => {
        loadUser();
        loadSiteSettings();
    }, []);

    useEffect(() => {
        const current = getCurrentJalaliDate();

        const next = getNextMonth();
        let activeYear = next.year;
        let activeMonth = next.month;

        const prev = getPreviousMonth();

        if (urlYear) activeYear = parseInt(urlYear);
        if (urlMonth) activeMonth = parseInt(urlMonth);

        setFilterYear(activeYear);
        setFilterMonth(activeMonth);

        setListYear(prev.year);
        setListMonth(prev.month);
    }, []);

    useEffect(() => {
        if (wardId) {
            setActivePage('approve');
        } else {
            setActivePage('home');
        }
    }, [wardId]);

    useEffect(() => {
        if (filterYear && filterMonth && activePage === 'home' && !wardId) {
            loadWards();
        }
    }, [filterYear, filterMonth, activePage, wardId]);

    const filteredWards = wards.filter(ward => {
        if (filterWard && String(ward.id) !== String(filterWard)) {
            return false;
        }
        if (filterScheduleType && ward.schedule_type !== filterScheduleType) {
            return false;
        }
        return true;
    });

    const handleEnterSchedule = (wardIdParam, scheduleType = 'main') => {
        navigate(
            `/supervisor-schedule?ward_id=${wardIdParam}&schedule_type=${scheduleType}&year=${filterYear}&month=${filterMonth}`
        );
    };

    const handleEnterScheduleFromList = (wardIdParam, scheduleType = 'main') => {
        navigate(
            `/supervisor-schedule?ward_id=${wardIdParam}&schedule_type=${scheduleType}&year=${listYear}&month=${listMonth}`
        );
    };

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        navigate('/login');
    };

    const scheduleTypeLabel = (st) => {
        return SCHEDULE_TYPE_META[st]?.label || '🤖 اصلی';
    };

    const scheduleTypeColor = (st) => {
        const meta = SCHEDULE_TYPE_META[st];
        if (meta) {
            return { bg: meta.bg, color: meta.text };
        }
        return { bg: '#DBEAFE', color: '#1E40AF' };
    };

    const uniqueWards = Array.from(
        new Map(wards.map(w => [w.id, { id: w.id, name: w.name }])).values()
    );

    const pastYears = getPastYears(10);
    const viewableMonths = getViewableMonthsForYear(listYear);

    return (
        <div className="dashboard-container role-supervisor">
            <header className="header role-supervisor">
                <div className="header-info">
                    {/* ✅ عنوان جدید */}
                    <h1>📋 داشبورد تایید میانی</h1>
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
                            const next = getNextMonth();
                            setFilterYear(next.year);
                            setFilterMonth(next.month);
                            if (wardId) navigate('/supervisor-schedule');
                        }}
                    >
                        🏠 صفحه اصلی
                    </button>
                    <button
                        className={`header-btn ${activePage === 'list' ? 'active' : ''}`}
                        onClick={() => {
                            setActivePage('list');
                            const current = getCurrentJalaliDate();
                            setListYear(current.year);
                            setListMonth(current.month);
                            if (wardId) navigate('/supervisor-schedule');
                        }}
                    >
                        📅 لیست برنامه‌ها
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
                            background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
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
                        gap: '12px',
                        alignItems: 'center',
                        marginBottom: '20px',
                        flexWrap: 'wrap',
                        padding: '16px',
                        background: '#F8FAFC',
                        borderRadius: '12px',
                        border: '1px solid #E2E8F0',
                    }}>
                        <h3 style={{
                            margin: 0,
                            color: '#0F172A',
                            fontSize: '16px',
                            fontWeight: '800',
                        }}>
                            🔍 فیلترها:
                        </h3>

                        <select
                            value={filterYear || ''}
                            onChange={(e) => setFilterYear(parseInt(e.target.value))}
                            className="input-small"
                            style={{ padding: '8px 12px', borderRadius: '8px' }}
                        >
                            {Array.from({ length: 11 }, (_, i) => {
                                const current = getCurrentJalaliDate();
                                return current.year + i;
                            }).map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>

                        <select
                            value={filterMonth || ''}
                            onChange={(e) => setFilterMonth(parseInt(e.target.value))}
                            className="input-small"
                            style={{ padding: '8px 12px', borderRadius: '8px' }}
                        >
                            {MONTH_NAMES.slice(1).map((m, idx) => (
                                <option key={idx + 1} value={idx + 1}>{m}</option>
                            ))}
                        </select>

                        <select
                            value={filterWard}
                            onChange={(e) => setFilterWard(e.target.value)}
                            className="input-small"
                            style={{ padding: '8px 12px', borderRadius: '8px' }}
                        >
                            <option value="">🏥 همه بخش‌ها</option>
                            {uniqueWards.map(w => (
                                <option key={w.id} value={w.id}>{w.name}</option>
                            ))}
                        </select>

                        <select
                            value={filterScheduleType}
                            onChange={(e) => setFilterScheduleType(e.target.value)}
                            className="input-small"
                            style={{ padding: '8px 12px', borderRadius: '8px' }}
                        >
                            <option value="">📋 همه انواع</option>
                            {SCHEDULE_TYPES_RENDER.map(st => (
                                <option key={st} value={st}>
                                    {SCHEDULE_TYPE_META[st]?.label}
                                </option>
                            ))}
                        </select>

                        <button
                            onClick={loadWards}
                            className="btn btn-primary btn-sm"
                            disabled={loadingWards}
                            style={{ minWidth: '130px' }}
                        >
                            {loadingWards ? '⏳ در حال بارگذاری...' : '🔄 به‌روزرسانی'}
                        </button>
                    </div>

                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>بخش</th>
                                    <th>نوع برنامه</th>
                                    <th>سرپرستار</th>
                                    <th>تعداد پرسنل</th>
                                    <th>وضعیت</th>
                                    <th>عملیات</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loadingWards ? (
                                    <tr>
                                        <td colSpan="7" style={{ padding: '20px', textAlign: 'center' }}>
                                            <div className="spinner-large"></div>
                                            در حال بارگذاری بخش‌ها...
                                        </td>
                                    </tr>
                                ) : filteredWards.length === 0 ? (
                                    <tr>
                                        <td colSpan="7" style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                                            📭 برای این فیلترها برنامه‌ای یافت نشد.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredWards.map((ward, index) => {
                                        const colors = scheduleTypeColor(ward.schedule_type);
                                        return (
                                            <tr key={`${ward.id}-${ward.schedule_type || 'main'}`}>
                                                <td style={{ fontWeight: 'bold', color: '#6B7280' }}>{index + 1}</td>
                                                <td style={{ fontWeight: 'bold' }}>🏥 {ward.name}</td>
                                                <td>
                                                    <span style={{
                                                        padding: '4px 10px',
                                                        borderRadius: '12px',
                                                        fontSize: '12px',
                                                        fontWeight: 'bold',
                                                        backgroundColor: colors.bg,
                                                        color: colors.color,
                                                    }}>
                                                        {ward.schedule_type_label || scheduleTypeLabel(ward.schedule_type)}
                                                    </span>
                                                </td>
                                                <td>{ward.head_name}</td>
                                                <td style={{ fontWeight: 'bold' }}>{ward.staff_count}</td>
                                                <td>
                                                    <span className={`badge ${
                                                        ward.status === 'LOCKED' ? 'badge-locked' :
                                                        ward.status === 'RETURNED_TO_HEAD' ? 'badge-returned' :
                                                        ward.status === 'RETURNED_TO_SUPERVISOR' ? 'badge-returned' :
                                                        'badge-pending'
                                                    }`}>
                                                        {ward.status_text || '⏳ در گردش کار'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <button
                                                        onClick={() => handleEnterSchedule(ward.id, ward.schedule_type || 'main')}
                                                        className="btn btn-primary btn-sm"
                                                    >
                                                        ورود ➜
                                                    </button>
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

            {activePage === 'list' && !wardId && (
                <div>
                    <div className="filter-bar">
                        <h3 className="filter-title">📊 مشاهده برنامه‌های ماهانه بخش‌ها</h3>

                        <div className="filter-controls">
                            <select
                                value={listYear || ''}
                                onChange={(e) => {
                                    const newYear = parseInt(e.target.value);
                                    setListYear(newYear);
                                    const months = getViewableMonthsForYear(newYear);
                                    if (months.length > 0 && listMonth > months[months.length - 1].month) {
                                        setListMonth(months[months.length - 1].month);
                                    }
                                }}
                                className="input-small"
                            >
                                {pastYears.map(y => (
                                    <option key={y} value={y}>{y}</option>
                                ))}
                            </select>

                            <select
                                value={listMonth || ''}
                                onChange={(e) => setListMonth(parseInt(e.target.value))}
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
                                    <th>نوع برنامه</th>
                                    <th>سرپرستار</th>
                                    <th>تعداد پرسنل</th>
                                    <th>وضعیت</th>
                                    <th>عملیات</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loadingLocked ? (
                                    <tr>
                                        <td colSpan="7" style={{ padding: '20px', textAlign: 'center' }}>
                                            <div className="spinner-large"></div>
                                            در حال بارگذاری برنامه‌ها...
                                        </td>
                                    </tr>
                                ) : !isViewingLocked ? (
                                    <tr>
                                        <td colSpan="7" style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                                            👈 لطفاً سال و ماه را انتخاب کرده و دکمه "نمایش برنامه‌ها" را بزنید.
                                        </td>
                                    </tr>
                                ) : lockedSchedules.length === 0 ? (
                                    <tr>
                                        <td colSpan="7" style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
                                            🔒 برای این ماه، هیچ برنامه قفل‌شده‌ای وجود ندارد.
                                        </td>
                                    </tr>
                                ) : (
                                    lockedSchedules.map((item, index) => {
                                        const colors = scheduleTypeColor(item.schedule_type);
                                        return (
                                            <tr key={`${item.id}-${item.schedule_type || 'main'}`}>
                                                <td style={{ fontWeight: 'bold', color: '#6B7280' }}>{index + 1}</td>
                                                <td style={{ fontWeight: 'bold' }}>🏥 {item.name}</td>
                                                <td>
                                                    <span style={{
                                                        padding: '4px 10px',
                                                        borderRadius: '12px',
                                                        fontSize: '12px',
                                                        fontWeight: 'bold',
                                                        backgroundColor: colors.bg,
                                                        color: colors.color,
                                                    }}>
                                                        {item.schedule_type_label || scheduleTypeLabel(item.schedule_type)}
                                                    </span>
                                                </td>
                                                <td>{item.head_name || '-'}</td>
                                                <td style={{ fontWeight: 'bold' }}>{item.staff_count || 0}</td>
                                                <td>
                                                    <span className={`badge ${
                                                        item.status === 'LOCKED' ? 'badge-locked' :
                                                        item.status === 'RETURNED_TO_HEAD' ? 'badge-returned' :
                                                        item.status === 'RETURNED_TO_SUPERVISOR' ? 'badge-returned' :
                                                        'badge-pending'
                                                    }`}>
                                                        {item.status_text || '⏳ در گردش کار'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <button
                                                        onClick={() => handleEnterScheduleFromList(item.id, item.schedule_type || 'main')}
                                                        className="btn btn-primary btn-sm"
                                                    >
                                                        ورود ➜
                                                    </button>
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
                <div className="schedule-zoom-wrapper-supervisor">
                    <ScheduleBase
                        key={`${wardId}-${scheduleTypeFromUrl}-${urlYear}-${urlMonth}`}
                        title="📋 برنامه ماهانه - سوپروایزر"
                        mode="supervisor"
                        hideToolbar={true}
                        renderActions={null}
                        extraProps={{
                            wardId: wardId,
                            userRole: 'supervisor',
                            scheduleType: scheduleTypeFromUrl,
                            initialYear: urlYear ? parseInt(urlYear) : filterYear,
                            initialMonth: urlMonth ? parseInt(urlMonth) : filterMonth,
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

export default SupervisorSchedule;