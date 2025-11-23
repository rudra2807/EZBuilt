// frontend/src/services/ezbuilt.service.ts

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

export interface CFNLinkResponse {
  cfn_link: string;
  external_id: string;
  instructions: string;
}

export interface ConnectionStatus {
  connected: boolean;
  status: string;
  role_arn?: string;
}

export interface TerraformGenerateResponse {
  status: string;
  terraform_id?: string;
  code?: string;
  validation?: any;
  message?: string;
  errors?: string;
}

export interface DeploymentResponse {
  deployment_id: string;
  status: string;
  message: string;
}

export interface DeploymentStatus {
  deployment_id: string;
  status:
    | "started"
    | "planned"
    | "success"
    | "failed"
    | "destroyed"
    | "destroy_failed";
  output: string;
  started_at: string;
  completed_at: string | null;
}

class EZBuiltService {
  private userId: string;

  constructor(userId: string = "demo-user") {
    this.userId = userId;
  }

  /**
   * Step 1: Generate CloudFormation link for AWS account connection
   */
  async generateCFNLink(): Promise<CFNLinkResponse> {
    const response = await fetch(`${API_BASE_URL}/api/generate-cfn-link`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: this.userId,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to generate CloudFormation link");
    }

    return await response.json();
  }

  /**
   * Check connection status (for polling)
   */
  async checkConnectionStatus(externalId: string): Promise<ConnectionStatus> {
    const response = await fetch(
      `${API_BASE_URL}/api/connection-status/${externalId}`
    );

    if (!response.ok) {
      throw new Error("Failed to check connection status");
    }

    return await response.json();
  }

  /**
   * Wait for AWS account to be connected (polls every 5 seconds)
   */
  async waitForConnection(
    externalId: string,
    onProgress?: (status: ConnectionStatus) => void
  ): Promise<ConnectionStatus> {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const status = await this.checkConnectionStatus(externalId);

          if (onProgress) {
            onProgress(status);
          }

          if (status.connected) {
            clearInterval(interval);
            resolve(status);
          }
        } catch (error) {
          clearInterval(interval);
          reject(error);
        }
      }, 5000); // Poll every 5 seconds

      // Timeout after 10 minutes
      setTimeout(() => {
        clearInterval(interval);
        reject(new Error("Connection timeout - please try again"));
      }, 600000);
    });
  }

  /**
   * Manual connection method (for MVP)
   */
  async connectAccountManual(
    roleArn: string,
    externalId: string
  ): Promise<any> {
    const response = await fetch(
      `${API_BASE_URL}/api/connect-account-manual?user_id=${
        this.userId
      }&role_arn=${encodeURIComponent(roleArn)}&external_id=${externalId}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to connect account");
    }

    return await response.json();
  }

  /**
   * Step 2: Generate Terraform code from natural language
   */
  async generateTerraform(
    requirements: string
  ): Promise<TerraformGenerateResponse> {
    const response = await fetch(`${API_BASE_URL}/api/generate-terraform`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: this.userId,
        requirements: requirements,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to generate Terraform");
    }

    return await response.json();
  }

  /**
   * Step 3: Deploy Terraform to AWS
   */
  async deployTerraform(terraformId: string): Promise<DeploymentResponse> {
    const response = await fetch(`${API_BASE_URL}/api/deploy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: this.userId,
        terraform_id: terraformId,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to deploy");
    }

    return await response.json();
  }

  /**
   * Get deployment status
   */
  async getDeploymentStatus(deploymentId: string): Promise<DeploymentStatus> {
    const response = await fetch(
      `${API_BASE_URL}/api/deployment/${deploymentId}/status`
    );

    if (!response.ok) {
      throw new Error("Failed to get deployment status");
    }

    return await response.json();
  }

  /**
   * Poll deployment status until completion
   */
  async waitForDeployment(
    deploymentId: string,
    onProgress?: (status: DeploymentStatus) => void
  ): Promise<DeploymentStatus> {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const status = await this.getDeploymentStatus(deploymentId);

          if (onProgress) {
            onProgress(status);
          }

          if (status.status === "success" || status.status === "failed") {
            clearInterval(interval);
            resolve(status);
          }
        } catch (error) {
          clearInterval(interval);
          reject(error);
        }
      }, 3000); // Poll every 3 seconds

      // Timeout after 30 minutes
      setTimeout(() => {
        clearInterval(interval);
        reject(new Error("Deployment timeout"));
      }, 1800000);
    });
  }

  /**
   * Get all terraform configs for user
   */
  async getUserTerraform(): Promise<any> {
    const response = await fetch(
      `${API_BASE_URL}/api/user/${this.userId}/terraform`
    );

    if (!response.ok) {
      throw new Error("Failed to get terraform configs");
    }

    return await response.json();
  }

  /**
   * Get all deployments for user
   */
  async getUserDeployments(): Promise<any> {
    const response = await fetch(
      `${API_BASE_URL}/api/user/${this.userId}/deployments`
    );

    if (!response.ok) {
      throw new Error("Failed to get deployments");
    }

    return await response.json();
  }

  /**
   * Get terraform resource status
   */
  async getTerraformResources(terraformId: string): Promise<any> {
    const response = await fetch(
      `${API_BASE_URL}/api/terraform/${terraformId}/resources`
    );

    if (!response.ok) {
      throw new Error("Failed to get terraform resources");
    }

    return await response.json();
  }

  /**
   * Destroy infrastructure
   */
  async destroyTerraform(terraformId: string): Promise<DeploymentResponse> {
    const response = await fetch(`${API_BASE_URL}/api/destroy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: this.userId,
        terraform_id: terraformId,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to destroy infrastructure");
    }

    return await response.json();
  }
}

export default EZBuiltService;
