// src/components/HistoryWardList.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { format } from 'date-fns-jalali';
import { MONTH_NAMES } from '../constants/persianCalendar';

function HistoryWardList({ role }) {
    const navigate = useNavigate();
    const [wards, setWards] = useState([]);
    const [loading, setLoading] = useState(false);
    const [year, setYear] = useState(null);
    const [month, setMonth] = useState(null);
    const [selectedWardId, setSelectedWardId] = useState(null);

    useEffect(() => {
        const today = new Date();
        // ✅ سال و ماه شمسی
        const currentYear = parseInt(format(today, 'yyyy'));
        const currentMonth = parseInt(format(today, 'M')) + 1;
        setYear(currentYear);
        setMonth(currentMonth);
    }, []);

    useEffect(() => {
        if (year && month) {
            loadWards();
        }
    }, [year, month]);

    const loadWards = async () => {
        if (!year || !month) return;
        setLoading(true);
        try {
            let apiUrl = '';
            if (role === 'head') {
                apiUrl = `/api/head-schedule/?year=${year}&month=${month}&show_locked_only=true`;
            } else if (role === 'supervisor') {
                apiUrl = `/api/supervisor-dashboard/?year=${year}&month=${month}`;
            } else if (role === 'admin') {
                apiUrl = `/api/matron-dashboard/?year=${year}&month=${month}`;
            }

            const res = await api.get(apiUrl);
            let wardList = [];
            if (res.data.mode === 'list') {
                wardList = res.data.wards || [];
            } else if (Array.isArray(res.data)) {
                wardList = res.data;
            }

            setWards(wardList);
            if (wardList.length > 0) {
                setSelectedWardId(wardList[0].id);
            } else {
                setSelectedWardId(null);
            }
        } catch (error) {
            console.error('خطا در دریافت لیست بخش‌ها:', error);
            setWards([]);
            setSelectedWardId(null);
        } finally {
            setLoading(false);
        }
    };

    const handleHistorySearch = () => {
        if (year && month && selectedWardId) {
            if (role === 'head') {
                navigate(`/head-schedule?ward_id=${selectedWardId}&year=${year}&month=${month}`);
            } else if (role === 'supervisor') {
                navigate(`/supervisor-schedule?ward_id=${selectedWardId}&year=${year}&month=${month}`);
            } else if (role === 'admin') {
                navigate(`/matron-schedule?ward_id=${selectedWardId}&year=${year}&month=${month}`);
            }
        } else {
            alert('لطفاً سال، ماه و بخش مورد نظر را انتخاب کنید.');
        }
    };

    const generateYearOptions = () => {
        const years = [];
        for (let y = 1405; y <= 1415; y++) {
            years.push(y);
        }
        return years;
    };

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px', flexWrap: 'wrap', borderBottom: '2px solid #3498db', paddingBottom: '15px' }}>
            <h3 style={{ margin: '0 20px 0 0', color: '#2c3e50', fontSize: '18px' }}>مشاهده برنامه‌های ماهانه بخش‌ها</h3>

            <select
                value={year || ''}
                onChange={(e) => setYear(parseInt(e.target.value))}
                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '14px' }}
            >
                {generateYearOptions().map(y => (
                    <option key={y} value={y}>{y}</option>
                ))}
            </select>

            <select
                value={month || ''}
                onChange={(e) => setMonth(parseInt(e.target.value))}
                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '14px' }}
            >
                {MONTH_NAMES.slice(1).map((m, idx) => (
                    <option key={idx + 1} value={idx + 1}>{m}</option>
                ))}
            </select>

            <select
                value={selectedWardId || ''}
                onChange={(e) => setSelectedWardId(parseInt(e.target.value))}
                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '14px' }}
                disabled={wards.length === 0 || loading}
            >
                <option value="">انتخاب بخش...</option>
                {wards.map(ward => (
                    <option key={ward.id} value={ward.id}>{ward.name}</option>
                ))}
            </select>

            <button
                onClick={handleHistorySearch}
                style={{ padding: '6px 16px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' }}
                disabled={wards.length === 0 || loading}
            >
                {loading ? '⏳' : '🔍 نمایش برنامه‌ها'}
            </button>
        </div>
    );
}

export default HistoryWardList;