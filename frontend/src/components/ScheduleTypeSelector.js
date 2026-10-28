// src/components/ScheduleTypeSelector.js
import React from 'react';
import { SCHEDULE_TYPES } from '../constants/persianCalendar';

/**
 * سلکتور نوع برنامه (اصلی/آنکالی/بحران)
 * 
 * @param {string} value - مقدار فعلی ('main' | 'oncall' | 'crisis')
 * @param {function} onChange - تابع تغییر
 * @param {boolean} disabled - غیرفعال
 * @param {boolean} showLabel - نمایش برچسب
 * @param {object} statuses - وضعیت‌های هر برنامه برای نمایش در آپشن
 */
function ScheduleTypeSelector({
    value = 'main',
    onChange,
    disabled = false,
    showLabel = true,
    statuses = null,
    className = ''
}) {
    return (
        <div className={`schedule-type-selector ${className}`}>
            {showLabel && (
                <label className="schedule-type-label">📋 نوع برنامه:</label>
            )}
            <select
                value={value}
                onChange={(e) => onChange(e.target.value)}
                disabled={disabled}
                className="schedule-type-select"
            >
                {SCHEDULE_TYPES.map(type => {
                    const statusInfo = statuses?.[type.value];
                    let suffix = '';
                    
                    if (statusInfo && !statusInfo.can_generate && statusInfo.generation_error) {
                        suffix = ' 🔒';
                    } else if (statusInfo && statusInfo.has_schedule) {
                        suffix = ' ✅';
                    }
                    
                    return (
                        <option key={type.value} value={type.value}>
                            {type.label}{suffix}
                        </option>
                    );
                })}
            </select>
        </div>
    );
}

export default ScheduleTypeSelector;