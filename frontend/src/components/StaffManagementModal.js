// src/components/StaffManagementModal.js
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import api from '../services/api';

function StaffManagementModal({ wardId, year, month, scheduleType, wardName, onClose, onUpdate }) {
    const [activeStaff, setActiveStaff] = useState([]);
    const [removedStaff, setRemovedStaff] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchText, setSearchText] = useState('');
    const [reason, setReason] = useState('');
    const [selectedStaff, setSelectedStaff] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);

    useEffect(() => {
        loadStaff();
    }, [wardId, year, month, scheduleType]);

    const loadStaff = async () => {
        setLoading(true);
        try {
            const res = await api.get(
                `/api/ai/ward-staff/?ward_id=${wardId}&year=${year}&month=${month}&schedule_type=${scheduleType}`
            );
            setActiveStaff(res.data.active_staff || []);
            setRemovedStaff(res.data.removed_staff || []);
        } catch (err) {
            console.error('خطا در دریافت لیست پرسنل:', err);
            alert('❌ خطا در دریافت لیست پرسنل');
        } finally {
            setLoading(false);
        }
    };

    const confirmRemove = async () => {
        if (!selectedStaff || isProcessing) return;
        setIsProcessing(true);
        try {
            await api.post('/api/ai/exclude-staff/', {
                ward_id: wardId,
                year,
                month,
                schedule_type: scheduleType,
                staff_id: selectedStaff.staff_id,
                reason: reason,
            });
            setSelectedStaff(null);
            setReason('');
            await loadStaff();
            if (onUpdate) onUpdate();
        } catch (err) {
            console.error('خطا در حذف پرستار:', err);
            alert('❌ خطا در حذف پرستار');
        } finally {
            setIsProcessing(false);
        }
    };

    const handleRestore = async (staff) => {
        if (!window.confirm(`آیا می‌خواهید «${staff.staff_name}» را به برنامه برگردانید؟`)) {
            return;
        }
        setIsProcessing(true);
        try {
            await api.post('/api/ai/restore-staff/', {
                ward_id: wardId,
                year,
                month,
                schedule_type: scheduleType,
                staff_id: staff.staff_id,
            });
            await loadStaff();
            if (onUpdate) onUpdate();
        } catch (err) {
            console.error('خطا در بازگرداندن پرستار:', err);
            alert('❌ خطا در بازگرداندن پرستار');
        } finally {
            setIsProcessing(false);
        }
    };

    const filteredActive = activeStaff.filter(s =>
        !searchText || s.staff_name.toLowerCase().includes(searchText.toLowerCase())
    );

    const scheduleTypeLabel = {
        main: '🤖 اصلی',
        oncall: '📞 آنکالی',
        crisis: '🚨 بحران',
    }[scheduleType] || '🤖 اصلی';

    return createPortal(
        <div
            onClick={onClose}
            style={{
                position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
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
                    maxWidth: '750px',
                    width: '100%',
                    maxHeight: '90vh',
                    overflow: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                }}
            >
                {/* Header */}
                <div style={{
                    padding: '20px 24px',
                    background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                    color: 'white',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    position: 'sticky',
                    top: 0,
                    zIndex: 10,
                    gap: '12px',
                }}>
                    <div style={{ flex: 1 }}>
                        <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '800' }}>
                            👥 مدیریت پرسنل برنامه
                        </h2>
                        <div style={{
                            fontSize: '12px',
                            marginTop: '6px',
                            opacity: 0.95,
                            display: 'flex',
                            gap: '12px',
                            flexWrap: 'wrap',
                        }}>
                            <span>🏥 {wardName || 'بخش'}</span>
                            <span>📅 {year}/{month}</span>
                            <span>{scheduleTypeLabel}</span>
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
                            flexShrink: 0,
                            lineHeight: 1,
                        }}
                    >
                        ×
                    </button>
                </div>

                {/* Body */}
                <div style={{ padding: '20px 24px' }}>
                    {loading ? (
                        <div style={{ padding: '60px 20px', textAlign: 'center', color: '#6B7280' }}>
                            <div style={{
                                width: '40px', height: '40px',
                                border: '4px solid #E5E7EB',
                                borderTop: '4px solid #8B5CF6',
                                borderRadius: '50%',
                                animation: 'spin 0.8s linear infinite',
                                margin: '0 auto 16px',
                            }}></div>
                            ⏳ در حال بارگذاری...
                        </div>
                    ) : (
                        <>
                            {/* راهنما */}
                            <div style={{
                                padding: '12px 16px',
                                background: '#EFF6FF',
                                border: '1px solid #BFDBFE',
                                borderRadius: '10px',
                                marginBottom: '20px',
                                fontSize: '13px',
                                color: '#1E40AF',
                                lineHeight: '1.7',
                            }}>
                                💡 <b>راهنما:</b> اگر پرستاری به اشتباه در این بخش تعریف شده، می‌توانید او را از برنامه‌ی این ماه <b>حذف موقت</b> کنید. این حذف فقط برای این ماه و این نوع برنامه اعمال می‌شود.
                            </div>

                            {/* جستجو */}
                            <input
                                type="text"
                                placeholder="🔍 جستجوی نام پرستار..."
                                value={searchText}
                                onChange={(e) => setSearchText(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '10px 14px',
                                    borderRadius: '8px',
                                    border: '1px solid #D1D5DB',
                                    fontSize: '14px',
                                    fontFamily: 'inherit',
                                    marginBottom: '16px',
                                    boxSizing: 'border-box',
                                }}
                            />

                            {/* پرسنل فعال */}
                            <h3 style={{
                                fontSize: '14px',
                                fontWeight: '800',
                                color: '#065F46',
                                marginBottom: '10px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                            }}>
                                ✅ پرسنل فعال در برنامه
                                <span style={{
                                    padding: '2px 10px',
                                    background: '#D1FAE5',
                                    borderRadius: '10px',
                                    fontSize: '12px',
                                }}>
                                    {filteredActive.length}
                                </span>
                            </h3>

                            <div style={{
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '8px',
                                marginBottom: '24px',
                                maxHeight: '300px',
                                overflowY: 'auto',
                                paddingLeft: '4px',
                            }}>
                                {filteredActive.length === 0 ? (
                                    <div style={{
                                        padding: '30px',
                                        textAlign: 'center',
                                        color: '#9CA3AF',
                                        fontSize: '13px',
                                        background: '#F9FAFB',
                                        borderRadius: '10px',
                                    }}>
                                        {searchText ? 'نتیجه‌ای یافت نشد' : 'هیچ پرستاری در این برنامه وجود ندارد'}
                                    </div>
                                ) : (
                                    filteredActive.map(staff => (
                                        <div key={staff.staff_id} style={{
                                            padding: '12px 16px',
                                            background: '#F0FDF4',
                                            borderRadius: '10px',
                                            border: '1px solid #86EFAC',
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            gap: '12px',
                                        }}>
                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                <div style={{
                                                    fontWeight: '700',
                                                    fontSize: '14px',
                                                    color: '#065F46',
                                                    marginBottom: '2px',
                                                    whiteSpace: 'nowrap',
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                }}>
                                                    {staff.staff_name}
                                                </div>
                                                <div style={{
                                                    fontSize: '11px',
                                                    color: '#6B7280',
                                                    display: 'flex',
                                                    gap: '10px',
                                                    flexWrap: 'wrap',
                                                }}>
                                                    {staff.position_label && <span>👨‍⚕️ {staff.position_label}</span>}
                                                    {staff.employment_status && <span>📋 {staff.employment_status}</span>}
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => setSelectedStaff(staff)}
                                                disabled={isProcessing}
                                                style={{
                                                    padding: '6px 14px',
                                                    background: '#FEE2E2',
                                                    color: '#991B1B',
                                                    border: '1px solid #FCA5A5',
                                                    borderRadius: '8px',
                                                    cursor: isProcessing ? 'wait' : 'pointer',
                                                    fontWeight: '700',
                                                    fontSize: '12px',
                                                    fontFamily: 'inherit',
                                                    whiteSpace: 'nowrap',
                                                    flexShrink: 0,
                                                }}
                                            >
                                                🗑️ حذف موقت
                                            </button>
                                        </div>
                                    ))
                                )}
                            </div>

                            {/* پرسنل حذف‌شده */}
                            {removedStaff.length > 0 && (
                                <>
                                    <h3 style={{
                                        fontSize: '14px',
                                        fontWeight: '800',
                                        color: '#991B1B',
                                        marginBottom: '10px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                    }}>
                                        🗑️ پرسنل حذف‌شده
                                        <span style={{
                                            padding: '2px 10px',
                                            background: '#FEE2E2',
                                            borderRadius: '10px',
                                            fontSize: '12px',
                                        }}>
                                            {removedStaff.length}
                                        </span>
                                    </h3>
                                    <div style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '8px',
                                    }}>
                                        {removedStaff.map(staff => (
                                            <div key={staff.staff_id} style={{
                                                padding: '12px 16px',
                                                background: '#FEF2F2',
                                                borderRadius: '10px',
                                                border: '1px solid #FCA5A5',
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                gap: '12px',
                                            }}>
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    <div style={{
                                                        fontWeight: '700',
                                                        fontSize: '14px',
                                                        color: '#991B1B',
                                                        marginBottom: '2px',
                                                    }}>
                                                        {staff.staff_name}
                                                    </div>
                                                    {staff.reason && (
                                                        <div style={{
                                                            fontSize: '11px',
                                                            color: '#991B1B',
                                                            marginTop: '2px',
                                                            fontStyle: 'italic',
                                                        }}>
                                                            📝 {staff.reason}
                                                        </div>
                                                    )}
                                                    {staff.created_by_name && (
                                                        <div style={{
                                                            fontSize: '10px',
                                                            color: '#6B7280',
                                                            marginTop: '2px',
                                                        }}>
                                                            👤 توسط: {staff.created_by_name}
                                                        </div>
                                                    )}
                                                </div>
                                                <button
                                                    onClick={() => handleRestore(staff)}
                                                    disabled={isProcessing}
                                                    style={{
                                                        padding: '6px 14px',
                                                        background: '#D1FAE5',
                                                        color: '#065F46',
                                                        border: '1px solid #86EFAC',
                                                        borderRadius: '8px',
                                                        cursor: isProcessing ? 'wait' : 'pointer',
                                                        fontWeight: '700',
                                                        fontSize: '12px',
                                                        fontFamily: 'inherit',
                                                        whiteSpace: 'nowrap',
                                                        flexShrink: 0,
                                                    }}
                                                >
                                                    ↩️ بازگرداندن
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Modal دلیل حذف */}
            {selectedStaff && (
                <div
                    onClick={() => { setSelectedStaff(null); setReason(''); }}
                    style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(0,0,0,0.7)',
                        zIndex: 999999,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '20px',
                    }}
                >
                    <div
                        onClick={(e) => e.stopPropagation()}
                        style={{
                            background: 'white',
                            borderRadius: '12px',
                            padding: '24px',
                            maxWidth: '420px',
                            width: '100%',
                        }}
                    >
                        <h3 style={{
                            margin: '0 0 16px 0',
                            fontSize: '16px',
                            fontWeight: '800',
                            color: '#991B1B',
                        }}>
                            🗑️ حذف موقت از برنامه
                        </h3>
                        <div style={{
                            padding: '10px 14px',
                            background: '#FEF2F2',
                            borderRadius: '8px',
                            marginBottom: '16px',
                            fontSize: '13px',
                            color: '#991B1B',
                            fontWeight: '700',
                        }}>
                            👤 {selectedStaff.staff_name}
                        </div>
                        <p style={{
                            fontSize: '13px',
                            color: '#6B7280',
                            marginBottom: '8px',
                        }}>
                            دلیل حذف (اختیاری):
                        </p>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="مثلاً: انتقال به بخش دیگر، اشتباه در تعریف، ..."
                            style={{
                                width: '100%',
                                padding: '10px 12px',
                                borderRadius: '8px',
                                border: '1px solid #D1D5DB',
                                fontSize: '13px',
                                fontFamily: 'inherit',
                                minHeight: '80px',
                                boxSizing: 'border-box',
                                marginBottom: '16px',
                                resize: 'vertical',
                            }}
                        />
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                                onClick={confirmRemove}
                                disabled={isProcessing}
                                style={{
                                    flex: 1,
                                    padding: '10px',
                                    background: isProcessing ? '#9CA3AF' : '#DC2626',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: isProcessing ? 'wait' : 'pointer',
                                    fontWeight: '700',
                                    fontFamily: 'inherit',
                                    fontSize: '13px',
                                }}
                            >
                                {isProcessing ? '⏳ در حال حذف...' : '✅ تایید حذف'}
                            </button>
                            <button
                                onClick={() => { setSelectedStaff(null); setReason(''); }}
                                disabled={isProcessing}
                                style={{
                                    flex: 1,
                                    padding: '10px',
                                    background: '#F3F4F6',
                                    color: '#374151',
                                    border: '1px solid #D1D5DB',
                                    borderRadius: '8px',
                                    cursor: isProcessing ? 'wait' : 'pointer',
                                    fontWeight: '700',
                                    fontFamily: 'inherit',
                                    fontSize: '13px',
                                }}
                            >
                                انصراف
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <style>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>,
        document.body
    );
}

export default StaffManagementModal;