/**
 * PlanCard component - displays summary information for a TerraformPlan
 * Requirements: 1.2, 1.3, 1.4, 1.5, 3.1, 3.3, 7.2, 7.3, 8.1, 8.3
 */

import React from 'react';
import { TerraformPlanWithDeployments } from '@/types/deployment';
import { StatusBadge } from './StatusBadge';

interface PlanCardProps {
    plan: TerraformPlanWithDeployments;
    isExpanded: boolean;
    onToggle: () => void;
}

export const PlanCard: React.FC<PlanCardProps> = ({ plan, isExpanded, onToggle }) => {
    // Truncate requirements to 150 characters (Requirement 1.2)
    const truncatedRequirements = plan.original_requirements.length > 150
        ? plan.original_requirements.substring(0, 150) + '...'
        : plan.original_requirements;

    // Format created date in ISO 8601 format (Requirement 1.3)
    const formattedDate = new Date(plan.created_at).toISOString().replace('T', ' ').substring(0, 19);

    // Determine status badge to display (Requirements 1.5, 8.3)
    const displayStatus = plan.latest_deployment_status || 'not_deployed';

    return (
        <div
            className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 hover:border-slate-700 transition-colors cursor-pointer"
            onClick={onToggle}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                    {/* Requirements summary */}
                    <p className="text-slate-200 mb-3 leading-relaxed">
                        {truncatedRequirements}
                    </p>

                    {/* Metadata row */}
                    <div className="flex items-center gap-4 text-sm">
                        {/* Created date (Requirement 1.3) */}
                        <span className="text-slate-300">
                            Created: {formattedDate}
                        </span>

                        {/* Deployment count badge (Requirements 1.4, 8.1) */}
                        <span className="text-slate-400">
                            {plan.deployment_count} {plan.deployment_count === 1 ? 'deployment' : 'deployments'}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Latest deployment status (Requirements 1.5, 8.3) */}
                    {displayStatus === 'not_deployed' ? (
                        <span className="inline-flex items-center gap-1.5 border rounded-2xl font-medium border-slate-600/70 bg-slate-600/10 text-slate-300 px-3 py-1 text-xs">
                            <span className="leading-none">○</span>
                            <span>Not Deployed</span>
                        </span>
                    ) : (
                        <StatusBadge status={displayStatus as any} size="sm" />
                    )}

                    {/* Expand/collapse indicator (Requirement 3.1, 3.3) */}
                    <div className="text-slate-400 text-xl">
                        {isExpanded ? '▼' : '▶'}
                    </div>
                </div>
            </div>
        </div>
    );
};
