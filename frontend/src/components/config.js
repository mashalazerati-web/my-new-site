// src/config.js

// ✅ آدرس پایه API — از متغیر محیطی خوانده می‌شود یا به 127.0.0.1:8000 برمی‌گردد
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// ✅ آدرس پایه Media (تصاویر، لوگوها، امضاها)
export const MEDIA_BASE_URL = process.env.REACT_APP_MEDIA_URL || `${API_BASE_URL}/media`;

/**
 * تبدیل مسیر نسبی media به URL کامل
 * @param {string|null|undefined} path - مسیر نسبی مثل '/media/logos/logo.png' یا URL کامل
 * @returns {string|null} - URL کامل یا null
 */
export function getMediaUrl(path) {
    if (!path) return null;

    // اگر URL کامل است (http/https)، همان را برگردان
    if (path.startsWith('http://') || path.startsWith('https://')) {
        return path;
    }

    // اگر path با /media شروع می‌شود، آن را حذف کن تا دوباره اضافه نشود
    const cleanPath = path.startsWith('/media/') ? path.substring(6) : path;

    // اگر path با / شروع نمی‌شود، اضافه کن
    const normalizedPath = cleanPath.startsWith('/') ? cleanPath : `/${cleanPath}`;

    // اگر مسیر قبلاً شامل /media است، دوباره اضافه نکن
    if (normalizedPath.startsWith('/media/')) {
        return `${API_BASE_URL}${normalizedPath}`;
    }

    return `${API_BASE_URL}/media${normalizedPath}`;
}