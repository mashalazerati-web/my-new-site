// src/components/ReportsPage.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { MONTH_NAMES, SCHEDULE_TYPE_META } from '../constants/persianCalendar';
import ProfileMenu from './ProfileMenu';

import '../styles/index.css';

// ✅ ثابت: همه‌ی انواع برنامه‌ها
const ALL_SCHEDULE_TYPES = ['main', 'oncall', 'crisis', 'assistant'];

function ReportsPage() {
    const navigate = useNavigate();

    const [user, setUser] = useState(null);
    const [userRole, setUserRole] = useState(null);
    const [siteSettings, setSiteSettings] = useState(null);
    const [wards, setWards] = useState([]);
    const [wardId, setWardId] = useState(null);
    const [year, setYear] = useState(1405);
    const [month, setMonth] = useState(6);
    const [reportData, setReportData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // ✅ بارگذاری اولیه
    useEffect(() => {
        loadUserAndWards();
        loadSiteSettings();
    }, []);

    const loadSiteSettings = async () => {
        try {
            const res = await api.get('/api/site-settings/');
            setSiteSettings(res.data);
        } catch (err) {
            console.error('خطا در تنظیمات سایت:', err);
        }
    };

    // ✅ بارگذاری کاربر + بخش‌ها بر اساس نقش
    const loadUserAndWards = async () => {
        try {
            const userRes = await api.get('/api/users/me/');
            setUser(userRes.data);

            // ✅ دریافت نقش
            const profileRes = await api.get('/api/profiles/');
            const profile = profileRes.data.find(p => p.user?.username === userRes.data.username);
            const role = profile?.role || 'staff';
            setUserRole(role);
            setUser({
                ...userRes.data,
                avatar_url: profile?.avatar_url || null,
            });

            // ✅ بارگذاری بخش‌ها بر اساس نقش
            let wardsList = [];

            if (role === 'head') {
                // سرپرستار: بخش خودش
                if (profile.ward) {
                    try {
                        const wardRes = await api.get(`/api/wards/${profile.ward}/`);
                        wardsList = [{ id: wardRes.data.id, name: wardRes.data.name }];
                    } catch (err) {
                        console.error('خطا در بارگذاری بخش:', err);
                    }
                }
            } else if (role === 'supervisor') {
                // ✅ سوپروایزر: از endpoint اختصاصی
                try {
                    const res = await api.get('/api/my-supervised-wards/');
                    if (Array.isArray(res.data)) {
                        wardsList = res.data;
                    }
                } catch (err) {
                    console.error('خطا در بارگذاری بخش‌های سوپروایزر:', err);
                }
            } else if (role === 'admin') {
                // ✅ مترون: از endpoint اختصاصی
                try {
                    const res = await api.get('/api/all-wards-for-matron/');
                    if (Array.isArray(res.data)) {
                        wardsList = res.data;
                    }
                } catch (err) {
                    console.error('خطا در بارگذاری همه بخش‌ها:', err);
                }
            }

            setWards(wardsList);
            if (wardsList.length > 0) {
                setWardId(wardsList[0].id);
            }
        } catch (error) {
            console.error('خطا در بارگذاری کاربر:', error);
            if (error.response?.status === 401) {
                navigate('/login');
            }
        }
    };

    const handleLoadReport = async () => {
        if (!wardId || !year || !month) {
            alert('لطفاً بخش، سال و ماه را انتخاب کنید.');
            return;
        }

        setLoading(true);
        setError(null);
        setReportData(null);

        try {
            const res = await api.get(
                `/api/monthly-report/?ward_id=${wardId}&year=${year}&month=${month}`
            );
            setReportData(res.data);
        } catch (err) {
            console.error('خطا در بارگذاری گزارش:', err);
            setError(err.response?.data?.error || 'خطا در بارگذاری گزارش');
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        if (userRole === 'supervisor') {
            navigate('/supervisor-schedule');
        } else if (userRole === 'admin') {
            navigate('/matron-schedule');
        } else {
            navigate('/head-schedule');
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'LOCKED': return { bg: '#D1FAE5', color: '#065F46' };
            case 'PENDING_MATRON': return { bg: '#DBEAFE', color: '#1E40AF' };
            case 'PENDING_SUPERVISOR': return { bg: '#FEF3C7', color: '#92400E' };
            case 'RETURNED_TO_HEAD': return { bg: '#FEE2E2', color: '#991B1B' };
            case 'RETURNED_TO_SUPERVISOR': return { bg: '#FEE2E2', color: '#991B1B' };
            default: return { bg: '#F3F4F6', color: '#374151' };
        }
    };

    // ✅ برنامه config — شامل assistant
    const programConfig = {
        main: { label: '🤖 برنامه اصلی', color: '#3B82F6', bg: '#DBEAFE' },
        oncall: { label: '📞 برنامه آنکالی', color: '#F59E0B', bg: '#FEF3C7' },
        crisis: { label: '🚨 برنامه بحران', color: '#EF4444', bg: '#FEE2E2' },
        assistant: { label: '🧑‍⚕️ کمک پرستار', color: '#10B981', bg: '#D1FAE5' },
    };

    const getHeaderRoleClass = () => {
        if (userRole === 'supervisor') return 'role-supervisor';
        if (userRole === 'admin') return 'role-matron';
        return 'role-head';
    };

    const getRoleTitle = () => {
        if (userRole === 'supervisor') return 'داشبورد سوپروایزر';
        if (userRole === 'admin') return 'داشبورد مترون';
        return 'داشبورد سرپرستار';
    };

    return (
        <div className={`dashboard-container ${getHeaderRoleClass()}`}>
            <header className={`header ${getHeaderRoleClass()}`}>
                <div className="header-info">
                    <h1>📊 داشبورد گزارش‌گیری</h1>
                    <p>👤 {user?.first_name || ''} {user?.last_name || ''} - {getRoleTitle()}</p>
                </div>

                <div className="header-buttons">
                    <button
                        className="header-btn"
                        onClick={handleBack}
                    >
                        ↩️ بازگشت به داشبورد
                    </button>

                    <ProfileMenu
                        user={user}
                        onUserUpdate={(newUser) => setUser(newUser)}
                    />
                </div>
            </header>

            {/* فیلترها */}
            <div className="ai-section-card">
                <h3 className="ai-section-title">🔍 انتخاب بخش، سال و ماه</h3>
                <div className="ai-form-row">
                    <div className="ai-form-group">
                        <label>🏥 بخش:</label>
                        <select
                            value={wardId || ''}
                            onChange={(e) => setWardId(parseInt(e.target.value))}
                            className="input-small"
                            disabled={wards.length === 0}
                        >
                            {wards.length === 0 ? (
                                <option value="">بخشی یافت نشد</option>
                            ) : (
                                wards.map(ward => (
                                    <option key={ward.id} value={ward.id}>{ward.name}</option>
                                ))
                            )}
                        </select>
                    </div>
                    <div className="ai-form-group">
                        <label>📆 سال:</label>
                        <select
                            value={year}
                            onChange={(e) => setYear(parseInt(e.target.value))}
                            className="input-small"
                        >
                            {Array.from({ length: 11 }, (_, i) => 1405 + i).map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                    </div>
                    <div className="ai-form-group">
                        <label>🗓️ ماه:</label>
                        <select
                            value={month}
                            onChange={(e) => setMonth(parseInt(e.target.value))}
                            className="input-small"
                        >
                            {MONTH_NAMES.slice(1).map((m, idx) => (
                                <option key={idx + 1} value={idx + 1}>{m}</option>
                            ))}
                        </select>
                    </div>
                    <div className="ai-form-group">
                        <label>&nbsp;</label>
                        <button
                            onClick={handleLoadReport}
                            disabled={loading || !wardId}
                            className="btn btn-primary"
                            style={{ minWidth: '160px' }}
                        >
                            {loading ? '⏳ در حال بارگذاری...' : '📊 نمایش گزارش'}
                        </button>
                    </div>
                </div>
            </div>

            {/* خطا */}
            {error && (
                <div style={{
                    padding: '16px 20px',
                    background: '#FEE2E2',
                    border: '2px solid #FCA5A5',
                    borderRadius: '12px',
                    color: '#991B1B',
                    fontWeight: '700',
                    marginBottom: '16px',
                }}>
                    ❌ {error}
                </div>
            )}

            {/* گزارش */}
            {reportData && reportData.summary && (
                <>
                    {/* خلاصه */}
                    <div className="ai-section-card">
                        <h3 className="ai-section-title">
                            📋 خلاصه گزارش - {reportData.summary.ward_name} - {reportData.summary.month_name} {reportData.summary.year}
                        </h3>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                            gap: '12px',
                            marginTop: '12px',
                        }}>
                            <SummaryCard
                                title="تعداد پرسنل"
                                value={reportData.summary.total_staff}
                                icon="👥"
                                color="#3B82F6"
                            />
                            <SummaryCard
                                title="برنامه‌های فعال"
                                value={`${reportData.summary.active_programs} از 4`}
                                icon="📋"
                                color="#10B981"
                            />
                            <SummaryCard
                                title="برنامه‌های قفل‌شده"
                                value={`${reportData.summary.locked_programs} از 4`}
                                icon="🔒"
                                color="#8B5CF6"
                            />
                            <SummaryCard
                                title="روزهای ماه"
                                value={reportData.summary.days_in_month}
                                icon="📅"
                                color="#F59E0B"
                            />
                        </div>
                    </div>

                    {/* ✅ بخش هشدارها و مشکلات */}
                    <div className="ai-section-card">
                        <h3 className="ai-section-title">⚠️ تحلیل برنامه‌ها</h3>

                        {/* خلاصه هشدارها */}
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                            gap: '12px',
                            marginTop: '12px',
                            marginBottom: '20px',
                        }}>
                            {ALL_SCHEDULE_TYPES.map(st => {
                                const data = reportData[st];
                                const config = programConfig[st];

                                if (!data || !data.exists) {
                                    return (
                                        <div key={st} style={{
                                            padding: '14px',
                                            background: '#F3F4F6',
                                            borderRadius: '12px',
                                            border: '2px solid #D1D5DB',
                                            borderRight: `5px solid ${config.color}`,
                                            opacity: 0.7,
                                        }}>
                                            <div style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                marginBottom: '8px',
                                            }}>
                                                <span style={{
                                                    fontSize: '13px',
                                                    fontWeight: '700',
                                                    color: config.color,
                                                }}>
                                                    {config.label}
                                                </span>
                                                <span style={{
                                                    fontSize: '20px',
                                                    fontWeight: '800',
                                                    color: '#9CA3AF',
                                                }}>
                                                    📭
                                                </span>
                                            </div>
                                            <div style={{
                                                fontSize: '12px',
                                                color: '#6B7280',
                                                fontWeight: '600',
                                            }}>
                                                این برنامه تولید نشده است
                                            </div>
                                        </div>
                                    );
                                }

                                const totalWarnings = data.warnings_count || 0;
                                const highWarnings = data.warnings_high || 0;
                                const mediumWarnings = data.warnings_medium || 0;

                                return (
                                    <div key={st} style={{
                                        padding: '14px',
                                        background: totalWarnings > 0 ? '#FEF2F2' : '#F0FDF4',
                                        borderRadius: '12px',
                                        border: `2px solid ${totalWarnings > 0 ? '#FCA5A5' : '#86EFAC'}`,
                                        borderRight: `5px solid ${config.color}`,
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            marginBottom: '8px',
                                        }}>
                                            <span style={{
                                                fontSize: '13px',
                                                fontWeight: '700',
                                                color: config.color,
                                            }}>
                                                {config.label}
                                            </span>
                                            <span style={{
                                                fontSize: '20px',
                                                fontWeight: '800',
                                                color: totalWarnings > 0 ? '#DC2626' : '#16A34A',
                                            }}>
                                                {totalWarnings > 0 ? `⚠️ ${totalWarnings}` : '✅'}
                                            </span>
                                        </div>

                                        {totalWarnings > 0 ? (
                                            <div style={{
                                                display: 'flex',
                                                gap: '8px',
                                                fontSize: '11px',
                                                flexWrap: 'wrap',
                                            }}>
                                                {highWarnings > 0 && (
                                                    <span style={{
                                                        padding: '2px 8px',
                                                        background: '#FEE2E2',
                                                        color: '#991B1B',
                                                        borderRadius: '8px',
                                                        fontWeight: '700',
                                                    }}>
                                                        🔴 بحرانی: {highWarnings}
                                                    </span>
                                                )}
                                                {mediumWarnings > 0 && (
                                                    <span style={{
                                                        padding: '2px 8px',
                                                        background: '#FEF3C7',
                                                        color: '#92400E',
                                                        borderRadius: '8px',
                                                        fontWeight: '700',
                                                    }}>
                                                        🟡 متوسط: {mediumWarnings}
                                                    </span>
                                                )}
                                            </div>
                                        ) : (
                                            <div style={{
                                                fontSize: '12px',
                                                color: '#065F46',
                                                fontWeight: '600',
                                            }}>
                                                ✅ بدون مشکل
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>

                        {/* جزئیات هشدارها */}
                        {ALL_SCHEDULE_TYPES.map(st => {
                            const data = reportData[st];
                            const config = programConfig[st];

                            // حالت ۱: برنامه تولید نشده
                            if (!data || !data.exists) {
                                return (
                                    <div key={st} style={{
                                        marginBottom: '16px',
                                        padding: '24px',
                                        background: '#F9FAFB',
                                        borderRadius: '12px',
                                        border: '2px dashed #D1D5DB',
                                        textAlign: 'center',
                                    }}>
                                        <div style={{
                                            fontSize: '40px',
                                            marginBottom: '10px',
                                        }}>
                                            📭
                                        </div>
                                        <div style={{
                                            fontSize: '15px',
                                            fontWeight: '700',
                                            color: config.color,
                                            marginBottom: '6px',
                                        }}>
                                            {config.label}
                                        </div>
                                        <div style={{
                                            fontSize: '13px',
                                            color: '#6B7280',
                                            fontWeight: '600',
                                        }}>
                                            این برنامه هنوز تولید نشده است — تحلیلی برای نمایش وجود ندارد
                                        </div>
                                    </div>
                                );
                            }

                            // حالت ۲: تولید شده، بدون هشدار
                            if (!data.warnings || data.warnings.length === 0) {
                                return (
                                    <div key={st} style={{
                                        marginBottom: '16px',
                                        padding: '20px',
                                        background: '#F0FDF4',
                                        borderRadius: '12px',
                                        border: `2px solid #86EFAC`,
                                        borderRight: `5px solid ${config.color}`,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '16px',
                                    }}>
                                        <div style={{ fontSize: '36px' }}>✅</div>
                                        <div>
                                            <div style={{
                                                fontSize: '15px',
                                                fontWeight: '700',
                                                color: config.color,
                                                marginBottom: '4px',
                                            }}>
                                                {config.label}
                                            </div>
                                            <div style={{
                                                fontSize: '13px',
                                                color: '#065F46',
                                                fontWeight: '600',
                                            }}>
                                                این برنامه تولید شده و هیچ هشداری ندارد
                                            </div>
                                        </div>
                                    </div>
                                );
                            }

                            // حالت ۳: تولید شده، با هشدار
                            const groupedWarnings = {};
                            const warningTypeLabels = {
                                'staff_shortage': '🔴 کمبود پرسنل',
                                'staff_surplus': '🟢 اضافه پرسنل',
                                'consecutive_nights': '🔴 شب‌های متوالی',
                                'work_after_night': '🔴 کار بعد از شب',
                                'shift_imbalance': '🟡 عدم تعادل شیفت',
                                'no_shifts': '🔴 بدون شیفت',
                                'no_off': '🟡 آف ناکافی',
                                'low_shifts': '🟡 شیفت کم',
                            };

                            data.warnings.forEach(w => {
                                if (!groupedWarnings[w.type]) {
                                    groupedWarnings[w.type] = [];
                                }
                                groupedWarnings[w.type].push(w);
                            });

                            return (
                                <div key={st} style={{
                                    marginBottom: '20px',
                                    padding: '16px',
                                    background: '#FFFFFF',
                                    borderRadius: '12px',
                                    border: `2px solid ${config.color}`,
                                    borderTop: `5px solid ${config.color}`,
                                }}>
                                    <h4 style={{
                                        margin: '0 0 12px 0',
                                        fontSize: '15px',
                                        color: config.color,
                                        fontWeight: '800',
                                    }}>
                                        {config.label} — {data.warnings.length} هشدار
                                    </h4>

                                    {Object.entries(groupedWarnings).map(([type, items]) => (
                                        <div key={type} style={{ marginBottom: '12px' }}>
                                            <div style={{
                                                fontSize: '13px',
                                                fontWeight: '700',
                                                color: '#374151',
                                                marginBottom: '6px',
                                            }}>
                                                {warningTypeLabels[type] || type} ({items.length})
                                            </div>
                                            <div style={{
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: '4px',
                                            }}>
                                                {items.slice(0, 10).map((w, idx) => (
                                                    <div key={idx} style={{
                                                        padding: '6px 10px',
                                                        background: w.severity === 'high' ? '#FEF2F2' : '#FFFBEB',
                                                        borderRadius: '6px',
                                                        fontSize: '12px',
                                                        color: w.severity === 'high' ? '#991B1B' : '#92400E',
                                                        borderRight: `3px solid ${w.severity === 'high' ? '#DC2626' : '#F59E0B'}`,
                                                    }}>
                                                        {w.message}
                                                    </div>
                                                ))}
                                                {items.length > 10 && (
                                                    <div style={{
                                                        padding: '4px 10px',
                                                        fontSize: '11px',
                                                        color: '#6B7280',
                                                        fontStyle: 'italic',
                                                    }}>
                                                        ... و {items.length - 10} مورد دیگر
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            );
                        })}
                    </div>

                    {/* ✅ مقایسه چهار برنامه */}
                    <div className="ai-section-card">
                        <h3 className="ai-section-title">⚖️ مقایسه چهار برنامه</h3>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                            gap: '16px',
                            marginTop: '16px',
                        }}>
                            {ALL_SCHEDULE_TYPES.map(st => {
                                const data = reportData[st];
                                const config = programConfig[st];

                                if (!data) return null;

                                const statusColors = getStatusColor(data.status);

                                return (
                                    <div key={st} style={{
                                        padding: '16px',
                                        background: '#FFFFFF',
                                        borderRadius: '12px',
                                        border: `2px solid ${config.color}`,
                                        borderTop: `5px solid ${config.color}`,
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            marginBottom: '12px',
                                        }}>
                                            <h4 style={{
                                                margin: 0,
                                                color: config.color,
                                                fontSize: '15px',
                                                fontWeight: '800',
                                            }}>
                                                {config.label}
                                            </h4>
                                            <span style={{
                                                padding: '4px 10px',
                                                borderRadius: '12px',
                                                fontSize: '11px',
                                                fontWeight: '700',
                                                backgroundColor: statusColors.bg,
                                                color: statusColors.color,
                                            }}>
                                                {data.status_display}
                                            </span>
                                        </div>

                                        {!data.exists ? (
                                            <div style={{
                                                padding: '20px',
                                                textAlign: 'center',
                                                color: '#9CA3AF',
                                                fontSize: '13px',
                                            }}>
                                                📭 این برنامه تولید نشده است
                                            </div>
                                        ) : (
                                            <>
                                                <div style={{
                                                    display: 'grid',
                                                    gridTemplateColumns: 'repeat(2, 1fr)',
                                                    gap: '8px',
                                                    marginBottom: '12px',
                                                }}>
                                                    <StatBox label="پرسنل" value={data.staff_count} color="#3B82F6" />
                                                    <StatBox label="کل شیفت‌ها" value={data.total_records} color="#8B5CF6" />
                                                </div>

                                                <div style={{
                                                    display: 'grid',
                                                    gridTemplateColumns: 'repeat(3, 1fr)',
                                                    gap: '6px',
                                                    marginBottom: '12px',
                                                }}>
                                                    <StatBox label="☀️ صبح" value={data.total_m} color="#3498DB" small />
                                                    <StatBox label="🌅 عصر" value={data.total_e} color="#F39C12" small />
                                                    <StatBox label="🌙 شب" value={data.total_n} color="#2C3E50" small />
                                                </div>

                                                <div style={{
                                                    display: 'grid',
                                                    gridTemplateColumns: 'repeat(3, 1fr)',
                                                    gap: '6px',
                                                }}>
                                                    <CoverageBox label="صبح" percent={data.coverage_m} />
                                                    <CoverageBox label="عصر" percent={data.coverage_e} />
                                                    <CoverageBox label="شب" percent={data.coverage_n} />
                                                </div>
                                            </>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* آمار روزانه */}
                    <div className="ai-section-card">
                        <h3 className="ai-section-title">📅 آمار روزانه برنامه‌ها</h3>
                        <div style={{ overflowX: 'auto', marginTop: '12px' }}>
                            <table style={{
                                width: '100%',
                                borderCollapse: 'collapse',
                                fontSize: '12px',
                                minWidth: '1200px',
                            }}>
                                <thead>
                                    <tr style={{ background: '#2C3E50', color: 'white' }}>
                                        <th style={{ padding: '8px', border: '1px solid #34495E' }}>روز</th>
                                        <th style={{ padding: '8px', border: '1px solid #34495E' }}>روز هفته</th>
                                        {ALL_SCHEDULE_TYPES.map(st => (
                                            <th key={st} colSpan="3" style={{
                                                padding: '8px',
                                                border: '1px solid #34495E',
                                                background: programConfig[st].bg,
                                                color: programConfig[st].color,
                                            }}>
                                                {programConfig[st].label}
                                            </th>
                                        ))}
                                    </tr>
                                    <tr style={{ background: '#F3F4F6' }}>
                                        <th style={{ padding: '4px', border: '1px solid #E5E7EB' }}></th>
                                        <th style={{ padding: '4px', border: '1px solid #E5E7EB' }}></th>
                                        {ALL_SCHEDULE_TYPES.map(st => (
                                            <React.Fragment key={st}>
                                                <th style={{ padding: '4px', border: '1px solid #E5E7EB', fontSize: '10px' }}>M</th>
                                                <th style={{ padding: '4px', border: '1px solid #E5E7EB', fontSize: '10px' }}>E</th>
                                                <th style={{ padding: '4px', border: '1px solid #E5E7EB', fontSize: '10px' }}>N</th>
                                            </React.Fragment>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {Array.from({ length: reportData.summary.days_in_month }, (_, i) => {
                                        const day = i + 1;
                                        const dayIndex = reportData.summary.first_day_index + i;
                                        const weekday = reportData.summary.weekdays[dayIndex % 7];

                                        return (
                                            <tr key={day} style={{
                                                background: i % 2 === 0 ? '#FFFFFF' : '#F8F9FA',
                                            }}>
                                                <td style={{
                                                    padding: '6px',
                                                    border: '1px solid #E5E7EB',
                                                    textAlign: 'center',
                                                    fontWeight: '700',
                                                }}>
                                                    {day}
                                                </td>
                                                <td style={{
                                                    padding: '6px',
                                                    border: '1px solid #E5E7EB',
                                                    textAlign: 'center',
                                                    fontSize: '11px',
                                                }}>
                                                    {weekday}
                                                </td>
                                                {ALL_SCHEDULE_TYPES.map(st => {
                                                    const data = reportData[st];
                                                    return (
                                                        <React.Fragment key={`${st}-${day}`}>
                                                            <td style={{ padding: '6px', border: '1px solid #E5E7EB', textAlign: 'center', fontSize: '11px' }}>
                                                                {data?.exists ? data.daily_m[i] : '-'}
                                                            </td>
                                                            <td style={{ padding: '6px', border: '1px solid #E5E7EB', textAlign: 'center', fontSize: '11px' }}>
                                                                {data?.exists ? data.daily_e[i] : '-'}
                                                            </td>
                                                            <td style={{ padding: '6px', border: '1px solid #E5E7EB', textAlign: 'center', fontSize: '11px' }}>
                                                                {data?.exists ? data.daily_n[i] : '-'}
                                                            </td>
                                                        </React.Fragment>
                                                    );
                                                })}
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}

            {siteSettings?.footer_text && (
                <footer className="site-footer">
                    {siteSettings.footer_text}
                </footer>
            )}
        </div>
    );
}

// ✅ کامپوننت کمکی: کارت خلاصه
function SummaryCard({ title, value, icon, color }) {
    return (
        <div style={{
            padding: '16px',
            background: '#FFFFFF',
            borderRadius: '12px',
            border: `2px solid ${color}20`,
            boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
        }}>
            <div style={{ fontSize: '24px', marginBottom: '4px' }}>{icon}</div>
            <div style={{
                fontSize: '20px',
                fontWeight: '800',
                color: color,
                marginBottom: '4px',
            }}>{value}</div>
            <div style={{
                fontSize: '12px',
                color: '#6B7280',
                fontWeight: '600',
            }}>{title}</div>
        </div>
    );
}

// ✅ کامپوننت کمکی: جعبه آمار
function StatBox({ label, value, color, small = false }) {
    return (
        <div style={{
            padding: small ? '6px' : '10px',
            background: `${color}15`,
            borderRadius: '8px',
            textAlign: 'center',
        }}>
            <div style={{
                fontSize: small ? '10px' : '11px',
                color: '#6B7280',
                fontWeight: '600',
                marginBottom: '2px',
            }}>{label}</div>
            <div style={{
                fontSize: small ? '16px' : '18px',
                fontWeight: '800',
                color: color,
            }}>{value}</div>
        </div>
    );
}

// ✅ کامپوننت کمکی: پوشش اهداف
function CoverageBox({ label, percent }) {
    let bg = '#D1FAE5';
    let color = '#065F46';
    if (percent < 95) {
        bg = '#FEF3C7';
        color = '#92400E';
    }
    if (percent < 80) {
        bg = '#FEE2E2';
        color = '#991B1B';
    }

    return (
        <div style={{
            padding: '6px',
            background: bg,
            borderRadius: '8px',
            textAlign: 'center',
        }}>
            <div style={{
                fontSize: '10px',
                color: color,
                fontWeight: '600',
            }}>{label}</div>
            <div style={{
                fontSize: '15px',
                fontWeight: '800',
                color: color,
            }}>{percent}%</div>
        </div>
    );
}

export default ReportsPage;