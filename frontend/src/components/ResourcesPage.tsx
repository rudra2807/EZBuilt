// frontend/src/components/ResourcesPage.tsx
import React, { useState, useEffect } from 'react';
import EZBuiltService, { DeploymentStatus } from '../services/ezbuilt.service';
import './ResourcesPage.css';

const service = new EZBuiltService('demo-user-123');

interface TerraformConfig {
    id: string;
    user_id: string;
    requirements: string;
    code: string;
    created_at: string;
}

interface Deployment {
    id: string;
    user_id: string;
    terraform_id: string;
    status: string;
    operation: string;
    output: string;
    started_at: string;
    completed_at: string | null;
}

const ResourcesPage: React.FC = () => {
    const [terraformConfigs, setTerraformConfigs] = useState<TerraformConfig[]>([]);
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
    const [showDestroyConfirm, setShowDestroyConfirm] = useState(false);
    const [destroyingId, setDestroyingId] = useState<string | null>(null);
    const [destroyStatus, setDestroyStatus] = useState<DeploymentStatus | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        setError(null);

        try {
            const [tfResponse, deployResponse] = await Promise.all([
                service.getUserTerraform(),
                service.getUserDeployments(),
            ]);

            setTerraformConfigs(tfResponse.terraform_configs || []);
            setDeployments(deployResponse.deployments || []);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const getConfigStatus = (configId: string) => {
        const configDeployments = deployments.filter(
            (d) => d.terraform_id === configId
        );

        if (configDeployments.length === 0) {
            return { status: 'not_deployed', label: 'Not Deployed', color: 'gray' };
        }

        // Check for active deployments
        const activeDeployment = configDeployments.find((d) =>
            ['started', 'planned', 'destroying'].includes(d.status)
        );
        if (activeDeployment) {
            return {
                status: activeDeployment.status,
                label: activeDeployment.status === 'destroying' ? 'Destroying' : 'Deploying',
                color: 'blue',
            };
        }

        // Check for successful deployments that haven't been destroyed
        const successDeployments = configDeployments.filter((d) => d.status === 'success');
        const destroyedDeployments = configDeployments.filter((d) => d.status === 'destroyed');

        if (successDeployments.length > destroyedDeployments.length) {
            return { status: 'deployed', label: 'Deployed', color: 'green' };
        }

        if (destroyedDeployments.length > 0) {
            return { status: 'destroyed', label: 'Destroyed', color: 'orange' };
        }

        const failedDeployment = configDeployments.find((d) => d.status === 'failed');
        if (failedDeployment) {
            return { status: 'failed', label: 'Failed', color: 'red' };
        }

        return { status: 'unknown', label: 'Unknown', color: 'gray' };
    };

    const handleDestroy = async (configId: string) => {
        setDestroyingId(configId);
        setShowDestroyConfirm(false);
        setError(null);

        try {
            const response = await service.destroyTerraform(configId);

            // Poll for destroy status
            service.waitForDeployment(response.deployment_id, (status) => {
                setDestroyStatus(status);

                if (status.status === 'destroyed' || status.status === 'destroy_failed') {
                    setDestroyingId(null);
                    loadData(); // Reload data to update status
                }
            });
        } catch (err: any) {
            setError(err.message);
            setDestroyingId(null);
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString();
    };

    if (loading) {
        return (
            <div className="resources-page">
                <div className="loading">Loading resources...</div>
            </div>
        );
    }

    return (
        <div className="resources-page">
            <div className="resources-header">
                <h1>📦 Your Infrastructure</h1>
                <p>Manage all your deployed resources</p>
            </div>

            {error && (
                <div className="error-banner">
                    <strong>Error:</strong> {error}
                    <button onClick={() => setError(null)}>×</button>
                </div>
            )}

            {terraformConfigs.length === 0 ? (
                <div className="empty-state">
                    <h2>No Infrastructure Yet</h2>
                    <p>You haven't deployed any infrastructure yet. Get started by creating your first deployment!</p>
                </div>
            ) : (
                <div className="resources-grid">
                    {terraformConfigs.map((config) => {
                        const status = getConfigStatus(config.id);
                        const configDeployments = deployments.filter(
                            (d) => d.terraform_id === config.id
                        );
                        const isDestroying = destroyingId === config.id;
                        const canDestroy = status.status === 'deployed' && !isDestroying;

                        return (
                            <div key={config.id} className="resource-card">
                                <div className="resource-header">
                                    <div className="resource-title">
                                        <h3>{config.requirements.substring(0, 60)}...</h3>
                                        <span className={`status-badge status-${status.color}`}>
                                            {status.label}
                                        </span>
                                    </div>
                                    <div className="resource-meta">
                                        <span>Created: {formatDate(config.created_at)}</span>
                                    </div>
                                </div>

                                <div className="resource-body">
                                    <div className="resource-info">
                                        <p className="requirements">{config.requirements}</p>
                                    </div>

                                    <div className="deployment-history">
                                        <h4>Deployment History ({configDeployments.length})</h4>
                                        {configDeployments.length > 0 ? (
                                            <ul>
                                                {configDeployments
                                                    .sort((a, b) =>
                                                        new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
                                                    )
                                                    .slice(0, 3)
                                                    .map((dep) => (
                                                        <li key={dep.id}>
                                                            <span className={`dep-status status-${dep.status}`}>
                                                                {dep.operation === 'destroy' ? '🗑️' : '🚀'} {dep.status}
                                                            </span>
                                                            <span className="dep-time">{formatDate(dep.started_at)}</span>
                                                        </li>
                                                    ))}
                                            </ul>
                                        ) : (
                                            <p className="no-deployments">No deployments yet</p>
                                        )}
                                    </div>

                                    {isDestroying && destroyStatus && (
                                        <div className="destroy-progress">
                                            <p>Destroying: {destroyStatus.status}</p>
                                            <div className="progress-bar">
                                                <div className="progress-fill"></div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="resource-actions">
                                    <button
                                        className="btn btn-view"
                                        onClick={() => setSelectedConfig(config.id)}
                                    >
                                        View Code
                                    </button>

                                    {canDestroy && (
                                        <button
                                            className="btn btn-destroy"
                                            onClick={() => {
                                                setSelectedConfig(config.id);
                                                setShowDestroyConfirm(true);
                                            }}
                                        >
                                            🗑️ Destroy
                                        </button>
                                    )}

                                    {isDestroying && (
                                        <button className="btn btn-disabled" disabled>
                                            Destroying...
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Code Preview Modal */}
            {selectedConfig && !showDestroyConfirm && (
                <div className="modal-overlay" onClick={() => setSelectedConfig(null)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Terraform Code</h3>
                            <button onClick={() => setSelectedConfig(null)}>×</button>
                        </div>
                        <div className="modal-body">
                            <pre className="code-block">
                                {terraformConfigs.find((c) => c.id === selectedConfig)?.code}
                            </pre>
                        </div>
                    </div>
                </div>
            )}

            {/* Destroy Confirmation Modal */}
            {showDestroyConfirm && selectedConfig && (
                <div className="modal-overlay">
                    <div className="modal-content confirm-modal">
                        <h3>⚠️ Confirm Destroy</h3>
                        <p>
                            Are you sure you want to destroy this infrastructure? This action cannot be undone.
                            All resources will be permanently deleted from your AWS account.
                        </p>
                        <div className="confirm-details">
                            <strong>Infrastructure:</strong>
                            <p>{terraformConfigs.find((c) => c.id === selectedConfig)?.requirements}</p>
                        </div>
                        <div className="modal-actions">
                            <button
                                className="btn btn-secondary"
                                onClick={() => {
                                    setShowDestroyConfirm(false);
                                    setSelectedConfig(null);
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn btn-danger"
                                onClick={() => handleDestroy(selectedConfig)}
                            >
                                Yes, Destroy Infrastructure
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ResourcesPage;