// src/components/ScheduleActions.js
import React from 'react';
import '../styles/index.css';

function ScheduleActions({ scheduleStatus, userRole, scheduleType = 'main', onAction }) {
    const handleAction = async (action) => {
        const confirmMessages = {
            approve: 'آیا از تایید این برنامه اطمینان دارید؟',
            reject: 'آیا از بازگردانی این برنامه اطمینان دارید؟',
            reset: 'آیا از بازگرداندن برنامه به حالت اولیه اطمینان دارید؟',
            save_draft: 'آیا از ذخیره موقت این برنامه به عنوان پیش‌نویس اطمینان دارید؟'
        };

        if (action === 'reject' || action === 'reset') {
            const reason = window.prompt('لطفاً دلیل را وارد کنید:');
            if (reason === null) return;
            if (!reason.trim()) {
                alert('دلیل الزامی است.');
                return;
            }
            await onAction(action, reason);
        } else if (action === 'save_draft') {
            if (window.confirm(confirmMessages[action])) {
                await onAction(action);
            }
        } else {
            if (window.confirm(confirmMessages[action])) {
                await onAction(action);
            }
        }
    };

    const getStatusInfo = () => {
        const statusMap = {
            'DRAFT': {
                text: '⏳ در انتظار تنظیم و تایید سرپرستار',
                className: 'status-badge status-draft'
            },
            'PENDING_SUPERVISOR': {
                text: '⏳ در انتظار تایید سوپروایزر',
                className: 'status-badge status-pending-supervisor'
            },
            'PENDING_MATRON': {
                text: '⏳ در انتظار تایید نهایی مترون',
                className: 'status-badge status-pending-matron'
            },
            'LOCKED': {
                text: '🔒 قفل شده (تایید نهایی)',
                className: 'status-badge status-locked'
            },
            'RETURNED_TO_HEAD': {
                text: '🔄 بازگردانده شده به سرپرستار',
                className: 'status-badge status-returned'
            },
            'RETURNED_TO_SUPERVISOR': {
                text: '🔄 بازگردانده شده به سوپروایزر',
                className: 'status-badge status-returned'
            },
        };
        return statusMap[scheduleStatus] || {
            text: '⏳ وضعیت نامشخص',
            className: 'status-badge status-default'
        };
    };

    const statusInfo = getStatusInfo();

    // ✅ برچسب نوع برنامه برای دکمه‌ها
    const typeLabel = {
        main: 'اصلی',
        oncall: 'آنکالی',
        crisis: 'بحران',
    }[scheduleType] || '';

    return (
        <div className="schedule-actions-container">
            {/* ✅ نمایش وضعیت */}
            <div className={statusInfo.className}>
                {statusInfo.text}
            </div>

            {/* ✅ دکمه‌های عملیات */}
            <div className="schedule-actions-buttons">

                {/* ✅ سرپرستار در DRAFT */}
                {scheduleStatus === 'DRAFT' && userRole === 'head' && (
                    <>
                        <button
                            onClick={() => handleAction('save_draft')}
                            className="action-btn action-btn-save-draft"
                        >
                            <span className="action-btn-icon">💾</span>
                            <span>ذخیره موقت ({typeLabel})</span>
                        </button>
                        <button
                            onClick={() => handleAction('approve')}
                            className="action-btn action-btn-approve"
                        >
                            <span className="action-btn-icon">✅</span>
                            <span>تایید {typeLabel} و ارسال به سوپروایزر</span>
                        </button>
                    </>
                )}

                {/* ✅ سوپروایزر در PENDING_SUPERVISOR */}
                {scheduleStatus === 'PENDING_SUPERVISOR' && userRole === 'supervisor' && (
                    <>
                        <button
                            onClick={() => handleAction('approve')}
                            className="action-btn action-btn-approve"
                        >
                            <span className="action-btn-icon">✅</span>
                            <span>تایید {typeLabel} و ارسال به مترون</span>
                        </button>
                        <button
                            onClick={() => handleAction('reject')}
                            className="action-btn action-btn-reject"
                        >
                            <span className="action-btn-icon">🔄</span>
                            <span>بازگردانی {typeLabel} به سرپرستار</span>
                        </button>
                    </>
                )}

                {/* ✅ مترون در PENDING_MATRON */}
                {scheduleStatus === 'PENDING_MATRON' && userRole === 'admin' && (
                    <>
                        <button
                            onClick={() => handleAction('approve')}
                            className="action-btn action-btn-approve"
                        >
                            <span className="action-btn-icon">🔒</span>
                            <span>تایید نهایی و قفل {typeLabel}</span>
                        </button>
                        <button
                            onClick={() => handleAction('reject')}
                            className="action-btn action-btn-reject"
                        >
                            <span className="action-btn-icon">🔄</span>
                            <span>بازگردانی {typeLabel} به سوپروایزر</span>
                        </button>
                    </>
                )}

                {/* ✅ سرپرستار در RETURNED_TO_HEAD */}
                {scheduleStatus === 'RETURNED_TO_HEAD' && userRole === 'head' && (
                    <>
                        <button
                            onClick={() => handleAction('save_draft')}
                            className="action-btn action-btn-save-draft"
                        >
                            <span className="action-btn-icon">💾</span>
                            <span>ذخیره موقت ({typeLabel})</span>
                        </button>
                        <button
                            onClick={() => handleAction('approve')}
                            className="action-btn action-btn-approve"
                        >
                            <span className="action-btn-icon">✅</span>
                            <span>تایید مجدد {typeLabel}</span>
                        </button>
                    </>
                )}

                {/* ✅ سوپروایزر در RETURNED_TO_SUPERVISOR */}
                {scheduleStatus === 'RETURNED_TO_SUPERVISOR' && userRole === 'supervisor' && (
                    <>
                        <button
                            onClick={() => handleAction('approve')}
                            className="action-btn action-btn-approve"
                        >
                            <span className="action-btn-icon">✅</span>
                            <span>تایید مجدد {typeLabel}</span>
                        </button>
                        <button
                            onClick={() => handleAction('reject')}
                            className="action-btn action-btn-reject"
                        >
                            <span className="action-btn-icon">🔄</span>
                            <span>بازگردانی به سرپرستار</span>
                        </button>
                    </>
                )}

                {/* ✅ مترون در LOCKED */}
                {scheduleStatus === 'LOCKED' && userRole === 'admin' && (
                    <button
                        onClick={() => handleAction('reset')}
                        className="action-btn action-btn-reset"
                    >
                        <span className="action-btn-icon">♻️</span>
                        <span>بازگشت {typeLabel} به حالت صفر</span>
                    </button>
                )}
            </div>
        </div>
    );
}

export default ScheduleActions;