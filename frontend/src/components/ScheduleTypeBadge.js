// src/components/ScheduleTypeBadge.js
import React from 'react';

/**
 * بج نمایش نوع برنامه
 */
function ScheduleTypeBadge({ scheduleType = 'main', size = 'md' }) {
    const config = {
        main: {
            label: '🤖 اصلی',
            bg: '#DBEAFE',
            color: '#1E40AF',
            border: '#93C5FD',
        },
        oncall: {
            label: '📞 آنکالی',
            bg: '#FEF3C7',
            color: '#92400E',
            border: '#FCD34D',
        },
        crisis: {
            label: '🚨 بحران',
            bg: '#FEE2E2',
            color: '#991B1B',
            border: '#FCA5A5',
        },
    };

    const c = config[scheduleType] || config.main;
    const sizeStyles = {
        sm: { padding: '2px 8px', fontSize: '11px' },
        md: { padding: '4px 12px', fontSize: '12px' },
        lg: { padding: '6px 16px', fontSize: '14px' },
    };

    return (
        <span
            className="schedule-type-badge"
            style={{
                backgroundColor: c.bg,
                color: c.color,
                border: `1px solid ${c.border}`,
                borderRadius: '12px',
                fontWeight: 'bold',
                display: 'inline-block',
                whiteSpace: 'nowrap',
                ...sizeStyles[size],
            }}
        >
            {c.label}
        </span>
    );
}

export default ScheduleTypeBadge;