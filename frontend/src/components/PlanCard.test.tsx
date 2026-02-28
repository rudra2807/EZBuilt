/**
 * Property-based tests for PlanCard component
 * Feature: deployment-history
 */

import * as fc from "fast-check";
import { render, fireEvent } from "@testing-library/react";
import { PlanCard } from "./PlanCard";
import { TerraformPlanWithDeployments } from "@/types/deployment";

describe("PlanCard property-based tests", () => {
    describe("Property 2: Requirements Truncation", () => {
        /**
         * Feature: deployment-history, Property 2: Requirements Truncation
         *
         * For any TerraformPlan with requirements text, when rendering the Plan_Card,
         * if the requirements exceed 150 characters, the displayed text should be
         * exactly 150 characters followed by an ellipsis.
         */
        it("should truncate requirements text over 150 characters with ellipsis", () => {
            fc.assert(
                fc.property(
                    // Generate random strings of 0-500 characters
                    fc.string({ minLength: 0, maxLength: 500 }),
                    fc.uuid(), // plan id
                    fc.uuid(), // user id
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }), // created_at
                    (requirements, planId, userId, createdAt) => {
                        // Create a mock plan with the generated requirements
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        // Render the PlanCard component
                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        // Find the requirements text element
                        const requirementsElement = container.querySelector(
                            ".text-slate-200",
                        );
                        expect(requirementsElement).not.toBeNull();

                        const displayedText = requirementsElement?.textContent || "";

                        // Verify truncation behavior
                        if (requirements.length > 150) {
                            // Text should be truncated to 150 characters + "..."
                            expect(displayedText).toBe(requirements.substring(0, 150) + "...");
                            expect(displayedText.length).toBe(153); // 150 + 3 for "..."
                        } else {
                            // Text should be displayed as-is
                            expect(displayedText).toBe(requirements);
                            expect(displayedText.length).toBe(requirements.length);
                        }
                    },
                ),
                { numRuns: 100 }, // Minimum 100 iterations as specified
            );
        });

        it("should preserve text under 150 characters without modification", () => {
            fc.assert(
                fc.property(
                    // Generate strings specifically under 150 characters
                    fc.string({ minLength: 0, maxLength: 150 }),
                    fc.uuid(),
                    fc.uuid(),
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
                    (requirements, planId, userId, createdAt) => {
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const requirementsElement = container.querySelector(
                            ".text-slate-200",
                        );
                        const displayedText = requirementsElement?.textContent || "";

                        // Text should be unchanged
                        expect(displayedText).toBe(requirements);
                        // Should not have ellipsis
                        expect(displayedText).not.toContain("...");
                    },
                ),
                { numRuns: 100 },
            );
        });

        it("should handle exactly 150 characters without truncation", () => {
            fc.assert(
                fc.property(
                    // Generate strings of exactly 150 characters
                    fc
                        .array(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '.split('')), { minLength: 150, maxLength: 150 })
                        .map((chars) => chars.join("")),
                    fc.uuid(),
                    fc.uuid(),
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
                    (requirements, planId, userId, createdAt) => {
                        expect(requirements.length).toBe(150);

                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const requirementsElement = container.querySelector(
                            ".text-slate-200",
                        );
                        const displayedText = requirementsElement?.textContent || "";

                        // Exactly 150 characters should not be truncated
                        expect(displayedText).toBe(requirements);
                        expect(displayedText.length).toBe(150);
                        expect(displayedText).not.toContain("...");
                    },
                ),
                { numRuns: 100 },
            );
        });

        it("should handle exactly 151 characters with truncation", () => {
            fc.assert(
                fc.property(
                    // Generate strings of exactly 151 characters
                    fc
                        .array(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '.split('')), { minLength: 151, maxLength: 151 })
                        .map((chars) => chars.join("")),
                    fc.uuid(),
                    fc.uuid(),
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
                    (requirements, planId, userId, createdAt) => {
                        expect(requirements.length).toBe(151);

                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const requirementsElement = container.querySelector(
                            ".text-slate-200",
                        );
                        const displayedText = requirementsElement?.textContent || "";

                        // 151 characters should be truncated to 150 + "..."
                        expect(displayedText).toBe(requirements.substring(0, 150) + "...");
                        expect(displayedText.length).toBe(153);
                    },
                ),
                { numRuns: 100 },
            );
        });

        it("should handle empty string without errors", () => {
            fc.assert(
                fc.property(
                    fc.uuid(),
                    fc.uuid(),
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
                    (planId, userId, createdAt) => {
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: "",
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const requirementsElement = container.querySelector(
                            ".text-slate-200",
                        );
                        const displayedText = requirementsElement?.textContent || "";

                        // Empty string should remain empty
                        expect(displayedText).toBe("");
                        expect(displayedText).not.toContain("...");
                    },
                ),
                { numRuns: 100 },
            );
        });

        it("should handle special characters and unicode correctly", () => {
            fc.assert(
                fc.property(
                    // Generate strings with various unicode characters
                    fc.string({ minLength: 0, maxLength: 500 }),
                    fc.uuid(),
                    fc.uuid(),
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
                    (requirements, planId, userId, createdAt) => {
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const requirementsElement = container.querySelector(
                            ".text-slate-200",
                        );
                        const displayedText = requirementsElement?.textContent || "";

                        // Verify truncation behavior with unicode
                        if (requirements.length > 150) {
                            expect(displayedText).toBe(requirements.substring(0, 150) + "...");
                        } else {
                            expect(displayedText).toBe(requirements);
                        }
                    },
                ),
                { numRuns: 100 },
            );
        });

        it("should produce consistent results for the same input", () => {
            fc.assert(
                fc.property(
                    fc.string({ minLength: 0, maxLength: 500 }),
                    fc.uuid(),
                    fc.uuid(),
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
                    (requirements, planId, userId, createdAt) => {
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        // Render twice with the same input
                        const { container: container1 } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const { container: container2 } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const text1 =
                            container1.querySelector(".text-slate-200")?.textContent || "";
                        const text2 =
                            container2.querySelector(".text-slate-200")?.textContent || "";

                        // Results should be identical
                        expect(text1).toBe(text2);
                    },
                ),
                { numRuns: 100 },
            );
        });
    });

    describe("Property 3: ISO 8601 Date Formatting", () => {
        /**
         * Feature: deployment-history, Property 3: ISO 8601 Date Formatting
         *
         * For any TerraformPlan with a created_at timestamp, when rendering the Plan_Card,
         * the displayed date should be a valid ISO 8601 formatted string.
         */
        it("should format created_at timestamp as ISO 8601 string", () => {
            fc.assert(
                fc.property(
                    // Generate random valid Date objects
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2030-12-31") }),
                    fc.uuid(), // plan id
                    fc.uuid(), // user id
                    fc.string({ minLength: 10, maxLength: 200 }), // requirements
                    (createdAt, planId, userId, requirements) => {
                        // Create a mock plan with the generated date
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        // Render the PlanCard component
                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        // Find the date element (contains "Created:")
                        const dateElement = container.querySelector(".text-slate-300");
                        expect(dateElement).not.toBeNull();

                        const displayedText = dateElement?.textContent || "";
                        // Extract the date part after "Created: "
                        const dateString = displayedText.replace("Created: ", "");

                        // Verify the date matches ISO 8601 format (YYYY-MM-DD HH:mm:ss)
                        // The component formats as: toISOString().replace('T', ' ').substring(0, 19)
                        const iso8601Pattern = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
                        expect(dateString).toMatch(iso8601Pattern);

                        // Verify the date can be parsed back to a valid Date
                        const parsedDate = new Date(dateString.replace(" ", "T") + "Z");
                        expect(parsedDate).toBeInstanceOf(Date);
                        expect(isNaN(parsedDate.getTime())).toBe(false);

                        // Verify the formatted date matches the original date (within same second)
                        const originalDate = new Date(createdAt);
                        expect(parsedDate.getUTCFullYear()).toBe(originalDate.getUTCFullYear());
                        expect(parsedDate.getUTCMonth()).toBe(originalDate.getUTCMonth());
                        expect(parsedDate.getUTCDate()).toBe(originalDate.getUTCDate());
                        expect(parsedDate.getUTCHours()).toBe(originalDate.getUTCHours());
                        expect(parsedDate.getUTCMinutes()).toBe(originalDate.getUTCMinutes());
                        expect(parsedDate.getUTCSeconds()).toBe(originalDate.getUTCSeconds());
                    },
                ),
                { numRuns: 100 }, // Minimum 100 iterations as specified
            );
        });

        it("should produce consistent date format for the same timestamp", () => {
            fc.assert(
                fc.property(
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2030-12-31") }),
                    fc.uuid(),
                    fc.uuid(),
                    fc.string({ minLength: 10, maxLength: 200 }),
                    (createdAt, planId, userId, requirements) => {
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        // Render twice with the same input
                        const { container: container1 } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const { container: container2 } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const date1 = container1.querySelector(".text-slate-300")?.textContent || "";
                        const date2 = container2.querySelector(".text-slate-300")?.textContent || "";

                        // Results should be identical
                        expect(date1).toBe(date2);
                    },
                ),
                { numRuns: 100 },
            );
        });

        it("should handle edge case dates correctly", () => {
            fc.assert(
                fc.property(
                    // Generate dates at boundaries (start of year, end of year, leap years, etc.)
                    fc.oneof(
                        fc.constant(new Date("2020-01-01T00:00:00Z")), // Start of year
                        fc.constant(new Date("2020-12-31T23:59:59Z")), // End of year
                        fc.constant(new Date("2020-02-29T12:00:00Z")), // Leap year
                        fc.constant(new Date("2021-02-28T12:00:00Z")), // Non-leap year
                        fc.constant(new Date("2024-06-15T12:30:45Z")), // Mid-year
                        fc.date({ min: new Date("2020-01-01"), max: new Date("2030-12-31") }),
                    ),
                    fc.uuid(),
                    fc.uuid(),
                    fc.string({ minLength: 10, maxLength: 200 }),
                    (createdAt, planId, userId, requirements) => {
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const dateElement = container.querySelector(".text-slate-300");
                        const displayedText = dateElement?.textContent || "";
                        const dateString = displayedText.replace("Created: ", "");

                        // Verify ISO 8601 format
                        const iso8601Pattern = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
                        expect(dateString).toMatch(iso8601Pattern);

                        // Verify date components are valid
                        const [datePart, timePart] = dateString.split(" ");
                        const [year, month, day] = datePart.split("-").map(Number);
                        const [hours, minutes, seconds] = timePart.split(":").map(Number);

                        expect(year).toBeGreaterThanOrEqual(2020);
                        expect(year).toBeLessThanOrEqual(2030);
                        expect(month).toBeGreaterThanOrEqual(1);
                        expect(month).toBeLessThanOrEqual(12);
                        expect(day).toBeGreaterThanOrEqual(1);
                        expect(day).toBeLessThanOrEqual(31);
                        expect(hours).toBeGreaterThanOrEqual(0);
                        expect(hours).toBeLessThanOrEqual(23);
                        expect(minutes).toBeGreaterThanOrEqual(0);
                        expect(minutes).toBeLessThanOrEqual(59);
                        expect(seconds).toBeGreaterThanOrEqual(0);
                        expect(seconds).toBeLessThanOrEqual(59);
                    },
                ),
                { numRuns: 100 },
            );
        });

        it("should format date with proper zero-padding", () => {
            fc.assert(
                fc.property(
                    fc.date({ min: new Date("2020-01-01"), max: new Date("2030-12-31") }),
                    fc.uuid(),
                    fc.uuid(),
                    fc.string({ minLength: 10, maxLength: 200 }),
                    (createdAt, planId, userId, requirements) => {
                        const mockPlan: TerraformPlanWithDeployments = {
                            id: planId,
                            user_id: userId,
                            original_requirements: requirements,
                            created_at: createdAt.toISOString(),
                            deployment_count: 0,
                            latest_deployment_status: null,
                            deployments: [],
                        };

                        const { container } = render(
                            <PlanCard
                                plan={mockPlan}
                                isExpanded={false}
                                onToggle={() => { }}
                            />,
                        );

                        const dateElement = container.querySelector(".text-slate-300");
                        const displayedText = dateElement?.textContent || "";
                        const dateString = displayedText.replace("Created: ", "");

                        // Verify all components are zero-padded to 2 digits (except year which is 4)
                        const [datePart, timePart] = dateString.split(" ");
                        const [year, month, day] = datePart.split("-");
                        const [hours, minutes, seconds] = timePart.split(":");

                        expect(year.length).toBe(4);
                        expect(month.length).toBe(2);
                        expect(day.length).toBe(2);
                        expect(hours.length).toBe(2);
                        expect(minutes.length).toBe(2);
                        expect(seconds.length).toBe(2);
                    },
                ),
                { numRuns: 100 },
            );
        });
    });

    describe("Unit tests for PlanCard edge cases", () => {
        /**
         * Tests specific edge cases and styling requirements
         */

        it("should display '0 deployments' for plans with no deployments", () => {
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 0,
                latest_deployment_status: null,
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={false} onToggle={() => { }} />,
            );

            // Verify "0 deployments" text is displayed (Requirement 8.1)
            expect(container.textContent).toContain("0 deployments");
        });

        it("should display '1 deployment' (singular) for plans with one deployment", () => {
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 1,
                latest_deployment_status: "success",
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={false} onToggle={() => { }} />,
            );

            // Verify singular form is used
            expect(container.textContent).toContain("1 deployment");
            expect(container.textContent).not.toContain("1 deployments");
        });

        it("should display 'Not Deployed' status badge for plans with no deployments", () => {
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 0,
                latest_deployment_status: null,
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={false} onToggle={() => { }} />,
            );

            // Verify "Not Deployed" badge is displayed (Requirement 8.3)
            expect(container.textContent).toContain("Not Deployed");

            // Verify it has the correct styling
            const notDeployedBadge = container.querySelector(".border-slate-600\\/70");
            expect(notDeployedBadge).toBeInTheDocument();
        });

        it("should apply correct Tailwind styling classes", () => {
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 0,
                latest_deployment_status: null,
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={false} onToggle={() => { }} />,
            );

            // Verify bg-slate-900/80 background (Requirement 7.2)
            const card = container.querySelector(".bg-slate-900\\/80");
            expect(card).toBeInTheDocument();

            // Verify border-slate-800 border (Requirement 7.2)
            const border = container.querySelector(".border-slate-800");
            expect(border).toBeInTheDocument();

            // Verify rounded-3xl border radius (Requirement 7.3)
            const rounded = container.querySelector(".rounded-3xl");
            expect(rounded).toBeInTheDocument();

            // Verify hover effect class
            const hover = container.querySelector(".hover\\:border-slate-700");
            expect(hover).toBeInTheDocument();

            // Verify cursor-pointer class
            const cursor = container.querySelector(".cursor-pointer");
            expect(cursor).toBeInTheDocument();
        });

        it("should display expand indicator (▶) when not expanded", () => {
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 0,
                latest_deployment_status: null,
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={false} onToggle={() => { }} />,
            );

            // Verify expand indicator is displayed
            expect(container.textContent).toContain("▶");
            expect(container.textContent).not.toContain("▼");
        });

        it("should display collapse indicator (▼) when expanded", () => {
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 0,
                latest_deployment_status: null,
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={true} onToggle={() => { }} />,
            );

            // Verify collapse indicator is displayed
            expect(container.textContent).toContain("▼");
            expect(container.textContent).not.toContain("▶");
        });

        it("should call onToggle when card is clicked", () => {
            const mockOnToggle = jest.fn();
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 0,
                latest_deployment_status: null,
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={false} onToggle={mockOnToggle} />,
            );

            // Click the card
            const card = container.querySelector(".cursor-pointer");
            expect(card).not.toBeNull();
            if (card) {
                fireEvent.click(card);
            }

            // Verify onToggle was called
            expect(mockOnToggle).toHaveBeenCalledTimes(1);
        });

        it("should display StatusBadge when plan has deployments", () => {
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: new Date().toISOString(),
                deployment_count: 1,
                latest_deployment_status: "success",
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={false} onToggle={() => { }} />,
            );

            // Verify StatusBadge is displayed (not "Not Deployed")
            expect(container.textContent).toContain("Success");
            expect(container.textContent).not.toContain("Not Deployed");
        });

        it("should format date correctly in ISO 8601 format", () => {
            const testDate = new Date("2024-06-15T14:30:45.000Z");
            const mockPlan: TerraformPlanWithDeployments = {
                id: "test-plan-id",
                user_id: "test-user-id",
                original_requirements: "Test requirements",
                created_at: testDate.toISOString(),
                deployment_count: 0,
                latest_deployment_status: null,
                deployments: [],
            };

            const { container } = render(
                <PlanCard plan={mockPlan} isExpanded={false} onToggle={() => { }} />,
            );

            // Verify date is formatted as YYYY-MM-DD HH:mm:ss
            expect(container.textContent).toContain("2024-06-15 14:30:45");
        });
    });
});
