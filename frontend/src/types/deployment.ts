/**
 * Type definitions for deployment history feature
 * Requirements: 2.2, 2.4
 */

export type DeploymentStatus =
  | "started"
  | "running"
  | "success"
  | "failed"
  | "destroyed"
  | "destroy_failed";

export interface Deployment {
  id: string;
  status: DeploymentStatus;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface TerraformPlanWithDeployments {
  id: string;
  user_id: string;
  original_requirements: string;
  created_at: string;
  deployment_count: number;
  latest_deployment_status: string | null;
  deployments: Deployment[];
}
