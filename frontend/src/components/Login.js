// src/components/Login.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { getMediaUrl } from '../config';
import '../styles/index.css';

function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [siteSettings, setSiteSettings] = useState(null);
    const [loading, setLoading] = useState(false);

    // ✅ استیت‌های کپچا
    const [captcha, setCaptcha] = useState({ num1: 0, num2: 0, operator: '+', answer: 0 });
    const [userAnswer, setUserAnswer] = useState('');
    const [captchaError, setCaptchaError] = useState('');

    const navigate = useNavigate();

    // ✅ تولید کپچای جدید
    const generateCaptcha = () => {
        const num1 = Math.floor(Math.random() * 20) + 1;   // 1 تا 20
        const num2 = Math.floor(Math.random() * 20) + 1;   // 1 تا 20
        const operator = Math.random() > 0.5 ? '+' : '-';

        let answer;
        let a = num1, b = num2;

        if (operator === '+') {
            answer = a + b;
        } else {
            // برای تفریق، همیشه عدد بزرگ‌تر منهای کوچک‌تر (تا نتیجه منفی نشه)
            if (a < b) {
                [a, b] = [b, a];
            }
            answer = a - b;
        }

        setCaptcha({ num1: a, num2: b, operator, answer });
        setUserAnswer('');
        setCaptchaError('');
    };

    useEffect(() => {
        loadSiteSettings();
        generateCaptcha();   // ✅ تولید اولیه کپچا
    }, []);

    const loadSiteSettings = async () => {
        try {
            const res = await api.get('/api/site-settings/');
            setSiteSettings(res.data);
        } catch (err) {
            console.error('❌ خطا در دریافت تنظیمات سایت:', err);
        }
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        setCaptchaError('');

        // ✅ چک کپچا
        const parsedAnswer = parseInt(userAnswer, 10);
        if (isNaN(parsedAnswer) || parsedAnswer !== captcha.answer) {
            setCaptchaError('❌ پاسخ سؤال امنیتی اشتباه است. لطفاً دوباره تلاش کنید.');
            generateCaptcha();   // تولید کپچای جدید
            return;
        }

        setLoading(true);

        try {
            const response = await api.post('api/token/', { username, password });

            localStorage.setItem('access_token', response.data.access);
            localStorage.setItem('refresh_token', response.data.refresh);

            const profileRes = await api.get('api/profiles/');
            const profile = profileRes.data.find(p => p.user?.username === username);

            if (profile?.role === 'admin') {
                navigate('/matron-schedule');
            } else if (profile?.role === 'supervisor') {
                navigate('/supervisor-schedule');
            } else if (profile?.role === 'head') {
                navigate('/head-schedule');
            } else {
                navigate('/dashboard');
            }

        } catch (err) {
            console.error('❌ خطا در ورود:', err);
            if (err.response && err.response.status === 401) {
                setError('❌ نام کاربری یا رمز عبور اشتباه است.');
            } else {
                setError('❌ خطا در ارتباط با سرور. لطفاً مجدداً تلاش کنید.');
            }
            generateCaptcha();   // ✅ در صورت خطا هم کپچا رو عوض کن
        } finally {
            setLoading(false);
        }
    };

    const backgroundImage = getMediaUrl(siteSettings?.login_background);
    const logoUrl = getMediaUrl(siteSettings?.hospital_logo);

    return (
        <div
            className="login-page"
            style={backgroundImage ? { backgroundImage: `url(${backgroundImage})` } : {}}
        >
            <div className="login-overlay"></div>

            <div className="login-card">
                <div className="login-logo">
                    {logoUrl ? (
                        <img
                            src={logoUrl}
                            alt="لوگو"
                            onError={(e) => {
                                e.target.style.display = 'none';
                            }}
                        />
                    ) : (
                        <div className="login-logo-placeholder">🏥</div>
                    )}
                </div>

                <h1 className="login-main-title">مدیریت شیفت‌های پرستاری</h1>

                <p className="login-subtitle">
                    {siteSettings?.hospital_name || 'سیستم مدیریت بیمارستان'}
                </p>
                {siteSettings?.university_name && (
                    <p className="login-university">
                        {siteSettings.university_name}
                    </p>
                )}

                {error && <div className="login-error">{error}</div>}

                <form onSubmit={handleLogin} className="login-form">
                    <div className="login-form-group">
                        <label>👤 نام کاربری</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="کد ملی یا نام کاربری"
                            required
                            disabled={loading}
                        />
                    </div>
                    <div className="login-form-group">
                        <label>🔒 رمز عبور</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="رمز عبور خود را وارد کنید"
                            required
                            disabled={loading}
                        />
                    </div>

                    {/* ✅ کپچای ریاضی */}
                    <div className="login-form-group">
                        <label>🔐 سؤال امنیتی</label>
                        <div className="captcha-container">
                            <div className="captcha-question">
                                <span className="captcha-num">{captcha.num1}</span>
                                <span className="captcha-op">{captcha.operator}</span>
                                <span className="captcha-num">{captcha.num2}</span>
                                <span className="captcha-eq">=</span>
                                <span className="captcha-q">؟</span>
                            </div>
                            <input
                                type="number"
                                value={userAnswer}
                                onChange={(e) => setUserAnswer(e.target.value)}
                                placeholder="پاسخ"
                                required
                                disabled={loading}
                                className="captcha-input"
                                autoComplete="off"
                            />
                            <button
                                type="button"
                                onClick={generateCaptcha}
                                className="captcha-refresh"
                                disabled={loading}
                                title="سؤال جدید"
                            >
                                🔄
                            </button>
                        </div>
                        {captchaError && (
                            <div className="captcha-error">{captchaError}</div>
                        )}
                    </div>

                    <button
                        type="submit"
                        className="login-button"
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <span className="spinner"></span>
                                در حال ورود...
                            </>
                        ) : (
                            <>🚀 ورود به سیستم</>
                        )}
                    </button>
                </form>

                <div className="login-card-footer">
                    نسخه ۱.۰ - تمامی حقوق محفوظ است
                </div>
            </div>

            {siteSettings?.footer_text && (
                <div className="login-footer">
                    {siteSettings.footer_text}
                </div>
            )}
        </div>
    );
}

export default Login;