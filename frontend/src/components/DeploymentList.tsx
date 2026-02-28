/**
 * DeploymentList component - displays all deployments for a TerraformPlan
 * Requirements: 3.2, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5, 7.6, 8.2
 */

import React from 'react';
import { Deployment } from '@/types/deployment';
import { StatusBadge } from './StatusBadge';
import { formatRelativeTime, calculateDuration, calculateElapsedTime } from '@/lib/timeUtils';

interface DeploymentListProps {
    deployments: Deployment[];
}

export const DeploymentList: React.FC<DeploymentListProps> = ({ deployments }) => {
    // Handle empty state (Requirement 8.2)
    if (deployments.length === 0) {
        return (
            <div className="px-6 py-8 text-center text-slate-400">
                No deployments yet for this plan
            </div>
        );
    }

    return (
        <div className="px-6 pb-6 space-y-3">
            {deployments.map((deployment) => {
                // Calculate time display based on status (Requirements 5.1, 5.2, 5.3, 5.4, 5.5)
                const relativeTime = formatRelativeTime(deployment.created_at);

                let durationDisplay = '';
                if (deployment.status === 'success' || deployment.status === 'destroyed') {
                    // Completed deployments: show duration (Requirements 5.2, 5.3)
                    const completedTime = deployment.completed_at || deployment.updated_at;
                    durationDisplay = calculateDuration(deployment.created_at, completedTime);
                } else if (deployment.status === 'failed' || deployment.status === 'destroy_failed') {
                    // Failed deployments: show duration until failure (Requirement 5.5)
                    const failedTime = deployment.completed_at || deployment.updated_at;
                    durationDisplay = calculateDuration(deployment.created_at, failedTime);
                } else if (deployment.status === 'running' || deployment.status === 'started') {
                    // In-progress deployments: show elapsed time (Requirement 5.4)
                    durationDisplay = calculateElapsedTime(deployment.created_at);
                }

                return (
                    <div
                        key={deployment.id}
                        className="bg-slate-900/50 border border-slate-800 rounded-2xl p-4"
                    >
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-2">
                                    {/* Status badge (Requirements 4.1, 4.2, 4.3, 4.4) */}
                                    <StatusBadge status={deployment.status} size="sm" />

                                    {/* Relative time (Requirement 5.1) */}
                                    <span className="text-sm text-slate-300">
                                        {relativeTime}
                                    </span>
                                </div>

                                {/* Duration display */}
                                {durationDisplay && (
                                    <div className="text-sm text-slate-400 mb-2">
                                        {durationDisplay}
                                    </div>
                                )}

                                {/* Error message for failed deployments */}
                                {(deployment.status === 'failed' || deployment.status === 'destroy_failed') &&
                                    deployment.error_message && (
                                        <div className="mt-2 text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                                            <span className="font-medium">Error: </span>
                                            {deployment.error_message}
                                        </div>
                                    )}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
