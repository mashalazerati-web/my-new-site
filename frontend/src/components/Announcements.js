// src/components/Announcements.js
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import api from '../services/api';
import '../styles/index.css';

function Announcements() {
    const [announcements, setAnnouncements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedAnnouncement, setSelectedAnnouncement] = useState(null);
    const [filterPriority, setFilterPriority] = useState('all');
    const [searchText, setSearchText] = useState('');

    // ============================================================
    // بارگذاری
    // ============================================================
    useEffect(() => {
        loadAnnouncements();
    }, []);

    const loadAnnouncements = async () => {
        setLoading(true);
        setError('');
        try {
            const res = await api.get('/api/announcements/');
            setAnnouncements(res.data);
        } catch (err) {
            console.error('خطا در دریافت اخبار:', err);
            setError('❌ خطا در دریافت اخبار و دستورالعمل‌ها');
        } finally {
            setLoading(false);
        }
    };

    // ============================================================
    // helpers
    // ============================================================
    const getPriorityConfig = (priority) => {
        return {
            normal: {
                label: '📢 عادی',
                bg: '#F3F4F6',
                color: '#374151',
                border: '#D1D5DB',
                icon: '📢',
            },
            important: {
                label: '⚠️ مهم',
                bg: '#FEF3C7',
                color: '#92400E',
                border: '#FCD34D',
                icon: '⚠️',
            },
            urgent: {
                label: '🚨 فوری',
                bg: '#FEE2E2',
                color: '#991B1B',
                border: '#FCA5A5',
                icon: '🚨',
            },
        }[priority] || {
            label: '📢 عادی',
            bg: '#F3F4F6',
            color: '#374151',
            border: '#D1D5DB',
            icon: '📢',
        };
    };

    const formatFileSize = (bytes) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    };

    const formatDate = (dateStr) => {
        try {
            return new Date(dateStr).toLocaleDateString('fa-IR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
            });
        } catch {
            return dateStr;
        }
    };

    const getFileIcon = (fileType) => {
        return {
            image: '🖼️',
            video: '🎬',
            pdf: '📄',
            file: '📎',
        }[fileType] || '📎';
    };

    const getFileTypeLabel = (fileType) => {
        return {
            image: 'تصویر',
            video: 'فیلم',
            pdf: 'PDF',
            file: 'فایل',
        }[fileType] || 'فایل';
    };

    // ============================================================
    // فیلتر
    // ============================================================
    const filteredAnnouncements = announcements.filter(item => {
        if (filterPriority !== 'all' && item.priority !== filterPriority) {
            return false;
        }
        if (searchText) {
            const query = searchText.toLowerCase();
            return (
                item.title?.toLowerCase().includes(query) ||
                item.content?.toLowerCase().includes(query)
            );
        }
        return true;
    });

    // ============================================================
    // Loading / Error / Empty
    // ============================================================
    if (loading) {
        return (
            <div style={{
                padding: '60px 20px',
                textAlign: 'center',
                color: '#6B7280',
            }}>
                <div style={{
                    width: '50px',
                    height: '50px',
                    border: '5px solid #E5E7EB',
                    borderTop: '5px solid #3B82F6',
                    borderRadius: '50%',
                    animation: 'spin 0.8s linear infinite',
                    margin: '0 auto 16px',
                }}></div>
                <div style={{ fontSize: '15px', fontWeight: '600' }}>
                    ⏳ در حال بارگذاری اخبار...
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

    if (error) {
        return (
            <div style={{
                padding: '40px 20px',
                textAlign: 'center',
                color: '#991B1B',
                background: '#FEE2E2',
                borderRadius: '12px',
                border: '2px solid #FCA5A5',
            }}>
                <div style={{ fontSize: '36px', marginBottom: '10px' }}>❌</div>
                <div style={{ fontWeight: '700', marginBottom: '12px' }}>{error}</div>
                <button
                    onClick={loadAnnouncements}
                    style={{
                        padding: '10px 20px',
                        background: '#991B1B',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontWeight: '700',
                        fontFamily: 'inherit',
                    }}
                >
                    🔄 تلاش مجدد
                </button>
            </div>
        );
    }

    // ============================================================
    // رندر اصلی
    // ============================================================
    return (
        <div className="announcements-container">
            {/* هدر */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '20px',
                flexWrap: 'wrap',
                gap: '12px',
            }}>
                <h2 style={{
                    margin: 0,
                    fontSize: '22px',
                    fontWeight: '800',
                    color: '#0F172A',
                }}>
                    📢 اخبار و دستورالعمل‌ها
                </h2>
                <button
                    onClick={loadAnnouncements}
                    disabled={loading}
                    style={{
                        padding: '8px 16px',
                        background: '#3B82F6',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontWeight: '700',
                        fontSize: '13px',
                        fontFamily: 'inherit',
                    }}
                >
                    🔄 بروزرسانی
                </button>
            </div>

            {/* فیلترها */}
            <div style={{
                display: 'flex',
                gap: '10px',
                marginBottom: '20px',
                flexWrap: 'wrap',
                padding: '12px',
                background: '#F8FAFC',
                borderRadius: '12px',
                border: '1px solid #E2E8F0',
            }}>
                <input
                    type="text"
                    placeholder="🔍 جستجو در اخبار..."
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    style={{
                        flex: 1,
                        minWidth: '200px',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid #D1D5DB',
                        fontSize: '14px',
                        fontFamily: 'inherit',
                    }}
                />
                <select
                    value={filterPriority}
                    onChange={(e) => setFilterPriority(e.target.value)}
                    style={{
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid #D1D5DB',
                        fontSize: '14px',
                        fontFamily: 'inherit',
                        cursor: 'pointer',
                    }}
                >
                    <option value="all">📋 همه</option>
                    <option value="urgent">🚨 فوری</option>
                    <option value="important">⚠️ مهم</option>
                    <option value="normal">📢 عادی</option>
                </select>
            </div>

            {/* لیست اخبار */}
            {filteredAnnouncements.length === 0 ? (
                <div style={{
                    padding: '60px 20px',
                    textAlign: 'center',
                    color: '#6B7280',
                    background: '#F9FAFB',
                    borderRadius: '12px',
                    border: '2px dashed #D1D5DB',
                }}>
                    <div style={{ fontSize: '48px', marginBottom: '12px' }}>📭</div>
                    <div style={{ fontSize: '15px', fontWeight: '600' }}>
                        {searchText || filterPriority !== 'all'
                            ? 'نتیجه‌ای برای فیلترهای انتخابی یافت نشد'
                            : 'هیچ خبر یا دستورالعملی منتشر نشده است'}
                    </div>
                </div>
            ) : (
                <div style={{
                    display: 'grid',
                    gap: '16px',
                }}>
                    {filteredAnnouncements.map((item) => {
                        const config = getPriorityConfig(item.priority);
                        const attachmentsCount = item.attachments?.length || 0;

                        return (
                            <div
                                key={item.id}
                                style={{
                                    background: 'white',
                                    borderRadius: '14px',
                                    padding: '20px',
                                    border: `2px solid ${config.border}`,
                                    borderRight: `6px solid ${config.color}`,
                                    boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                                    transition: 'transform 0.15s, box-shadow 0.15s',
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.transform = 'translateY(-2px)';
                                    e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.08)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'translateY(0)';
                                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.04)';
                                }}
                            >
                                {/* هدر کارت */}
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    marginBottom: '12px',
                                    flexWrap: 'wrap',
                                    gap: '8px',
                                }}>
                                    <span style={{
                                        padding: '4px 12px',
                                        borderRadius: '12px',
                                        background: config.bg,
                                        color: config.color,
                                        fontWeight: '700',
                                        fontSize: '12px',
                                    }}>
                                        {config.label}
                                    </span>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '12px',
                                        fontSize: '12px',
                                        color: '#6B7280',
                                        fontWeight: '600',
                                    }}>
                                        <span>📅 {formatDate(item.created_at)}</span>
                                        {item.created_by_name && (
                                            <span>👤 {item.created_by_name}</span>
                                        )}
                                    </div>
                                </div>

                                {/* عنوان */}
                                <h3 style={{
                                    margin: '0 0 10px 0',
                                    fontSize: '18px',
                                    fontWeight: '800',
                                    color: '#0F172A',
                                    lineHeight: '1.5',
                                }}>
                                    {item.title}
                                </h3>

                                {/* محتوا (خلاصه) */}
                                <div style={{
                                    fontSize: '14px',
                                    color: '#374151',
                                    lineHeight: '1.8',
                                    marginBottom: '16px',
                                    display: '-webkit-box',
                                    WebkitLineClamp: 3,
                                    WebkitBoxOrient: 'vertical',
                                    overflow: 'hidden',
                                }}>
                                    {item.content}
                                </div>

                                {/* نمایش پیش‌نمایش تصاویر */}
                                {attachmentsCount > 0 && (
                                    <div style={{
                                        display: 'flex',
                                        gap: '8px',
                                        marginBottom: '16px',
                                        flexWrap: 'wrap',
                                    }}>
                                        {item.attachments.slice(0, 4).map((att) => {
                                            if (att.file_type === 'image') {
                                                return (
                                                    <div
                                                        key={att.id}
                                                        style={{
                                                            width: '80px',
                                                            height: '80px',
                                                            borderRadius: '10px',
                                                            overflow: 'hidden',
                                                            border: '2px solid #E5E7EB',
                                                            background: '#F9FAFB',
                                                            cursor: 'pointer',
                                                        }}
                                                        onClick={() => setSelectedAnnouncement(item)}
                                                    >
                                                        <img
                                                            src={att.file_url}
                                                            alt={att.caption || 'تصویر'}
                                                            style={{
                                                                width: '100%',
                                                                height: '100%',
                                                                objectFit: 'cover',
                                                            }}
                                                            onError={(e) => {
                                                                e.target.style.display = 'none';
                                                                e.target.parentNode.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:32px;">🖼️</div>';
                                                            }}
                                                        />
                                                    </div>
                                                );
                                            }
                                            return null;
                                        })}

                                        {/* آیکون‌های سایر فایل‌ها */}
                                        {item.attachments
                                            .filter(att => att.file_type !== 'image')
                                            .slice(0, 3)
                                            .map((att) => (
                                                <div
                                                    key={att.id}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '6px',
                                                        padding: '8px 12px',
                                                        borderRadius: '10px',
                                                        background: '#F3F4F6',
                                                        border: '1px solid #E5E7EB',
                                                        fontSize: '12px',
                                                        fontWeight: '600',
                                                        color: '#374151',
                                                    }}
                                                >
                                                    <span style={{ fontSize: '18px' }}>
                                                        {getFileIcon(att.file_type)}
                                                    </span>
                                                    <span>{getFileTypeLabel(att.file_type)}</span>
                                                </div>
                                            ))}
                                    </div>
                                )}

                                {/* دکمه‌ها */}
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    paddingTop: '12px',
                                    borderTop: '1px solid #F3F4F6',
                                }}>
                                    <div style={{
                                        fontSize: '12px',
                                        color: '#6B7280',
                                        fontWeight: '600',
                                    }}>
                                        {attachmentsCount > 0 ? (
                                            <>📎 {attachmentsCount} ضمیمه</>
                                        ) : (
                                            <></>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => setSelectedAnnouncement(item)}
                                        style={{
                                            padding: '8px 18px',
                                            background: config.color,
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            fontWeight: '700',
                                            fontSize: '13px',
                                            fontFamily: 'inherit',
                                        }}
                                    >
                                        👁️ مشاهده کامل
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Modal جزئیات */}
            {selectedAnnouncement && createPortal(
                <AnnouncementModal
                    announcement={selectedAnnouncement}
                    onClose={() => setSelectedAnnouncement(null)}
                    formatDate={formatDate}
                    formatFileSize={formatFileSize}
                    getFileIcon={getFileIcon}
                    getFileTypeLabel={getFileTypeLabel}
                    getPriorityConfig={getPriorityConfig}
                />,
                document.body
            )}
        </div>
    );
}

// ============================================================
// ✅ Modal نمایش جزئیات کامل
// ============================================================
function AnnouncementModal({
    announcement,
    onClose,
    formatDate,
    formatFileSize,
    getFileIcon,
    getFileTypeLabel,
    getPriorityConfig,
}) {
    const config = getPriorityConfig(announcement.priority);
    const [currentImageIndex, setCurrentImageIndex] = useState(0);

    const images = (announcement.attachments || []).filter(
        (a) => a.file_type === 'image'
    );
    const videos = (announcement.attachments || []).filter(
        (a) => a.file_type === 'video'
    );
    const pdfs = (announcement.attachments || []).filter(
        (a) => a.file_type === 'pdf'
    );
    const files = (announcement.attachments || []).filter(
        (a) => a.file_type === 'file'
    );

    // بستن با Escape
    useEffect(() => {
        const handleKey = (e) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', handleKey);
        return () => document.removeEventListener('keydown', handleKey);
    }, [onClose]);

    return (
        <div
            onClick={onClose}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.6)',
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
                    maxWidth: '900px',
                    width: '100%',
                    maxHeight: '90vh',
                    overflow: 'auto',
                    position: 'relative',
                }}
            >
                {/* هدر Modal */}
                <div style={{
                    padding: '20px 24px',
                    background: config.bg,
                    borderBottom: `3px solid ${config.color}`,
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: '12px',
                }}>
                    <div style={{ flex: 1 }}>
                        <span style={{
                            display: 'inline-block',
                            padding: '3px 10px',
                            borderRadius: '10px',
                            background: 'white',
                            color: config.color,
                            fontWeight: '700',
                            fontSize: '11px',
                            marginBottom: '8px',
                            border: `1px solid ${config.color}`,
                        }}>
                            {config.label}
                        </span>
                        <h2 style={{
                            margin: 0,
                            fontSize: '20px',
                            fontWeight: '800',
                            color: '#0F172A',
                            lineHeight: '1.5',
                        }}>
                            {announcement.title}
                        </h2>
                        <div style={{
                            marginTop: '8px',
                            display: 'flex',
                            gap: '12px',
                            fontSize: '12px',
                            color: '#6B7280',
                            fontWeight: '600',
                            flexWrap: 'wrap',
                        }}>
                            <span>📅 {formatDate(announcement.created_at)}</span>
                            {announcement.created_by_name && (
                                <span>👤 {announcement.created_by_name}</span>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '50%',
                            background: 'white',
                            border: `2px solid ${config.color}`,
                            color: config.color,
                            cursor: 'pointer',
                            fontSize: '20px',
                            fontWeight: 'bold',
                            fontFamily: 'inherit',
                            flexShrink: 0,
                            lineHeight: 1,
                        }}
                        aria-label="بستن"
                    >
                        ×
                    </button>
                </div>

                {/* بدنه Modal */}
                <div style={{ padding: '24px' }}>
                    {/* متن کامل */}
                    <div style={{
                        fontSize: '15px',
                        color: '#374151',
                        lineHeight: '2',
                        marginBottom: '24px',
                        whiteSpace: 'pre-wrap',
                    }}>
                        {announcement.content}
                    </div>

                    {/* گالری تصاویر */}
                    {images.length > 0 && (
                        <div style={{ marginBottom: '24px' }}>
                            <h4 style={{
                                margin: '0 0 12px 0',
                                fontSize: '14px',
                                fontWeight: '700',
                                color: '#0F172A',
                            }}>
                                🖼️ تصاویر ({images.length})
                            </h4>
                            <div style={{
                                background: '#F9FAFB',
                                borderRadius: '12px',
                                padding: '12px',
                                textAlign: 'center',
                            }}>
                                <img
                                    src={images[currentImageIndex].file_url}
                                    alt={images[currentImageIndex].caption || 'تصویر'}
                                    style={{
                                        maxWidth: '100%',
                                        maxHeight: '500px',
                                        borderRadius: '8px',
                                        objectFit: 'contain',
                                    }}
                                />
                                {images[currentImageIndex].caption && (
                                    <div style={{
                                        marginTop: '8px',
                                        fontSize: '13px',
                                        color: '#6B7280',
                                        fontWeight: '600',
                                    }}>
                                        {images[currentImageIndex].caption}
                                    </div>
                                )}
                                {images.length > 1 && (
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'center',
                                        alignItems: 'center',
                                        gap: '12px',
                                        marginTop: '12px',
                                    }}>
                                        <button
                                            onClick={() => setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length)}
                                            style={{
                                                padding: '6px 14px',
                                                background: 'white',
                                                border: '1px solid #D1D5DB',
                                                borderRadius: '8px',
                                                cursor: 'pointer',
                                                fontWeight: 'bold',
                                                fontFamily: 'inherit',
                                            }}
                                        >
                                            ▶
                                        </button>
                                        <span style={{ fontWeight: '700', fontSize: '13px' }}>
                                            {currentImageIndex + 1} / {images.length}
                                        </span>
                                        <button
                                            onClick={() => setCurrentImageIndex((prev) => (prev + 1) % images.length)}
                                            style={{
                                                padding: '6px 14px',
                                                background: 'white',
                                                border: '1px solid #D1D5DB',
                                                borderRadius: '8px',
                                                cursor: 'pointer',
                                                fontWeight: 'bold',
                                                fontFamily: 'inherit',
                                            }}
                                        >
                                            ◀
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* فیلم‌ها */}
                    {videos.length > 0 && (
                        <div style={{ marginBottom: '24px' }}>
                            <h4 style={{
                                margin: '0 0 12px 0',
                                fontSize: '14px',
                                fontWeight: '700',
                                color: '#0F172A',
                            }}>
                                🎬 فیلم‌ها ({videos.length})
                            </h4>
                            {videos.map((video) => (
                                <div key={video.id} style={{ marginBottom: '16px' }}>
                                    <video
                                        controls
                                        style={{
                                            width: '100%',
                                            maxHeight: '500px',
                                            borderRadius: '12px',
                                            background: '#000',
                                        }}
                                    >
                                        <source src={video.file_url} />
                                        مرورگر شما از پخش فیلم پشتیبانی نمی‌کند.
                                    </video>
                                    {video.caption && (
                                        <div style={{
                                            marginTop: '8px',
                                            fontSize: '13px',
                                            color: '#6B7280',
                                            fontWeight: '600',
                                            textAlign: 'center',
                                        }}>
                                            {video.caption}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* PDF ها */}
                    {pdfs.length > 0 && (
                        <div style={{ marginBottom: '24px' }}>
                            <h4 style={{
                                margin: '0 0 12px 0',
                                fontSize: '14px',
                                fontWeight: '700',
                                color: '#0F172A',
                            }}>
                                📄 فایل‌های PDF ({pdfs.length})
                            </h4>
                            <div style={{ display: 'grid', gap: '8px' }}>
                                {pdfs.map((pdf) => (
                                    <a
                                        key={pdf.id}
                                        href={pdf.file_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            padding: '12px 16px',
                                            background: '#FEF2F2',
                                            borderRadius: '10px',
                                            border: '1px solid #FECACA',
                                            textDecoration: 'none',
                                            color: '#991B1B',
                                            fontWeight: '600',
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                            <span style={{ fontSize: '22px' }}>📄</span>
                                            <div>
                                                <div style={{ fontSize: '13px', fontWeight: '700' }}>
                                                    {pdf.caption || pdf.file_name}
                                                </div>
                                                <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '2px' }}>
                                                    {formatFileSize(pdf.file_size)}
                                                </div>
                                            </div>
                                        </div>
                                        <span style={{ fontSize: '20px' }}>⬇️</span>
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* فایل‌های دیگر */}
                    {files.length > 0 && (
                        <div>
                            <h4 style={{
                                margin: '0 0 12px 0',
                                fontSize: '14px',
                                fontWeight: '700',
                                color: '#0F172A',
                            }}>
                                📎 سایر فایل‌ها ({files.length})
                            </h4>
                            <div style={{ display: 'grid', gap: '8px' }}>
                                {files.map((file) => (
                                    <a
                                        key={file.id}
                                        href={file.file_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        download
                                        style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            padding: '12px 16px',
                                            background: '#F3F4F6',
                                            borderRadius: '10px',
                                            border: '1px solid #E5E7EB',
                                            textDecoration: 'none',
                                            color: '#374151',
                                            fontWeight: '600',
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                            <span style={{ fontSize: '22px' }}>{getFileIcon(file.file_type)}</span>
                                            <div>
                                                <div style={{ fontSize: '13px', fontWeight: '700' }}>
                                                    {file.caption || file.file_name}
                                                </div>
                                                <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '2px' }}>
                                                    {formatFileSize(file.file_size)}
                                                </div>
                                            </div>
                                        </div>
                                        <span style={{ fontSize: '20px' }}>⬇️</span>
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* پیام اگر ضمیمه‌ای نیست */}
                    {(!announcement.attachments || announcement.attachments.length === 0) && (
                        <div style={{
                            padding: '20px',
                            textAlign: 'center',
                            color: '#9CA3AF',
                            fontSize: '13px',
                            background: '#F9FAFB',
                            borderRadius: '10px',
                            border: '1px dashed #D1D5DB',
                        }}>
                            📭 این خبر ضمیمه‌ای ندارد
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default Announcements;