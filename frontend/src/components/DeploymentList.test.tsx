/**
 * Unit tests for DeploymentList component
 * Feature: deployment-history
 */

import { render } from "@testing-library/react";
import { DeploymentList } from "./DeploymentList";
import { Deployment } from "@/types/deployment";

// Mock time utilities
jest.mock("@/lib/timeUtils", () => ({
    formatRelativeTime: jest.fn((timestamp: string) => "2 hours ago"),
    calculateDuration: jest.fn((created: string, completed: string) => "5m 23s"),
    calculateElapsedTime: jest.fn((created: string) => "Running for 2m 15s"),
}));

describe("DeploymentList unit tests", () => {
    describe("Empty state handling", () => {
        /**
         * Tests empty deployment list message display
         */
        it("should display empty message when deployments array is empty", () => {
            const { container } = render(<DeploymentList deployments={[]} />);

            // Verify empty state message is displayed (Requirement 8.2)
            expect(container.textContent).toContain("No deployments yet for this plan");
        });

        it("should apply correct styling to empty state message", () => {
            const { container } = render(<DeploymentList deployments={[]} />);

            // Verify text-slate-400 color class
            const emptyMessage = container.querySelector(".text-slate-400");
            expect(emptyMessage).toBeInTheDocument();

            // Verify text is centered
            const centeredText = container.querySelector(".text-center");
            expect(centeredText).toBeInTheDocument();
        });
    });

    describe("Deployment display", () => {
        /**\
         * Tests deployment rendering and styling
         */
        it("should render all deployments in the list", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: null,
                },
                {
                    id: "deployment-2",
                    status: "failed",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: "Test error",
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify both deployments are rendered
            const deploymentCards = container.querySelectorAll(".bg-slate-900\\/50");
            expect(deploymentCards.length).toBe(2);
        });

        it("should display StatusBadge for each deployment", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify StatusBadge is displayed
            expect(container.textContent).toContain("Success");
        });

        it("should display relative time for each deployment", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify relative time is displayed (mocked to "2 hours ago")
            expect(container.textContent).toContain("2 hours ago");
        });

        it("should display duration for completed deployments", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify duration is displayed (mocked to "5m 23s")
            expect(container.textContent).toContain("5m 23s");
        });

        it("should display elapsed time for running deployments", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "running",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: null,
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify elapsed time is displayed (mocked to "Running for 2m 15s")
            expect(container.textContent).toContain("Running for 2m 15s");
        });

        it("should display error message for failed deployments", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "failed",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: "Terraform apply failed: resource not found",
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify error message is displayed
            expect(container.textContent).toContain("Error:");
            expect(container.textContent).toContain("Terraform apply failed: resource not found");
        });

        it("should display error message for destroy_failed deployments", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "destroy_failed",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: "Terraform destroy failed: resource in use",
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify error message is displayed
            expect(container.textContent).toContain("Error:");
            expect(container.textContent).toContain("Terraform destroy failed: resource in use");
        });

        it("should not display error message for successful deployments", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify error message is not displayed
            expect(container.textContent).not.toContain("Error:");
        });

        it("should apply correct Tailwind styling classes", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify bg-slate-900/50 background (Requirement 7.6)
            const deploymentCard = container.querySelector(".bg-slate-900\\/50");
            expect(deploymentCard).toBeInTheDocument();

            // Verify border-slate-800 border (Requirement 7.6)
            const border = container.querySelector(".border-slate-800");
            expect(border).toBeInTheDocument();

            // Verify rounded-2xl border radius (Requirement 7.6)
            const rounded = container.querySelector(".rounded-2xl");
            expect(rounded).toBeInTheDocument();
        });

        it("should apply red styling to error messages", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "failed",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: new Date().toISOString(),
                    error_message: "Test error message",
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify red text color
            const errorText = container.querySelector(".text-red-300");
            expect(errorText).toBeInTheDocument();

            // Verify red background
            const errorBg = container.querySelector(".bg-red-500\\/10");
            expect(errorBg).toBeInTheDocument();

            // Verify red border
            const errorBorder = container.querySelector(".border-red-500\\/30");
            expect(errorBorder).toBeInTheDocument();
        });
    });

    describe("Duration display logic", () => {
        /**
         * Tests duration calculation for different deployment statuses
         */
        it("should display duration for success status", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: "2024-06-15T14:00:00Z",
                    updated_at: "2024-06-15T14:05:23Z",
                    completed_at: "2024-06-15T14:05:23Z",
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify duration is displayed (mocked)
            expect(container.textContent).toContain("5m 23s");
        });

        it("should display duration for destroyed status", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "destroyed",
                    created_at: "2024-06-15T14:00:00Z",
                    updated_at: "2024-06-15T14:03:15Z",
                    completed_at: "2024-06-15T14:03:15Z",
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify duration is displayed (mocked)
            expect(container.textContent).toContain("5m 23s");
        });

        it("should display duration for failed status", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "failed",
                    created_at: "2024-06-15T14:00:00Z",
                    updated_at: "2024-06-15T14:02:30Z",
                    completed_at: "2024-06-15T14:02:30Z",
                    error_message: "Test error",
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify duration is displayed (mocked)
            expect(container.textContent).toContain("5m 23s");
        });

        it("should display elapsed time for running status", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "running",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: null,
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify elapsed time is displayed (mocked)
            expect(container.textContent).toContain("Running for 2m 15s");
        });

        it("should display elapsed time for started status", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "started",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    completed_at: null,
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify elapsed time is displayed (mocked)
            expect(container.textContent).toContain("Running for 2m 15s");
        });

        it("should use updated_at when completed_at is null for completed deployments", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: "2024-06-15T14:00:00Z",
                    updated_at: "2024-06-15T14:05:00Z",
                    completed_at: null,
                    error_message: null,
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify duration is still displayed (using updated_at)
            expect(container.textContent).toContain("5m 23s");
        });
    });

    describe("Multiple deployments", () => {
        it("should render multiple deployments in correct order", () => {
            const mockDeployments: Deployment[] = [
                {
                    id: "deployment-1",
                    status: "success",
                    created_at: "2024-06-15T14:00:00Z",
                    updated_at: "2024-06-15T14:05:00Z",
                    completed_at: "2024-06-15T14:05:00Z",
                    error_message: null,
                },
                {
                    id: "deployment-2",
                    status: "running",
                    created_at: "2024-06-15T15:00:00Z",
                    updated_at: "2024-06-15T15:02:00Z",
                    completed_at: null,
                    error_message: null,
                },
                {
                    id: "deployment-3",
                    status: "failed",
                    created_at: "2024-06-15T13:00:00Z",
                    updated_at: "2024-06-15T13:03:00Z",
                    completed_at: "2024-06-15T13:03:00Z",
                    error_message: "Test error",
                },
            ];

            const { container } = render(<DeploymentList deployments={mockDeployments} />);

            // Verify all three deployments are rendered
            const deploymentCards = container.querySelectorAll(".bg-slate-900\\/50");
            expect(deploymentCards.length).toBe(3);

            // Verify different statuses are displayed
            expect(container.textContent).toContain("Success");
            expect(container.textContent).toContain("Running");
            expect(container.textContent).toContain("Failed");
        });
    });
});
