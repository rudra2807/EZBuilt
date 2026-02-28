import React from 'react';

type DeploymentStatus =
    | 'started'
    | 'running'
    | 'success'
    | 'failed'
    | 'destroyed'
    | 'destroy_failed';

interface StatusBadgeProps {
    status: DeploymentStatus;
    size?: 'sm' | 'md';
}

const statusConfig: Record<DeploymentStatus, {
    classes: string;
    icon: string;
    label: string;
}> = {
    success: {
        classes: 'border-emerald-500/70 bg-emerald-500/10 text-emerald-100',
        icon: '✓',
        label: 'Success',
    },
    failed: {
        classes: 'border-red-500/70 bg-red-500/10 text-red-100',
        icon: '✕',
        label: 'Failed',
    },
    destroy_failed: {
        classes: 'border-red-500/70 bg-red-500/10 text-red-100',
        icon: '✕',
        label: 'Destroy Failed',
    },
    running: {
        classes: 'border-amber-500/70 bg-amber-500/10 text-amber-100',
        icon: '⟳',
        label: 'Running',
    },
    started: {
        classes: 'border-amber-500/70 bg-amber-500/10 text-amber-100',
        icon: '⟳',
        label: 'Started',
    },
    destroyed: {
        classes: 'border-slate-600/70 bg-slate-600/10 text-slate-300',
        icon: '○',
        label: 'Destroyed',
    },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
    const config = statusConfig[status];
    const sizeClasses = size === 'sm' ? 'px-3 py-1 text-xs' : 'px-4 py-2 text-sm';

    return (
        <span
            className={`inline-flex items-center gap-1.5 border rounded-2xl font-medium ${config.classes} ${sizeClasses}`}
        >
            <span className="leading-none">{config.icon}</span>
            <span>{config.label}</span>
        </span>
    );
};
