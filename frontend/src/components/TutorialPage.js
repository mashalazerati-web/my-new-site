// src/components/TutorialPage.js
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../services/api';
import { TUTORIALS } from '../data/tutorials';
import { MONTH_NAMES } from '../constants/persianCalendar';
import ProfileMenu from './ProfileMenu';
import '../styles/index.css';

function TutorialPage() {
    const navigate = useNavigate();
    const location = useLocation();

    const [user, setUser] = useState(null);
    const [userRole, setUserRole] = useState('nurse');
    const [selectedRole, setSelectedRole] = useState('nurse');
    const [selectedSection, setSelectedSection] = useState(null);
    const [searchText, setSearchText] = useState('');
    const [showFAQ, setShowFAQ] = useState(true);

    // ✅ بارگذاری کاربر
    useEffect(() => {
        const loadUser = async () => {
            try {
                const res = await api.get('/api/users/me/');
                const profileRes = await api.get('/api/profiles/');
                const profile = profileRes.data.find(p => p.user?.username === res.data.username);

                const role = profile?.role || 'nurse';
                setUser({
                    ...res.data,
                    avatar_url: profile?.avatar_url || null,
                    role: role,
                });

                // ✅ پیش‌فرض: نقش کاربر
                const roleMap = {
                    'staff': 'nurse',
                    'head': 'head',
                    'supervisor': 'supervisor',
                    'admin': 'matron',
                };
                const initialRole = roleMap[role] || 'nurse';
                setSelectedRole(initialRole);

                // ✅ اگر URL نقش دارد
                const urlRole = new URLSearchParams(location.search).get('role');
                if (urlRole && TUTORIALS[urlRole]) {
                    setSelectedRole(urlRole);
                }
            } catch (error) {
                console.error('خطا در بارگذاری کاربر:', error);
            }
        };
        loadUser();
    }, []);

    // ✅ سکشن پیش‌فرض
    useEffect(() => {
        const tutorial = TUTORIALS[selectedRole];
        if (tutorial && tutorial.sections.length > 0) {
            setSelectedSection(tutorial.sections[0]);
        }
    }, [selectedRole]);

    // ✅ فیلتر جستجو
    const filterSections = (sections) => {
        if (!searchText.trim()) return sections;
        const query = searchText.toLowerCase();
        return sections.filter(section =>
            section.title.toLowerCase().includes(query) ||
            section.content.toLowerCase().includes(query)
        );
    };

    const currentTutorial = TUTORIALS[selectedRole];
    const filteredSections = currentTutorial ? filterSections(currentTutorial.sections) : [];

    // ✅ تعیین آدرس داشبورد بر اساس نقش
    const handleBackToDashboard = () => {
        const role = user?.role || 'staff';
        if (role === 'head') navigate('/head-schedule');
        else if (role === 'supervisor') navigate('/supervisor-schedule');
        else if (role === 'admin') navigate('/matron-schedule');
        else navigate('/dashboard');
    };

    return (
        <div className="dashboard-container role-head">
            <header className="header role-head">
                <div className="header-info">
                    <h1>📚 آموزش خودکار</h1>
                    <p>👤 {user?.first_name || ''} {user?.last_name || ''} - راهنمای گام‌به‌گام</p>
                </div>
                <div className="header-buttons">
                    <button
                        className="header-btn"
                        onClick={handleBackToDashboard}
                    >
                        ↩️ بازگشت به داشبورد
                    </button>
                    <ProfileMenu
                        user={user}
                        onUserUpdate={(newUser) => setUser(newUser)}
                    />
                </div>
            </header>

            {/* ============================================ */}
            {/* انتخاب نقش */}
            {/* ============================================ */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '12px',
                marginBottom: '24px',
            }}>
                {Object.values(TUTORIALS).map(tutorial => (
                    <button
                        key={tutorial.role}
                        onClick={() => setSelectedRole(tutorial.role)}
                        style={{
                            padding: '16px',
                            background: selectedRole === tutorial.role
                                ? `linear-gradient(135deg, ${tutorial.color} 0%, ${tutorial.color}dd 100%)`
                                : 'white',
                            color: selectedRole === tutorial.role ? 'white' : '#374151',
                            border: `2px solid ${selectedRole === tutorial.role ? tutorial.color : '#E5E7EB'}`,
                            borderRadius: '12px',
                            cursor: 'pointer',
                            fontWeight: '800',
                            fontSize: '15px',
                            fontFamily: 'inherit',
                            textAlign: 'center',
                            transition: 'all 0.2s',
                            boxShadow: selectedRole === tutorial.role
                                ? `0 4px 12px ${tutorial.color}40`
                                : '0 2px 4px rgba(0,0,0,0.05)',
                        }}
                    >
                        <div style={{ fontSize: '28px', marginBottom: '8px' }}>
                            {tutorial.icon}
                        </div>
                        <div>{tutorial.title}</div>
                        {user?.role && (
                            (user.role === 'staff' && tutorial.role === 'nurse') ||
                            (user.role === 'head' && tutorial.role === 'head') ||
                            (user.role === 'supervisor' && tutorial.role === 'supervisor') ||
                            (user.role === 'admin' && tutorial.role === 'matron')
                        ) && (
                            <div style={{
                                marginTop: '6px',
                                fontSize: '11px',
                                padding: '2px 8px',
                                borderRadius: '8px',
                                background: selectedRole === tutorial.role ? 'rgba(255,255,255,0.2)' : '#F3F4F6',
                                display: 'inline-block',
                            }}>
                                نقش شما
                            </div>
                        )}
                    </button>
                ))}
            </div>

            {/* ============================================ */}
            {/* محتوای اصلی */}
            {/* ============================================ */}
            {currentTutorial && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'minmax(220px, 280px) 1fr',
                    gap: '20px',
                    alignItems: 'start',
                }}>
                    {/* منوی کناری */}
                    <div style={{
                        background: 'white',
                        borderRadius: '12px',
                        padding: '16px',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                        position: 'sticky',
                        top: '20px',
                    }}>
                        {/* جستجو */}
                        <input
                            type="text"
                            placeholder="🔍 جستجو در آموزش..."
                            value={searchText}
                            onChange={(e) => setSearchText(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '10px 12px',
                                borderRadius: '8px',
                                border: '1px solid #D1D5DB',
                                fontSize: '13px',
                                marginBottom: '12px',
                                fontFamily: 'inherit',
                                boxSizing: 'border-box',
                            }}
                        />

                        <h3 style={{
                            margin: '0 0 12px 0',
                            fontSize: '14px',
                            fontWeight: '800',
                            color: '#0F172A',
                            paddingBottom: '8px',
                            borderBottom: '2px solid #F3F4F6',
                        }}>
                            📖 سرفصل‌ها
                        </h3>

                        {filteredSections.length === 0 ? (
                            <div style={{
                                padding: '20px',
                                textAlign: 'center',
                                color: '#9CA3AF',
                                fontSize: '13px',
                            }}>
                                نتیجه‌ای یافت نشد
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                {filteredSections.map(section => (
                                    <button
                                        key={section.id}
                                        onClick={() => setSelectedSection(section)}
                                        style={{
                                            padding: '10px 12px',
                                            background: selectedSection?.id === section.id
                                                ? currentTutorial.color + '15'
                                                : 'transparent',
                                            color: selectedSection?.id === section.id
                                                ? currentTutorial.color
                                                : '#374151',
                                            border: 'none',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            fontWeight: selectedSection?.id === section.id ? '800' : '600',
                                            fontSize: '13px',
                                            fontFamily: 'inherit',
                                            textAlign: 'right',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            transition: 'all 0.15s',
                                        }}
                                        onMouseEnter={(e) => {
                                            if (selectedSection?.id !== section.id) {
                                                e.currentTarget.style.background = '#F9FAFB';
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (selectedSection?.id !== section.id) {
                                                e.currentTarget.style.background = 'transparent';
                                            }
                                        }}
                                    >
                                        <span style={{ fontSize: '16px' }}>{section.icon}</span>
                                        <span style={{ flex: 1 }}>{section.title}</span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* محتوای سکشن */}
                    <div style={{
                        background: 'white',
                        borderRadius: '12px',
                        padding: '28px',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                    }}>
                        {selectedSection ? (
                            <>
                                {/* هدر */}
                                <div style={{
                                    paddingBottom: '16px',
                                    marginBottom: '20px',
                                    borderBottom: `3px solid ${currentTutorial.color}`,
                                }}>
                                    <div style={{
                                        fontSize: '14px',
                                        color: currentTutorial.color,
                                        fontWeight: '700',
                                        marginBottom: '6px',
                                    }}>
                                        {currentTutorial.icon} {currentTutorial.title}
                                    </div>
                                    <h1 style={{
                                        margin: 0,
                                        fontSize: '24px',
                                        fontWeight: '800',
                                        color: '#0F172A',
                                    }}>
                                        {selectedSection.icon} {selectedSection.title}
                                    </h1>
                                </div>

                                {/* محتوا */}
                                <div
                                    className="tutorial-content"
                                    dangerouslySetInnerHTML={{ __html: selectedSection.content }}
                                    style={{
                                        fontSize: '14px',
                                        lineHeight: '2',
                                        color: '#374151',
                                    }}
                                />

                                {/* نکات مهم */}
                                {selectedSection.tips && selectedSection.tips.length > 0 && (
                                    <div style={{
                                        marginTop: '24px',
                                        padding: '16px 20px',
                                        background: 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)',
                                        borderRight: '5px solid #F59E0B',
                                        borderRadius: '12px',
                                    }}>
                                        <div style={{
                                            fontSize: '15px',
                                            fontWeight: '800',
                                            color: '#92400E',
                                            marginBottom: '10px',
                                        }}>
                                            ⚠️ نکات مهم
                                        </div>
                                        <ul style={{
                                            margin: 0,
                                            padding: '0 20px 0 0',
                                            fontSize: '13px',
                                            color: '#78350F',
                                            lineHeight: '1.8',
                                        }}>
                                            {selectedSection.tips.map((tip, idx) => (
                                                <li key={idx}>{tip}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* سؤالات متداول */}
                                {selectedSection.faqs && selectedSection.faqs.length > 0 && (
                                    <div style={{
                                        marginTop: '24px',
                                        padding: '20px',
                                        background: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)',
                                        borderRadius: '12px',
                                        border: '2px solid #93C5FD',
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            marginBottom: '16px',
                                        }}>
                                            <div style={{
                                                fontSize: '16px',
                                                fontWeight: '800',
                                                color: '#1E40AF',
                                            }}>
                                                ❓ سؤالات متداول
                                            </div>
                                            <button
                                                onClick={() => setShowFAQ(!showFAQ)}
                                                style={{
                                                    padding: '4px 10px',
                                                    background: 'white',
                                                    border: '1px solid #93C5FD',
                                                    borderRadius: '6px',
                                                    cursor: 'pointer',
                                                    fontSize: '12px',
                                                    fontWeight: '700',
                                                    fontFamily: 'inherit',
                                                    color: '#1E40AF',
                                                }}
                                            >
                                                {showFAQ ? '▲ بستن' : '▼ نمایش'}
                                            </button>
                                        </div>

                                        {showFAQ && (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                                {selectedSection.faqs.map((faq, idx) => (
                                                    <details key={idx} style={{
                                                        padding: '12px 16px',
                                                        background: 'white',
                                                        borderRadius: '10px',
                                                        border: '1px solid #BFDBFE',
                                                    }}>
                                                        <summary style={{
                                                            cursor: 'pointer',
                                                            fontWeight: '700',
                                                            fontSize: '13px',
                                                            color: '#1E40AF',
                                                        }}>
                                                            {faq.q}
                                                        </summary>
                                                        <p style={{
                                                            margin: '10px 0 0 0',
                                                            fontSize: '13px',
                                                            color: '#374151',
                                                            lineHeight: '1.8',
                                                        }}>
                                                            {faq.a}
                                                        </p>
                                                    </details>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* دکمه‌های ناوبری */}
                                <div style={{
                                    marginTop: '32px',
                                    paddingTop: '20px',
                                    borderTop: '1px solid #E5E7EB',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    gap: '12px',
                                }}>
                                    <button
                                        onClick={() => {
                                            const idx = currentTutorial.sections.findIndex(s => s.id === selectedSection.id);
                                            if (idx > 0) setSelectedSection(currentTutorial.sections[idx - 1]);
                                        }}
                                        disabled={currentTutorial.sections.findIndex(s => s.id === selectedSection.id) === 0}
                                        style={{
                                            padding: '10px 20px',
                                            background: 'white',
                                            border: '1px solid #D1D5DB',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            fontWeight: '700',
                                            fontFamily: 'inherit',
                                            fontSize: '13px',
                                            opacity: currentTutorial.sections.findIndex(s => s.id === selectedSection.id) === 0 ? 0.4 : 1,
                                        }}
                                    >
                                        ← قبلی
                                    </button>

                                    <button
                                        onClick={() => {
                                            const idx = currentTutorial.sections.findIndex(s => s.id === selectedSection.id);
                                            if (idx < currentTutorial.sections.length - 1) setSelectedSection(currentTutorial.sections[idx + 1]);
                                        }}
                                        disabled={currentTutorial.sections.findIndex(s => s.id === selectedSection.id) === currentTutorial.sections.length - 1}
                                        style={{
                                            padding: '10px 20px',
                                            background: currentTutorial.color,
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            fontWeight: '700',
                                            fontFamily: 'inherit',
                                            fontSize: '13px',
                                            opacity: currentTutorial.sections.findIndex(s => s.id === selectedSection.id) === currentTutorial.sections.length - 1 ? 0.4 : 1,
                                        }}
                                    >
                                        بعدی →
                                    </button>
                                </div>
                            </>
                        ) : (
                            <div style={{
                                padding: '60px 20px',
                                textAlign: 'center',
                                color: '#9CA3AF',
                            }}>
                                <div style={{ fontSize: '48px', marginBottom: '12px' }}>📖</div>
                                <div>یک سرفصل را از منوی کناری انتخاب کنید</div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default TutorialPage;