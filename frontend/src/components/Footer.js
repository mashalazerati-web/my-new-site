// src/components/Footer.js
import React, { useState, useEffect } from 'react';
import api from '../services/api';

function Footer() {
    const [footerText, setFooterText] = useState('');

    useEffect(() => {
        const loadFooter = async () => {
            try {
                const res = await api.get('/api/site-settings/');
                if (res.data.footer_text) {
                    setFooterText(res.data.footer_text);
                }
            } catch (err) {
                console.error('خطا در دریافت پاورقی:', err);
            }
        };
        loadFooter();
    }, []);

    if (!footerText) return null;

    return (
        <footer className="site-footer">
            {footerText}
        </footer>
    );
}

export default Footer;