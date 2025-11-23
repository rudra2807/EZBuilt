// frontend/src/App.tsx
import React, { useState } from 'react';
import './App.css';
import EZBuiltService, {
  CFNLinkResponse,
  TerraformGenerateResponse,
  DeploymentStatus,
} from './services/ezbuilt.service';

const service = new EZBuiltService('demo-user-123');

type Step = 'connect' | 'generate' | 'deploy' | 'complete';

function App() {
  const [currentStep, setCurrentStep] = useState<Step>('connect');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 1: Connection
  const [cfnLink, setCfnLink] = useState<string | null>(null);
  const [externalId, setExternalId] = useState<string | null>(null);
  const [roleArn, setRoleArn] = useState('');
  const [isConnected, setIsConnected] = useState(false);

  // Step 2: Generation
  const [requirements, setRequirements] = useState('');
  const [terraformCode, setTerraformCode] = useState('');
  const [terraformId, setTerraformId] = useState('');

  // Step 3: Deployment
  const [deploymentId, setDeploymentId] = useState('');
  const [deploymentStatus, setDeploymentStatus] = useState<DeploymentStatus | null>(null);
  const [deploymentOutput, setDeploymentOutput] = useState('');
  const [showDestroyConfirm, setShowDestroyConfirm] = useState(false);
  const [isDestroying, setIsDestroying] = useState(false);

  // ============================================
  // STEP 1: Connect AWS Account
  // ============================================

  const handleGenerateCFNLink = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await service.generateCFNLink();
      setCfnLink(response.cfn_link);
      setExternalId(response.external_id);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleManualConnect = async () => {
    if (!roleArn || !externalId) {
      setError('Please provide Role ARN');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await service.connectAccountManual(roleArn, externalId);
      setIsConnected(true);
      setCurrentStep('generate');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // STEP 2: Generate Terraform
  // ============================================

  const handleGenerateTerraform = async () => {
    if (!requirements.trim()) {
      setError('Please describe your infrastructure requirements');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await service.generateTerraform(requirements);

      if (response.status === 'error') {
        setError(response.message || 'Failed to generate Terraform');
        return;
      }

      setTerraformCode(response.code || '');
      setTerraformId(response.terraform_id || '');
      setCurrentStep('deploy');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // STEP 3: Deploy
  // ============================================

  const handleDeploy = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await service.deployTerraform(terraformId);
      setDeploymentId(response.deployment_id);

      // Start polling for status
      service.waitForDeployment(response.deployment_id, (status) => {
        setDeploymentStatus(status);
        setDeploymentOutput(status.output);

        if (status.status === 'success') {
          setCurrentStep('complete');
        }
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // DESTROY INFRASTRUCTURE
  // ============================================

  const handleDestroy = async () => {
    setIsDestroying(true);
    setError(null);
    setShowDestroyConfirm(false);

    try {
      const response = await service.destroyTerraform(terraformId);
      setDeploymentId(response.deployment_id);

      // Start polling for destroy status
      service.waitForDeployment(response.deployment_id, (status) => {
        setDeploymentStatus(status);
        setDeploymentOutput(status.output);

        if (status.status === 'destroyed') {
          setDeploymentStatus(status);
          setIsDestroying(false);
        } else if (status.status === 'destroy_failed') {
          setError('Failed to destroy infrastructure');
          setIsDestroying(false);
        }
      });
    } catch (err: any) {
      setError(err.message);
      setIsDestroying(false);
    }
  };

  const handleStartOver = () => {
    setCurrentStep('generate');
    setRequirements('');
    setTerraformCode('');
    setTerraformId('');
    setDeploymentId('');
    setDeploymentStatus(null);
    setDeploymentOutput('');
    setShowDestroyConfirm(false);
  };

  // ============================================
  // RENDER
  // ============================================

  return (
    <div className="App">
      <header className="App-header">
        <h1>🚀 EZBuilt Platform</h1>
        <p>Infrastructure as a Conversation</p>
      </header>

      <div className="container">
        {/* Progress Steps */}
        <div className="steps">
          <div className={`step ${currentStep === 'connect' ? 'active' : ''} ${isConnected ? 'completed' : ''}`}>
            1. Connect AWS
          </div>
          <div className={`step ${currentStep === 'generate' ? 'active' : ''} ${terraformCode ? 'completed' : ''}`}>
            2. Generate
          </div>
          <div className={`step ${currentStep === 'deploy' ? 'active' : ''} ${deploymentStatus?.status === 'success' ? 'completed' : ''}`}>
            3. Deploy
          </div>
          <div className={`step ${currentStep === 'complete' ? 'active' : ''}`}>
            4. Complete
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-box">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* STEP 1: Connect AWS Account */}
        {currentStep === 'connect' && (
          <div className="step-content">
            <h2>Step 1: Connect Your AWS Account</h2>

            {!cfnLink ? (
              <div>
                <p>Click the button below to generate your CloudFormation setup link.</p>
                <button
                  className="btn btn-primary"
                  onClick={handleGenerateCFNLink}
                  disabled={loading}
                >
                  {loading ? 'Generating...' : 'Generate CloudFormation Link'}
                </button>
              </div>
            ) : (
              <div>
                <div className="info-box">
                  <p><strong>External ID:</strong> {externalId}</p>
                  <p>This ID is used for secure cross-account access.</p>
                </div>

                <div className="action-box">
                  <h3>Follow these steps:</h3>
                  <ol>
                    <li>Click the button below to open AWS CloudFormation</li>
                    <li>Review the permissions and click "Create stack"</li>
                    <li>Wait for the stack to complete (2-3 minutes)</li>
                    <li>Copy the Role ARN from the "Outputs" tab</li>
                    <li>Paste it below and click "Connect"</li>
                  </ol>

                  <a
                    href={cfnLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-success"
                  >
                    Open CloudFormation Console →
                  </a>
                </div>

                <div className="input-group">
                  <label>Role ARN (from CloudFormation Outputs):</label>
                  <input
                    type="text"
                    placeholder="arn:aws:iam::123456789012:role/EZBuilt-DeploymentRole-..."
                    value={roleArn}
                    onChange={(e) => setRoleArn(e.target.value)}
                    className="input-field"
                  />
                  <button
                    className="btn btn-primary"
                    onClick={handleManualConnect}
                    disabled={loading || !roleArn}
                  >
                    {loading ? 'Connecting...' : 'Connect Account'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 2: Generate Terraform */}
        {currentStep === 'generate' && (
          <div className="step-content">
            <h2>Step 2: Describe Your Infrastructure</h2>
            <p>Tell us what you need in plain English. Our AI will generate the Terraform code.</p>

            <div className="input-group">
              <label>Infrastructure Requirements:</label>
              <textarea
                rows={6}
                placeholder="Example: I need a web server running nginx with 2GB RAM, a PostgreSQL database with 20GB storage, and an S3 bucket for file uploads"
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                className="textarea-field"
              />
              <button
                className="btn btn-primary"
                onClick={handleGenerateTerraform}
                disabled={loading || !requirements.trim()}
              >
                {loading ? 'Generating...' : 'Generate Terraform Code'}
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: Deploy */}
        {currentStep === 'deploy' && (
          <div className="step-content">
            <h2>Step 3: Review & Deploy</h2>

            <div className="code-preview">
              <h3>Generated Terraform Code:</h3>
              <pre>{terraformCode}</pre>
            </div>

            <div className="action-box">
              <p>Review the code above. When ready, click deploy to provision this infrastructure in your AWS account.</p>
              <button
                className="btn btn-success"
                onClick={handleDeploy}
                disabled={loading || !!deploymentId}
              >
                {loading ? 'Deploying...' : '🚀 Deploy to AWS'}
              </button>
            </div>

            {deploymentStatus && (
              <div className={`status-box status-${deploymentStatus.status}`}>
                <h3>Deployment Status: {deploymentStatus.status.toUpperCase()}</h3>
                <pre className="output-box">{deploymentOutput}</pre>
              </div>
            )}
          </div>
        )}

        {/* STEP 4: Complete */}
        {currentStep === 'complete' && (
          <div className="step-content">
            <h2>🎉 Deployment Complete!</h2>
            <div className="success-box">
              <p>Your infrastructure has been successfully deployed to AWS.</p>
              <pre className="output-box">{deploymentOutput}</pre>
            </div>

            {/* Destroy Confirmation Dialog */}
            {showDestroyConfirm && (
              <div className="modal-overlay">
                <div className="modal-content">
                  <h3>⚠️ Confirm Destroy</h3>
                  <p>
                    Are you sure you want to destroy this infrastructure? This action cannot be undone.
                    All resources will be permanently deleted from your AWS account.
                  </p>
                  <div className="modal-actions">
                    <button
                      className="btn btn-secondary"
                      onClick={() => setShowDestroyConfirm(false)}
                    >
                      Cancel
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={handleDestroy}
                    >
                      Yes, Destroy Infrastructure
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Destroy Status */}
            {isDestroying && deploymentStatus && (
              <div className={`status-box status-${deploymentStatus.status}`}>
                <h3>Destroy Status: {deploymentStatus.status.toUpperCase()}</h3>
                <pre className="output-box">{deploymentOutput}</pre>
              </div>
            )}

            {/* Show destroyed message */}
            {deploymentStatus?.status === 'destroyed' && (
              <div className="success-box">
                <h3>✅ Infrastructure Destroyed</h3>
                <p>All resources have been successfully removed from your AWS account.</p>
              </div>
            )}

            <div className="action-box">
              <div className="button-group">
                {!isDestroying && deploymentStatus?.status !== 'destroyed' && (
                  <button
                    className="btn btn-danger"
                    onClick={() => setShowDestroyConfirm(true)}
                  >
                    🗑️ Destroy Infrastructure
                  </button>
                )}

                <button
                  className="btn btn-primary"
                  onClick={handleStartOver}
                  disabled={isDestroying}
                >
                  {deploymentStatus?.status === 'destroyed'
                    ? '🚀 Deploy New Infrastructure'
                    : '➕ Deploy Another Infrastructure'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;