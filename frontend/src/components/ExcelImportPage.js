// src/components/ExcelImportPage.js
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { API_BASE_URL } from '../config';
import '../styles/index.css';

function ExcelImportPage() {
    const navigate = useNavigate();
    const fileInputRef = useRef(null);

    const [user, setUser] = useState(null);
    const [siteSettings, setSiteSettings] = useState(null);

    // ✅ استیت‌های آپلود
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState(null);
    const [uploadError, setUploadError] = useState(null);
    const [uploadHistory, setUploadHistory] = useState([]);
    const [loadingHistory, setLoadingHistory] = useState(false);

    // ✅ وضعیت Drag & Drop
    const [isDragging, setIsDragging] = useState(false);

    useEffect(() => {
        loadUser();
        loadSiteSettings();
        loadHistory();
    }, []);

    const loadUser = async () => {
        try {
            const res = await api.get('/api/users/me/');
            const profileRes = await api.get('/api/profiles/');
            const profile = profileRes.data.find(p => p.user?.username === res.data.username);

            setUser({
                ...res.data,
                avatar_url: profile?.avatar_url || null,
                role: profile?.role || 'staff',
            });
        } catch (error) {
            console.error('خطا در بارگذاری کاربر:', error);
            if (error.response?.status === 401) {
                navigate('/login');
            }
        }
    };

    const loadSiteSettings = async () => {
        try {
            const res = await api.get('/api/site-settings/');
            setSiteSettings(res.data);
        } catch (err) {
            console.error('خطا در تنظیمات سایت:', err);
        }
    };

    const loadHistory = async () => {
        setLoadingHistory(true);
        try {
            const res = await api.get('/api/excel-uploads/history/');
            setUploadHistory(res.data || []);
        } catch (err) {
            console.error('خطا در تاریخچه:', err);
        } finally {
            setLoadingHistory(false);
        }
    };

    // ============================================================
    // دانلود قالب
    // ============================================================
    const handleDownloadTemplate = () => {
        const url = `${API_BASE_URL}/api/excel-uploads/download-template/`;
        window.open(url, '_blank');
    };

    // ============================================================
    // انتخاب فایل
    // ============================================================
    const handleFileSelect = (file) => {
        if (!file) return;

        // اعتبارسنجی سمت کاربر
        if (!file.name.toLowerCase().endsWith('.xlsx')) {
            setUploadError('❌ فقط فایل با فرمت .xlsx مجاز است');
            setSelectedFile(null);
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            setUploadError(`❌ حجم فایل نباید بیشتر از ۵ مگابایت باشد (فعلی: ${(file.size / 1024 / 1024).toFixed(1)}MB)`);
            setSelectedFile(null);
            return;
        }

        setSelectedFile(file);
        setUploadError(null);
        setUploadResult(null);
    };

    const handleInputChange = (e) => {
        const file = e.target.files[0];
        handleFileSelect(file);
    };

    // ============================================================
    // Drag & Drop
    // ============================================================
    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files[0];
        handleFileSelect(file);
    };

    // ============================================================
    // آپلود
    // ============================================================
    const handleUpload = async () => {
        if (!selectedFile) {
            setUploadError('❌ لطفاً یک فایل انتخاب کنید');
            return;
        }

        setIsUploading(true);
        setUploadError(null);
        setUploadResult(null);

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const res = await api.post('/api/excel-uploads/upload/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                timeout: 120000,  // ۲ دقیقه
            });

            setUploadResult(res.data);
            setSelectedFile(null);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }

            // رفرش تاریخچه
            loadHistory();

        } catch (err) {
            console.error('خطا در آپلود:', err);
            const msg = err.response?.data?.error || 'خطا در آپلود فایل';
            setUploadError(`❌ ${msg}`);
        } finally {
            setIsUploading(false);
        }
    };

    const handleClearFile = () => {
        setSelectedFile(null);
        setUploadError(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const formatFileSize = (bytes) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
    };

    const formatDate = (dateStr) => {
        try {
            return new Date(dateStr).toLocaleDateString('fa-IR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="dashboard-container role-matron">
            {/* هدر */}
            <header className="header role-matron">
                <div className="header-info">
                    <h1>📤 آپلود اطلاعات از اکسل</h1>
                    <p>👤 {user?.first_name || ''} {user?.last_name || ''} - ورود گروهی اطلاعات</p>
                </div>

                <div className="header-buttons">
                    <button
                        className="header-btn"
                        onClick={() => navigate('/matron-schedule')}
                    >
                        ↩️ بازگشت به داشبورد
                    </button>
                </div>
            </header>

            {/* ============================================ */}
            {/* گام ۱: دانلود قالب */}
            {/* ============================================ */}
            <div style={{
                background: 'white',
                borderRadius: '16px',
                padding: '24px',
                marginBottom: '20px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                border: '2px solid #DBEAFE',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
                    <div style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '24px',
                        fontWeight: 'bold',
                        flexShrink: 0,
                    }}>
                        ۱
                    </div>
                    <div>
                        <h2 style={{
                            margin: 0,
                            fontSize: '18px',
                            fontWeight: '800',
                            color: '#0F172A',
                        }}>
                            دانلود قالب نمونه
                        </h2>
                        <p style={{
                            margin: '4px 0 0 0',
                            fontSize: '13px',
                            color: '#6B7280',
                        }}>
                            ابتدا فایل نمونه را دانلود کنید
                        </p>
                    </div>
                </div>

                <div style={{
                    padding: '16px',
                    background: '#F8FAFC',
                    borderRadius: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                }}>
                    <div style={{ flex: 1, minWidth: '200px' }}>
                        <div style={{
                            fontSize: '14px',
                            fontWeight: '700',
                            color: '#1E40AF',
                            marginBottom: '4px',
                        }}>
                            📄 نمونه_اطلاعات.xlsx
                        </div>
                        <div style={{
                            fontSize: '12px',
                            color: '#6B7280',
                            lineHeight: '1.6',
                        }}>
                            شامل ۴ شیت: پرسنل، بخش‌ها، تعطیلات، کدهای_شیفت
                            <br />
                            به همراه راهنمای کامل
                        </div>
                    </div>
                    <button
                        onClick={handleDownloadTemplate}
                        style={{
                            padding: '12px 24px',
                            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '10px',
                            cursor: 'pointer',
                            fontWeight: '700',
                            fontSize: '14px',
                            fontFamily: 'inherit',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)',
                        }}
                    >
                        📥 دانلود قالب
                    </button>
                </div>
            </div>

            {/* ============================================ */}
            {/* گام ۲: آپلود فایل */}
            {/* ============================================ */}
            <div style={{
                background: 'white',
                borderRadius: '16px',
                padding: '24px',
                marginBottom: '20px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                border: '2px solid #FEF3C7',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
                    <div style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '24px',
                        fontWeight: 'bold',
                        flexShrink: 0,
                    }}>
                        ۲
                    </div>
                    <div>
                        <h2 style={{
                            margin: 0,
                            fontSize: '18px',
                            fontWeight: '800',
                            color: '#0F172A',
                        }}>
                            آپلود فایل اکسل
                        </h2>
                        <p style={{
                            margin: '4px 0 0 0',
                            fontSize: '13px',
                            color: '#6B7280',
                        }}>
                            فایل پر‌شده را اینجا آپلود کنید
                        </p>
                    </div>
                </div>

                {/* Drag & Drop Area */}
                {!selectedFile ? (
                    <div
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                        style={{
                            padding: '48px 24px',
                            border: `3px dashed ${isDragging ? '#3B82F6' : '#CBD5E1'}`,
                            borderRadius: '12px',
                            background: isDragging ? '#EFF6FF' : '#F8FAFC',
                            textAlign: 'center',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                        }}
                    >
                        <div style={{
                            fontSize: '48px',
                            marginBottom: '12px',
                        }}>
                            {isDragging ? '📂' : '📁'}
                        </div>
                        <div style={{
                            fontSize: '16px',
                            fontWeight: '700',
                            color: '#1E40AF',
                            marginBottom: '6px',
                        }}>
                            {isDragging ? 'فایل را رها کنید' : 'فایل را اینجا بکشید'}
                        </div>
                        <div style={{
                            fontSize: '13px',
                            color: '#6B7280',
                            marginBottom: '12px',
                        }}>
                            یا کلیک کنید تا انتخاب شود
                        </div>
                        <div style={{
                            fontSize: '11px',
                            color: '#9CA3AF',
                            fontWeight: '600',
                        }}>
                            فقط فایل xlsx — حداکثر ۵ مگابایت
                        </div>
                    </div>
                ) : (
                    <div style={{
                        padding: '20px',
                        background: 'linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)',
                        border: '2px solid #86EFAC',
                        borderRadius: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '16px',
                        flexWrap: 'wrap',
                    }}>
                        <div style={{
                            fontSize: '36px',
                            flexShrink: 0,
                        }}>
                            📊
                        </div>
                        <div style={{ flex: 1, minWidth: '180px' }}>
                            <div style={{
                                fontSize: '14px',
                                fontWeight: '700',
                                color: '#065F46',
                                marginBottom: '4px',
                            }}>
                                {selectedFile.name}
                            </div>
                            <div style={{
                                fontSize: '12px',
                                color: '#047857',
                                fontWeight: '600',
                            }}>
                                {formatFileSize(selectedFile.size)}
                            </div>
                        </div>
                        <button
                            onClick={handleClearFile}
                            style={{
                                width: '36px',
                                height: '36px',
                                borderRadius: '50%',
                                background: '#FEE2E2',
                                border: '1px solid #FCA5A5',
                                color: '#DC2626',
                                cursor: 'pointer',
                                fontSize: '18px',
                                fontWeight: 'bold',
                                fontFamily: 'inherit',
                                flexShrink: 0,
                            }}
                            title="حذف فایل"
                        >
                            ×
                        </button>
                    </div>
                )}

                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".xlsx"
                    style={{ display: 'none' }}
                    onChange={handleInputChange}
                />

                {/* دکمه آپلود */}
                {selectedFile && (
                    <button
                        onClick={handleUpload}
                        disabled={isUploading}
                        style={{
                            marginTop: '16px',
                            width: '100%',
                            padding: '16px',
                            background: isUploading
                                ? '#9CA3AF'
                                : 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '12px',
                            cursor: isUploading ? 'wait' : 'pointer',
                            fontWeight: '800',
                            fontSize: '16px',
                            fontFamily: 'inherit',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '10px',
                            boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)',
                        }}
                    >
                        {isUploading ? (
                            <>
                                <span style={{
                                    width: '20px',
                                    height: '20px',
                                    border: '3px solid white',
                                    borderTop: '3px solid transparent',
                                    borderRadius: '50%',
                                    animation: 'spin 0.8s linear infinite',
                                }}></span>
                                در حال پردازش...
                            </>
                        ) : (
                            <>🚀 شروع آپلود و پردازش</>
                        )}
                    </button>
                )}

                {/* خطای آپلود */}
                {uploadError && (
                    <div style={{
                        marginTop: '16px',
                        padding: '14px 18px',
                        background: '#FEE2E2',
                        border: '2px solid #FCA5A5',
                        borderRadius: '10px',
                        color: '#991B1B',
                        fontWeight: '700',
                        fontSize: '13px',
                    }}>
                        {uploadError}
                    </div>
                )}
            </div>

            {/* ============================================ */}
            {/* گام ۳: نتیجه */}
            {/* ============================================ */}
            {uploadResult && (
                <div style={{
                    background: 'white',
                    borderRadius: '16px',
                    padding: '24px',
                    marginBottom: '20px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                    border: uploadResult.is_success ? '2px solid #86EFAC' : '2px solid #FCD34D',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
                        <div style={{
                            width: '48px',
                            height: '48px',
                            borderRadius: '50%',
                            background: uploadResult.is_success
                                ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)'
                                : 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '24px',
                            fontWeight: 'bold',
                            flexShrink: 0,
                        }}>
                            {uploadResult.is_success ? '✓' : '!'}
                        </div>
                        <div>
                            <h2 style={{
                                margin: 0,
                                fontSize: '18px',
                                fontWeight: '800',
                                color: uploadResult.is_success ? '#065F46' : '#92400E',
                            }}>
                                {uploadResult.is_success ? '✅ آپلود با موفقیت انجام شد' : '⚠️ آپلود با خطا مواجه شد'}
                            </h2>
                            <p style={{
                                margin: '4px 0 0 0',
                                fontSize: '13px',
                                color: '#6B7280',
                            }}>
                                {uploadResult.message || 'نتیجه پردازش'}
                            </p>
                        </div>
                    </div>

                    {/* خلاصه */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                        gap: '12px',
                        marginBottom: '20px',
                    }}>
                        <ResultStat
                            label="ایجاد شده"
                            value={uploadResult.created_count || 0}
                            color="#10B981"
                            icon="✨"
                        />
                        <ResultStat
                            label="به‌روزرسانی"
                            value={uploadResult.updated_count || 0}
                            color="#3B82F6"
                            icon="🔄"
                        />
                        <ResultStat
                            label="خطاها"
                            value={uploadResult.error_count || 0}
                            color="#EF4444"
                            icon="❌"
                        />
                    </div>

                    {/* جزئیات بخش‌ها */}
                    {uploadResult.sections && Object.entries(uploadResult.sections).map(([key, data]) => {
                        if (!data || data.total === 0) return null;

                        const labels = {
                            staff: '👥 پرسنل',
                            wards: '🏥 بخش‌ها',
                            holidays: '📅 تعطیلات',
                            shift_codes: '🔧 کدهای شیفت',
                        };

                        return (
                            <div key={key} style={{
                                padding: '14px 16px',
                                background: '#F8FAFC',
                                borderRadius: '10px',
                                marginBottom: '10px',
                                borderRight: `4px solid ${data.errors?.length > 0 ? '#F59E0B' : '#10B981'}`,
                            }}>
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    flexWrap: 'wrap',
                                    gap: '8px',
                                }}>
                                    <div style={{
                                        fontSize: '14px',
                                        fontWeight: '800',
                                        color: '#0F172A',
                                    }}>
                                        {labels[key] || key}
                                    </div>
                                    <div style={{
                                        display: 'flex',
                                        gap: '12px',
                                        fontSize: '12px',
                                        fontWeight: '700',
                                    }}>
                                        <span style={{ color: '#10B981' }}>✨ {data.created || 0}</span>
                                        <span style={{ color: '#3B82F6' }}>🔄 {data.updated || 0}</span>
                                        {data.errors?.length > 0 && (
                                            <span style={{ color: '#EF4444' }}>❌ {data.errors.length}</span>
                                        )}
                                    </div>
                                </div>

                                {data.errors && data.errors.length > 0 && (
                                    <details style={{ marginTop: '10px' }}>
                                        <summary style={{
                                            cursor: 'pointer',
                                            color: '#991B1B',
                                            fontSize: '12px',
                                            fontWeight: '700',
                                        }}>
                                            نمایش {data.errors.length} خطا
                                        </summary>
                                        <ul style={{
                                            margin: '8px 0 0 0',
                                            padding: '0 20px 0 0',
                                            fontSize: '12px',
                                            color: '#7F1D1D',
                                            lineHeight: '1.8',
                                        }}>
                                            {data.errors.slice(0, 20).map((err, idx) => (
                                                <li key={idx}>
                                                    ردیف {err.row}: {err.message}
                                                </li>
                                            ))}
                                            {data.errors.length > 20 && (
                                                <li style={{ color: '#6B7280', fontStyle: 'italic' }}>
                                                    ... و {data.errors.length - 20} خطا دیگر
                                                </li>
                                            )}
                                        </ul>
                                    </details>
                                )}
                            </div>
                        );
                    })}

                    <button
                        onClick={() => {
                            setUploadResult(null);
                            handleClearFile();
                        }}
                        style={{
                            marginTop: '16px',
                            padding: '12px 24px',
                            background: '#F3F4F6',
                            color: '#374151',
                            border: '1px solid #D1D5DB',
                            borderRadius: '10px',
                            cursor: 'pointer',
                            fontWeight: '700',
                            fontSize: '14px',
                            fontFamily: 'inherit',
                        }}
                    >
                        📤 آپلود فایل دیگر
                    </button>
                </div>
            )}

            {/* ============================================ */}
            {/* تاریخچه آپلودها */}
            {/* ============================================ */}
            <div style={{
                background: 'white',
                borderRadius: '16px',
                padding: '24px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                border: '1px solid #E5E7EB',
            }}>
                <h2 style={{
                    margin: '0 0 16px 0',
                    fontSize: '16px',
                    fontWeight: '800',
                    color: '#0F172A',
                }}>
                    📜 تاریخچه آپلودها
                </h2>

                {loadingHistory ? (
                    <div style={{
                        padding: '30px',
                        textAlign: 'center',
                        color: '#6B7280',
                    }}>
                        ⏳ در حال بارگذاری...
                    </div>
                ) : uploadHistory.length === 0 ? (
                    <div style={{
                        padding: '30px',
                        textAlign: 'center',
                        color: '#9CA3AF',
                        fontSize: '13px',
                    }}>
                        📭 هیچ آپلودی ثبت نشده است
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {uploadHistory.map((item) => (
                            <div key={item.id} style={{
                                padding: '12px 16px',
                                background: '#F8FAFC',
                                borderRadius: '10px',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                flexWrap: 'wrap',
                                gap: '10px',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: '200px' }}>
                                    <span style={{ fontSize: '24px' }}>
                                        {item.status === 'success' ? '✅' :
                                         item.status === 'partial' ? '⚠️' :
                                         item.status === 'failed' ? '❌' : '⏳'}
                                    </span>
                                    <div>
                                        <div style={{
                                            fontSize: '13px',
                                            fontWeight: '700',
                                            color: '#0F172A',
                                            marginBottom: '2px',
                                        }}>
                                            {item.file_name}
                                        </div>
                                        <div style={{
                                            fontSize: '11px',
                                            color: '#6B7280',
                                        }}>
                                            {formatDate(item.created_at)}
                                            {item.uploaded_by_name && ` — ${item.uploaded_by_name}`}
                                        </div>
                                    </div>
                                </div>
                                <div style={{
                                    display: 'flex',
                                    gap: '12px',
                                    fontSize: '11px',
                                    fontWeight: '700',
                                }}>
                                    {item.created_count > 0 && (
                                        <span style={{ color: '#10B981' }}>✨ {item.created_count}</span>
                                    )}
                                    {item.updated_count > 0 && (
                                        <span style={{ color: '#3B82F6' }}>🔄 {item.updated_count}</span>
                                    )}
                                    {item.error_count > 0 && (
                                        <span style={{ color: '#EF4444' }}>❌ {item.error_count}</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {siteSettings?.footer_text && (
                <footer className="site-footer">
                    {siteSettings.footer_text}
                </footer>
            )}

            <style>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}

// ============================================================
// کامپوننت کمکی: کارت آماری
// ============================================================
function ResultStat({ label, value, color, icon }) {
    return (
        <div style={{
            padding: '14px',
            background: '#F9FAFB',
            borderRadius: '10px',
            border: `2px solid ${color}20`,
            textAlign: 'center',
        }}>
            <div style={{ fontSize: '24px', marginBottom: '4px' }}>{icon}</div>
            <div style={{
                fontSize: '22px',
                fontWeight: '800',
                color: color,
                marginBottom: '4px',
            }}>
                {value}
            </div>
            <div style={{
                fontSize: '11px',
                color: '#6B7280',
                fontWeight: '600',
            }}>
                {label}
            </div>
        </div>
    );
}

export default ExcelImportPage;