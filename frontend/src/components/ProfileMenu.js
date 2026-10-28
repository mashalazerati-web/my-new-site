// src/components/ProfileMenu.js
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { createPortal } from 'react-dom';
import api from '../services/api';
import { getMediaUrl } from '../config';

function ProfileMenu({ user, onUserUpdate }) {
    const navigate = useNavigate();
    const [isOpen, setIsOpen] = useState(false);
    const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0 });
    const [showProfileModal, setShowProfileModal] = useState(false);
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const menuRef = useRef(null);
    const triggerRef = useRef(null);

    // ✅ محاسبه موقعیت dropdown
    const updateDropdownPosition = () => {
        if (triggerRef.current) {
            const rect = triggerRef.current.getBoundingClientRect();
            setDropdownPos({
                top: rect.bottom + 8,                // ۸ پیکسل فاصله
                left: rect.right - 280,              // عرض منو ۲۸۰
            });
        }
    };

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (
                menuRef.current && !menuRef.current.contains(e.target) &&
                triggerRef.current && !triggerRef.current.contains(e.target)
            ) {
                setIsOpen(false);
            }
        };

        const handleScrollOrResize = () => {
            if (isOpen) updateDropdownPosition();
        };

        document.addEventListener('mousedown', handleClickOutside);
        window.addEventListener('scroll', handleScrollOrResize, true);
        window.addEventListener('resize', handleScrollOrResize);

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            window.removeEventListener('scroll', handleScrollOrResize, true);
            window.removeEventListener('resize', handleScrollOrResize);
        };
    }, [isOpen]);

    const handleToggle = () => {
        if (!isOpen) updateDropdownPosition();
        setIsOpen(!isOpen);
    };

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        navigate('/login');
    };

    return (
        <div className="profile-menu-wrapper">
            <button
                ref={triggerRef}
                className="profile-menu-trigger"
                onClick={handleToggle}
            >
                <div className="profile-avatar-small">
                    {user?.avatar_url ? (
                        <img
                            src={getMediaUrl(user.avatar_url)}
                            alt="Profile"
                            onError={(e) => { e.target.style.display = 'none'; }}
                        />
                    ) : (
                        <span>👤</span>
                    )}
                </div>
                <span className="profile-menu-name">
                    {`${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.username || 'کاربر'}
                </span>
                <span className="profile-menu-arrow">▼</span>
            </button>

            {/* ✅ dropdown با Portal رندر می‌شود */}
            {isOpen && createPortal(
                <div
                    ref={menuRef}
                    className="profile-menu-dropdown"
                    style={{
                        position: 'fixed',
                        top: dropdownPos.top,
                        left: dropdownPos.left,
                        zIndex: 99999,
                    }}
                >
                    <button
                        onClick={() => {
                            setShowProfileModal(true);
                            setIsOpen(false);
                        }}
                    >
                        👤 پروفایل من
                    </button>
                    <button
                        onClick={() => {
                            setShowPasswordModal(true);
                            setIsOpen(false);
                        }}
                    >
                        🔒 تغییر رمز عبور
                    </button>
                    <hr />
                    <button
                        onClick={handleLogout}
                        className="logout-item"
                    >
                        🚪 خروج
                    </button>
                </div>,
                document.body
            )}

            {showProfileModal && (
                <ProfileModal
                    user={user}
                    onClose={() => setShowProfileModal(false)}
                    onUserUpdate={onUserUpdate}
                />
            )}

            {showPasswordModal && (
                <ChangePasswordModal
                    onClose={() => setShowPasswordModal(false)}
                />
            )}
        </div>
    );
}

// ✅ Modal نمایش پروفایل + آپلود عکس
function ProfileModal({ user, onClose, onUserUpdate }) {
    const [profile, setProfile] = useState(user);
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);

    const handleUploadAvatar = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (file.size > 2 * 1024 * 1024) {
            alert('❌ حجم عکس نباید بیشتر از ۲ مگابایت باشد.');
            return;
        }

        if (!file.type.startsWith('image/')) {
            alert('❌ فقط فایل تصویری مجاز است.');
            return;
        }

        setUploading(true);
        const formData = new FormData();
        formData.append('avatar', file);

        try {
            const res = await api.post('/api/upload-avatar/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const updatedProfile = {
                ...profile,
                avatar_url: res.data.avatar_url
            };
            setProfile(updatedProfile);
            if (onUserUpdate) onUserUpdate(updatedProfile);

            alert('✅ عکس پروفایل با موفقیت آپلود شد.');
        } catch (err) {
            console.error('خطا در آپلود:', err);
            alert('❌ ' + (err.response?.data?.error || 'خطا در آپلود عکس'));
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-card profile-modal" onClick={(e) => e.stopPropagation()}>
                <h2>👤 پروفایل من</h2>

                <div className="profile-avatar-section">
                    <div className="profile-avatar-large">
                        {profile?.avatar_url ? (
                            <img src={getMediaUrl(profile.avatar_url)} alt="Profile" />
                        ) : (
                            <span className="avatar-placeholder">👤</span>
                        )}
                    </div>
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        style={{ display: 'none' }}
                        onChange={handleUploadAvatar}
                    />
                    <button
                        className="btn btn-primary"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                    >
                        {uploading ? '⏳ در حال آپلود...' : '📷 تغییر عکس پروفایل'}
                    </button>
                    <p className="hint-text">
                        ابعاد پیشنهادی: ۳۰۰×۳۰۰ پیکسل | حداکثر: ۲ مگابایت
                    </p>
                </div>

                <div className="profile-info-section">
                    <div className="info-row">
                        <span className="info-label">نام و نام خانوادگی:</span>
                        <span className="info-value">
                            {profile?.first_name} {profile?.last_name}
                        </span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">نام کاربری:</span>
                        <span className="info-value">{profile?.username}</span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">ایمیل:</span>
                        <span className="info-value">{profile?.email || '—'}</span>
                    </div>
                </div>

                <div className="modal-actions">
                    <button className="btn btn-secondary" onClick={onClose}>
                        بستن
                    </button>
                </div>
            </div>
        </div>
    );
}

// ✅ Modal تغییر رمز عبور
function ChangePasswordModal({ onClose }) {
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (newPassword !== confirmPassword) {
            setError('رمز جدید و تکرار آن یکسان نیستند.');
            return;
        }

        if (newPassword.length < 8) {
            setError('رمز عبور باید حداقل ۸ کاراکتر باشد.');
            return;
        }

        setLoading(true);

        try {
            await api.post('/api/change-password/', {
                old_password: oldPassword,
                new_password: newPassword,
                confirm_password: confirmPassword,
            });

            alert('✅ رمز عبور با موفقیت تغییر کرد.');
            onClose();
        } catch (err) {
            console.error('خطا:', err);
            setError(err.response?.data?.error || 'خطا در تغییر رمز عبور');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-card" onClick={(e) => e.stopPropagation()}>
                <h2>🔒 تغییر رمز عبور</h2>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>رمز عبور فعلی:</label>
                        <input
                            type="password"
                            value={oldPassword}
                            onChange={(e) => setOldPassword(e.target.value)}
                            required
                            disabled={loading}
                        />
                    </div>

                    <div className="form-group">
                        <label>رمز عبور جدید:</label>
                        <input
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            required
                            minLength={8}
                            disabled={loading}
                        />
                        <small>حداقل ۸ کاراکتر</small>
                    </div>

                    <div className="form-group">
                        <label>تکرار رمز عبور جدید:</label>
                        <input
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                            disabled={loading}
                        />
                    </div>

                    {error && (
                        <div className="form-error">❌ {error}</div>
                    )}

                    <div className="modal-actions">
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading}
                        >
                            {loading ? '⏳ در حال ذخیره...' : '✅ تغییر رمز'}
                        </button>
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={onClose}
                            disabled={loading}
                        >
                            انصراف
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default ProfileMenu;