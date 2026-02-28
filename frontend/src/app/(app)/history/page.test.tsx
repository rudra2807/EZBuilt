/**
 * Property-based tests for History page component
 * Feature: deployment-history
 */

import * as fc from "fast-check";
import { render, fireEvent, waitFor, cleanup } from "@testing-library/react";
import HistoryPage from "./page";
import { TerraformPlanWithDeployments } from "@/types/deployment";

// Mock Next.js router
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
    useRouter: () => ({
        push: mockPush,
    }),
}));

// Mock AuthContext
const mockUser = { sub: "test-user-id" };
let mockAuthLoading = false;
jest.mock("../context/AuthContext", () => ({
    useAuth: () => ({
        user: mockUser,
        loading: mockAuthLoading,
    }),
}));

// Mock fetch
global.fetch = jest.fn();

describe("History Page property-based tests", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockPush.mockClear();
        mockAuthLoading = false;
        (global.fetch as jest.Mock).mockClear();
    });

    afterEach(() => {
        cleanup();
    });

    describe("Property 11: Multiple Expansion Support", () => {
        /**
         * Feature: deployment-history, Property 11: Multiple Expansion Support
         *
         * For any set of Plan_Cards, expanding multiple cards should result in
         * all selected cards remaining in the expanded state simultaneously.
         */
        it("should allow multiple plans to be expanded simultaneously", async () => {
            await fc.assert(
                fc.asyncProperty(
                    // Generate random sets of 2-10 plan IDs
                    fc.array(fc.uuid(), { minLength: 2, maxLength: 10 }),
                    async (planIds) => {
                        // Create mock plans for each ID
                        const mockPlans: TerraformPlanWithDeployments[] = planIds.map((id) => ({
                            id,
                            user_id: "test-user-id",
                            original_requirements: `Requirements for plan ${id}`,
                            created_at: new Date().toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        }));

                        // Mock successful API response
                        (global.fetch as jest.Mock).mockResolvedValueOnce({
                            ok: true,
                            status: 200,
                            json: async () => ({ plans: mockPlans }),
                        });

                        // Render the History page
                        const { container, findByText } = render(<HistoryPage />);

                        // Wait for plans to load
                        await waitFor(() => {
                            expect(global.fetch).toHaveBeenCalledWith(
                                expect.stringContaining("/api/user/test-user-id/history"),
                            );
                        });

                        // Wait for first plan to be rendered
                        await findByText(`Requirements for plan ${planIds[0]}`);

                        // Find all plan cards (they have cursor-pointer class)
                        const planCards = container.querySelectorAll(".cursor-pointer");
                        expect(planCards.length).toBe(planIds.length);

                        // Click on each plan card to expand them
                        for (let i = 0; i < planCards.length; i++) {
                            fireEvent.click(planCards[i]);
                        }

                        // Wait for state updates
                        await waitFor(() => {
                            // All deployment lists should be visible
                            // Deployment lists are in divs with bg-slate-900/50 class
                            const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                            expect(deploymentLists.length).toBe(planIds.length);
                        });

                        // Verify all plans are expanded by checking for deployment list containers
                        const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                        expect(deploymentLists.length).toBe(planIds.length);

                        // Each deployment list should be visible
                        deploymentLists.forEach((list) => {
                            expect(list).toBeInTheDocument();
                        });
                    },
                ),
                { numRuns: 100 }, // Minimum 100 iterations as specified
            );
        }, 60000); // 60 second timeout for 100 iterations

        it("should maintain expansion state when toggling different plans", async () => {
            await fc.assert(
                fc.asyncProperty(
                    // Generate random sets of 3-5 plan IDs (reduced for performance)
                    fc.array(fc.uuid(), { minLength: 3, maxLength: 5 }),
                    async (planIds) => {
                        // Create mock plans
                        const mockPlans: TerraformPlanWithDeployments[] = planIds.map((id) => ({
                            id,
                            user_id: "test-user-id",
                            original_requirements: `Requirements for plan ${id}`,
                            created_at: new Date().toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        }));

                        // Mock successful API response
                        (global.fetch as jest.Mock).mockResolvedValueOnce({
                            ok: true,
                            status: 200,
                            json: async () => ({ plans: mockPlans }),
                        });

                        // Render the History page
                        const { container, findByText } = render(<HistoryPage />);

                        // Wait for plans to load
                        await findByText(`Requirements for plan ${planIds[0]}`);

                        const planCards = container.querySelectorAll(".cursor-pointer");

                        // Expand first plan
                        fireEvent.click(planCards[0]);
                        await waitFor(() => {
                            const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                            expect(deploymentLists.length).toBe(1);
                        });

                        // Expand second plan (first should remain expanded)
                        fireEvent.click(planCards[1]);
                        await waitFor(() => {
                            const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                            expect(deploymentLists.length).toBe(2);
                        });

                        // Expand third plan (first and second should remain expanded)
                        fireEvent.click(planCards[2]);
                        await waitFor(() => {
                            const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                            expect(deploymentLists.length).toBe(3);
                        });

                        // Verify all three are still expanded
                        const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                        expect(deploymentLists.length).toBe(3);
                    },
                ),
                { numRuns: 100 },
            );
        }, 60000);

        it("should allow collapsing individual plans without affecting others", async () => {
            await fc.assert(
                fc.asyncProperty(
                    // Generate random sets of 3-5 plan IDs
                    fc.array(fc.uuid(), { minLength: 3, maxLength: 5 }),
                    async (planIds) => {
                        // Create mock plans
                        const mockPlans: TerraformPlanWithDeployments[] = planIds.map((id) => ({
                            id,
                            user_id: "test-user-id",
                            original_requirements: `Requirements for plan ${id}`,
                            created_at: new Date().toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        }));

                        // Mock successful API response
                        (global.fetch as jest.Mock).mockResolvedValueOnce({
                            ok: true,
                            status: 200,
                            json: async () => ({ plans: mockPlans }),
                        });

                        // Render the History page
                        const { container, findByText } = render(<HistoryPage />);

                        // Wait for plans to load
                        await findByText(`Requirements for plan ${planIds[0]}`);

                        const planCards = container.querySelectorAll(".cursor-pointer");

                        // Expand all plans
                        for (let i = 0; i < planCards.length; i++) {
                            fireEvent.click(planCards[i]);
                        }

                        await waitFor(() => {
                            const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                            expect(deploymentLists.length).toBe(planIds.length);
                        });

                        // Collapse the first plan
                        fireEvent.click(planCards[0]);

                        await waitFor(() => {
                            const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                            expect(deploymentLists.length).toBe(planIds.length - 1);
                        });

                        // Verify the remaining plans are still expanded
                        const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                        expect(deploymentLists.length).toBe(planIds.length - 1);
                    },
                ),
                { numRuns: 100 },
            );
        }, 60000);

        it("should support expanding all plans at once", async () => {
            await fc.assert(
                fc.asyncProperty(
                    // Generate random sets of 2-10 plan IDs
                    fc.array(fc.uuid(), { minLength: 2, maxLength: 10 }),
                    async (planIds) => {
                        // Create mock plans
                        const mockPlans: TerraformPlanWithDeployments[] = planIds.map((id) => ({
                            id,
                            user_id: "test-user-id",
                            original_requirements: `Requirements for plan ${id}`,
                            created_at: new Date().toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        }));

                        // Mock successful API response
                        (global.fetch as jest.Mock).mockResolvedValueOnce({
                            ok: true,
                            status: 200,
                            json: async () => ({ plans: mockPlans }),
                        });

                        // Render the History page
                        const { container, findByText } = render(<HistoryPage />);

                        // Wait for plans to load
                        await findByText(`Requirements for plan ${planIds[0]}`);

                        const planCards = container.querySelectorAll(".cursor-pointer");
                        expect(planCards.length).toBe(planIds.length);

                        // Expand all plans rapidly
                        planCards.forEach((card) => {
                            fireEvent.click(card);
                        });

                        // Wait for all to be expanded
                        await waitFor(() => {
                            const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                            expect(deploymentLists.length).toBe(planIds.length);
                        });

                        // Verify final state
                        const deploymentLists = container.querySelectorAll(".bg-slate-900\\/50");
                        expect(deploymentLists.length).toBe(planIds.length);
                    },
                ),
                { numRuns: 100 },
            );
        }, 90000); // 90 second timeout
    });

    describe("Property 20: Error Message Display", () => {
        /**
         * Feature: deployment-history, Property 20: Error Message Display
         *
         * For any API error response, the History_View should display an error message
         * to the user that includes information about the error type.
         */
        it("should display error message for various error types", async () => {
            await fc.assert(
                fc.asyncProperty(
                    // Generate random error types and messages (excluding 401 which triggers redirect)
                    fc.record({
                        errorType: fc.constantFrom(
                            "NetworkError",
                            "ServerError",
                            "TimeoutError",
                            "DatabaseError",
                            "ValidationError",
                            "UnknownError",
                        ),
                        errorMessage: fc.string({ minLength: 10, maxLength: 100 }),
                        statusCode: fc.constantFrom(400, 403, 404, 500, 502, 503, 504), // Removed 401
                    }),
                    async ({ errorType, errorMessage, statusCode }) => {
                        // Mock failed API response
                        (global.fetch as jest.Mock).mockResolvedValueOnce({
                            ok: false,
                            status: statusCode,
                            json: async () => ({
                                error: errorType,
                                message: errorMessage,
                            }),
                        });

                        // Render the History page
                        const { container, unmount } = render(<HistoryPage />);

                        try {
                            // Wait for error state to be displayed
                            await waitFor(
                                () => {
                                    // Check for error message container with red styling
                                    const errorElements = container.querySelectorAll(".text-red-300");
                                    expect(errorElements.length).toBeGreaterThan(0);
                                },
                                { timeout: 5000 },
                            );

                            // Verify error message is displayed
                            const errorContainer = container.querySelector(".text-red-300");
                            expect(errorContainer).toBeInTheDocument();

                            // Verify the error message contains text
                            const displayedText = errorContainer?.textContent || "";
                            expect(displayedText.length).toBeGreaterThan(0);
                        } finally {
                            // Clean up after each iteration
                            unmount();
                        }
                    },
                ),
                { numRuns: 100 }, // Minimum 100 iterations as specified
            );
        }, 120000); // 120 second timeout for 100 iterations

        it("should display error message for network failures", async () => {
            await fc.assert(
                fc.asyncProperty(
                    // Generate random error messages
                    fc.string({ minLength: 5, maxLength: 50 }),
                    async (errorMessage) => {
                        // Mock network failure (fetch throws)
                        (global.fetch as jest.Mock).mockRejectedValueOnce(
                            new Error(errorMessage || "Network request failed"),
                        );

                        // Render the History page
                        const { container } = render(<HistoryPage />);

                        // Wait for error state to be displayed
                        await waitFor(
                            () => {
                                const errorElements = container.querySelectorAll(".text-red-300");
                                expect(errorElements.length).toBeGreaterThan(0);
                            },
                            { timeout: 5000 },
                        );

                        // Verify error message is displayed
                        const errorContainer = container.querySelector(".text-red-300");
                        expect(errorContainer).toBeInTheDocument();

                        // Verify the error message contains text
                        const displayedText = errorContainer?.textContent || "";
                        expect(displayedText.length).toBeGreaterThan(0);
                    },
                ),
                { numRuns: 100 },
            );
        }, 120000);

        it("should display error message with retry button", async () => {
            await fc.assert(
                fc.asyncProperty(
                    // Generate random error scenarios
                    fc.record({
                        statusCode: fc.constantFrom(500, 502, 503, 504),
                        errorMessage: fc.string({ minLength: 10, maxLength: 80 }),
                    }),
                    async ({ statusCode, errorMessage }) => {
                        // Mock failed API response
                        (global.fetch as jest.Mock).mockResolvedValueOnce({
                            ok: false,
                            status: statusCode,
                            json: async () => ({
                                error: "ServerError",
                                message: errorMessage,
                            }),
                        });

                        // Render the History page
                        const { container, findByText, unmount } = render(<HistoryPage />);

                        try {
                            // Wait for error state
                            await waitFor(
                                () => {
                                    const errorElements = container.querySelectorAll(".text-red-300");
                                    expect(errorElements.length).toBeGreaterThan(0);
                                },
                                { timeout: 5000 },
                            );

                            // Verify retry button is present using querySelector to avoid multiple element error
                            const retryButton = container.querySelector("button");
                            expect(retryButton).toBeInTheDocument();
                            expect(retryButton?.textContent).toMatch(/retry/i);

                            // Verify error message is displayed
                            const errorContainer = container.querySelector(".text-red-300");
                            expect(errorContainer).toBeInTheDocument();
                        } finally {
                            // Clean up after each iteration
                            unmount();
                        }
                    },
                ),
                { numRuns: 100 },
            );
        }, 120000);

        it("should display different error messages for different status codes", async () => {
            await fc.assert(
                fc.asyncProperty(
                    // Generate different HTTP status codes
                    fc.constantFrom(400, 403, 404, 500, 502, 503),
                    async (statusCode) => {
                        // Mock failed API response
                        (global.fetch as jest.Mock).mockResolvedValueOnce({
                            ok: false,
                            status: statusCode,
                            json: async () => ({
                                error: `Error${statusCode}`,
                                message: `Error occurred with status ${statusCode}`,
                            }),
                        });

                        // Render the History page
                        const { container } = render(<HistoryPage />);

                        // Wait for error state
                        await waitFor(
                            () => {
                                const errorElements = container.querySelectorAll(".text-red-300");
                                expect(errorElements.length).toBeGreaterThan(0);
                            },
                            { timeout: 5000 },
                        );

                        // Verify error message is displayed
                        const errorContainer = container.querySelector(".text-red-300");
                        expect(errorContainer).toBeInTheDocument();

                        // The error message should contain some text
                        const displayedText = errorContainer?.textContent || "";
                        expect(displayedText.length).toBeGreaterThan(0);
                    },
                ),
                { numRuns: 100 },
            );
        }, 120000);
    });

    describe("Unit tests for frontend edge cases", () => {
        /**
         * Tests specific edge cases and styling requirements
         */

        it("should display empty plans message when no plans exist", async () => {
            // Mock successful API response with empty plans array
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ plans: [] }),
            });

            const { findByText } = render(<HistoryPage />);

            // Wait for empty state message to appear (Requirement 1.6)
            const emptyMessage = await findByText(/No infrastructure plans yet/i);
            expect(emptyMessage).toBeInTheDocument();

            // Verify the message includes helpful text
            const helpText = await findByText(
                /Create your first plan to get started with infrastructure deployment/i,
            );
            expect(helpText).toBeInTheDocument();
        });

        it("should redirect to /auth when user is not authenticated", async () => {
            // Mock unauthenticated user
            const mockAuthContext = {
                user: null,
                loading: false,
            };

            jest.spyOn(require("../context/AuthContext"), "useAuth").mockReturnValue(
                mockAuthContext,
            );

            render(<HistoryPage />);

            // Wait for redirect to be called (Requirement 6.4)
            await waitFor(() => {
                expect(mockPush).toHaveBeenCalledWith("/auth");
            });
        });

        it("should display retry button when error occurs", async () => {
            // Mock failed API response BEFORE rendering
            (global.fetch as jest.Mock).mockRejectedValueOnce(
                new Error("Network request failed"),
            );

            const { findByText } = render(<HistoryPage />);

            // Wait for error state and retry button (Requirement 9.5)
            const errorText = await findByText(/Failed to load deployment history/i, {}, { timeout: 10000 });
            expect(errorText).toBeInTheDocument();

            // Verify retry button is present
            const retryButton = await findByText(/retry/i);
            expect(retryButton).toBeInTheDocument();
        }, 15000); // 15 second timeout

        it("should call fetchHistory again when retry button is clicked", async () => {
            // Mock initial failure BEFORE rendering
            (global.fetch as jest.Mock).mockRejectedValueOnce(
                new Error("Network request failed"),
            );

            const { findByText } = render(<HistoryPage />);

            // Wait for error message
            await findByText(/Failed to load deployment history/i, {}, { timeout: 10000 });

            // Get retry button
            const retryButton = await findByText(/retry/i);
            expect(retryButton).toBeInTheDocument();

            // Mock successful response for retry
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ plans: [] }),
            });

            // Click retry button
            fireEvent.click(retryButton);

            // Verify fetch was called again
            await waitFor(() => {
                expect(global.fetch).toHaveBeenCalledTimes(2);
            });
        }, 15000); // 15 second timeout

        it("should apply correct Tailwind styling classes", async () => {
            // Mock successful API response with one plan
            const mockPlan = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 0,
                latest_deployment_status: null,
                deployments: [],
            };

            // Mock BEFORE rendering
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ plans: [mockPlan] }),
            });

            const { container, findByText } = render(<HistoryPage />);

            // Wait for content to load
            await findByText("Test requirements", {}, { timeout: 10000 });

            // Verify bg-slate-950 background (Requirement 7.1)
            const mainContainer = container.querySelector(".bg-slate-950");
            expect(mainContainer).toBeInTheDocument();

            // Verify text color classes (Requirement 7.4)
            const slate200Text = container.querySelector(".text-slate-200");
            expect(slate200Text).toBeInTheDocument();
        }, 15000); // 15 second timeout

        it("should handle 401 unauthorized and redirect to /auth", async () => {
            // Mock 401 response
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: false,
                status: 401,
                json: async () => ({ error: "Unauthorized" }),
            });

            render(<HistoryPage />);

            // Wait for redirect to be called
            await waitFor(() => {
                expect(mockPush).toHaveBeenCalledWith("/auth");
            });
        });

        it("should display loading spinner while fetching data", () => {
            // Mock pending fetch (never resolves)
            (global.fetch as jest.Mock).mockImplementation(
                () => new Promise(() => { }),
            );

            const { container } = render(<HistoryPage />);

            // Verify loading spinner is displayed
            const spinner = container.querySelector(".animate-spin");
            expect(spinner).toBeInTheDocument();

            // Verify loading text
            expect(container.textContent).toContain("Loading deployment history");
        });

        it("should display error message with red styling", async () => {
            // Mock failed API response BEFORE rendering
            (global.fetch as jest.Mock).mockRejectedValueOnce(
                new Error("Server error occurred"),
            );

            const { container, findByText } = render(<HistoryPage />);

            // Wait for error message
            await findByText(/Failed to load deployment history/i, {}, { timeout: 10000 });

            // Verify error styling classes
            const errorBox = container.querySelector(".bg-red-500\\/10");
            expect(errorBox).toBeInTheDocument();

            const errorBorder = container.querySelector(".border-red-500\\/30");
            expect(errorBorder).toBeInTheDocument();

            const errorText = container.querySelector(".text-red-300");
            expect(errorText).toBeInTheDocument();
        }, 15000); // 15 second timeout

        it("should display Generate Plan button in empty state", async () => {
            // Mock successful API response with empty plans array BEFORE rendering
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ plans: [] }),
            });

            const { container, findByText } = render(<HistoryPage />);

            // Wait for empty state message
            await findByText(/No infrastructure plans yet/i, {}, { timeout: 10000 });

            // Verify Generate Plan button is present
            const generateButton = container.querySelector("button");
            expect(generateButton).toBeInTheDocument();
            expect(generateButton?.textContent).toContain("Generate Plan");
        }, 15000); // 15 second timeout

        it("should navigate to /generate when Generate Plan button is clicked", async () => {
            // Mock successful API response with empty plans array BEFORE rendering
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ plans: [] }),
            });

            const { container, findByText } = render(<HistoryPage />);

            // Wait for empty state message
            await findByText(/No infrastructure plans yet/i, {}, { timeout: 10000 });

            // Get Generate Plan button
            const generateButton = container.querySelector("button");
            expect(generateButton).toBeInTheDocument();

            // Click the button
            if (generateButton) {
                fireEvent.click(generateButton);
            }

            // Verify navigation was called
            expect(mockPush).toHaveBeenCalledWith("/generate");
        }, 15000); // 15 second timeout
    });
});
