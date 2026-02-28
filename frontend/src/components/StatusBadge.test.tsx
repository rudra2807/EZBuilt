/**
 * Property-based tests for StatusBadge component
 * Feature: deployment-history
 */

import * as fc from "fast-check";
import { render } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

type DeploymentStatus =
    | "started"
    | "running"
    | "success"
    | "failed"
    | "destroyed"
    | "destroy_failed";

describe("StatusBadge property-based tests", () => {
    describe("Property 12: Status Badge Color Mapping", () => {
        /**
         * Feature: deployment-history, Property 12: Status Badge Color Mapping
         *
         * For any Deployment status, the Status_Badge should display the correct color coding:
         * - emerald for "success"
         * - red for "failed" or "destroy_failed"
         * - amber for "running" or "started"
         * - slate for "destroyed"
         */
        it("should map all deployment statuses to correct CSS color classes", () => {
            // Define the expected color mappings based on design document
            const expectedColorMappings: Record<
                DeploymentStatus,
                { color: string; classes: string[] }
            > = {
                success: {
                    color: "emerald",
                    classes: ["border-emerald-500/70", "bg-emerald-500/10", "text-emerald-100"],
                },
                failed: {
                    color: "red",
                    classes: ["border-red-500/70", "bg-red-500/10", "text-red-100"],
                },
                destroy_failed: {
                    color: "red",
                    classes: ["border-red-500/70", "bg-red-500/10", "text-red-100"],
                },
                running: {
                    color: "amber",
                    classes: ["border-amber-500/70", "bg-amber-500/10", "text-amber-100"],
                },
                started: {
                    color: "amber",
                    classes: ["border-amber-500/70", "bg-amber-500/10", "text-amber-100"],
                },
                destroyed: {
                    color: "slate",
                    classes: ["border-slate-600/70", "bg-slate-600/10", "text-slate-300"],
                },
            };

            fc.assert(
                fc.property(
                    // Generate all possible DeploymentStatus enum values
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        // Render the StatusBadge with the generated status
                        const { container } = render(<StatusBadge status={status} />);

                        // Get the rendered span element
                        const badge = container.querySelector("span");
                        expect(badge).not.toBeNull();

                        if (badge) {
                            const classList = Array.from(badge.classList);

                            // Get expected classes for this status
                            const expectedClasses = expectedColorMappings[status].classes;

                            // Verify all expected color classes are present
                            expectedClasses.forEach((expectedClass) => {
                                expect(classList).toContain(expectedClass);
                            });

                            // Verify the color mapping is correct based on status
                            const expectedColor = expectedColorMappings[status].color;
                            const hasCorrectColorClasses = expectedClasses.every((cls) =>
                                classList.includes(cls)
                            );

                            expect(hasCorrectColorClasses).toBe(true);

                            // Additional verification: ensure the color is in the class list
                            const colorInClasses = classList.some((cls) =>
                                cls.includes(expectedColor)
                            );
                            expect(colorInClasses).toBe(true);
                        }
                    }
                ),
                { numRuns: 100 } // Minimum 100 iterations as specified
            );
        });

        it("should consistently apply the same color classes for the same status", () => {
            fc.assert(
                fc.property(
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        // Render the same status multiple times
                        const { container: container1 } = render(
                            <StatusBadge status={status} />
                        );
                        const { container: container2 } = render(
                            <StatusBadge status={status} />
                        );

                        const badge1 = container1.querySelector("span");
                        const badge2 = container2.querySelector("span");

                        expect(badge1).not.toBeNull();
                        expect(badge2).not.toBeNull();

                        if (badge1 && badge2) {
                            const classList1 = Array.from(badge1.classList).sort();
                            const classList2 = Array.from(badge2.classList).sort();

                            // Classes should be identical for the same status
                            expect(classList1).toEqual(classList2);
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });

        it("should apply emerald color only to success status", () => {
            fc.assert(
                fc.property(
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        const { container } = render(<StatusBadge status={status} />);
                        const badge = container.querySelector("span");

                        expect(badge).not.toBeNull();

                        if (badge) {
                            const classList = Array.from(badge.classList);
                            const hasEmeraldClasses = classList.some((cls) =>
                                cls.includes("emerald")
                            );

                            // Only success status should have emerald classes
                            if (status === "success") {
                                expect(hasEmeraldClasses).toBe(true);
                            } else {
                                expect(hasEmeraldClasses).toBe(false);
                            }
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });

        it("should apply red color only to failed and destroy_failed statuses", () => {
            fc.assert(
                fc.property(
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        const { container } = render(<StatusBadge status={status} />);
                        const badge = container.querySelector("span");

                        expect(badge).not.toBeNull();

                        if (badge) {
                            const classList = Array.from(badge.classList);
                            const hasRedClasses = classList.some((cls) => cls.includes("red"));

                            // Only failed and destroy_failed statuses should have red classes
                            if (status === "failed" || status === "destroy_failed") {
                                expect(hasRedClasses).toBe(true);
                            } else {
                                expect(hasRedClasses).toBe(false);
                            }
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });

        it("should apply amber color only to running and started statuses", () => {
            fc.assert(
                fc.property(
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        const { container } = render(<StatusBadge status={status} />);
                        const badge = container.querySelector("span");

                        expect(badge).not.toBeNull();

                        if (badge) {
                            const classList = Array.from(badge.classList);
                            const hasAmberClasses = classList.some((cls) =>
                                cls.includes("amber")
                            );

                            // Only running and started statuses should have amber classes
                            if (status === "running" || status === "started") {
                                expect(hasAmberClasses).toBe(true);
                            } else {
                                expect(hasAmberClasses).toBe(false);
                            }
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });

        it("should apply slate color only to destroyed status", () => {
            fc.assert(
                fc.property(
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        const { container } = render(<StatusBadge status={status} />);
                        const badge = container.querySelector("span");

                        expect(badge).not.toBeNull();

                        if (badge) {
                            const classList = Array.from(badge.classList);
                            const hasSlateClasses = classList.some((cls) =>
                                cls.includes("slate")
                            );

                            // Only destroyed status should have slate classes
                            if (status === "destroyed") {
                                expect(hasSlateClasses).toBe(true);
                            } else {
                                expect(hasSlateClasses).toBe(false);
                            }
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });

        it("should include all three color class types (border, background, text) for each status", () => {
            fc.assert(
                fc.property(
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        const { container } = render(<StatusBadge status={status} />);
                        const badge = container.querySelector("span");

                        expect(badge).not.toBeNull();

                        if (badge) {
                            const classList = Array.from(badge.classList);

                            // Each status should have border, background, and text color classes
                            const hasBorderClass = classList.some((cls) =>
                                cls.startsWith("border-")
                            );
                            const hasBackgroundClass = classList.some((cls) =>
                                cls.startsWith("bg-")
                            );
                            const hasTextClass = classList.some((cls) =>
                                cls.startsWith("text-")
                            );

                            expect(hasBorderClass).toBe(true);
                            expect(hasBackgroundClass).toBe(true);
                            expect(hasTextClass).toBe(true);
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });
    });

    describe("Property 13: Status Badge Icon Presence", () => {
        /**
         * Feature: deployment-history, Property 13: Status Badge Icon Presence
         *
         * For any Deployment status, the Status_Badge should include an icon element
         * corresponding to that status.
         */
        it("should include an icon element for all deployment statuses", () => {
            fc.assert(
                fc.property(
                    // Generate all possible DeploymentStatus enum values
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        // Render the StatusBadge with the generated status
                        const { container } = render(<StatusBadge status={status} />);

                        // Get the rendered badge element
                        const badge = container.querySelector("span");
                        expect(badge).not.toBeNull();

                        if (badge) {
                            // The badge should have child elements (icon + label)
                            const children = badge.querySelectorAll("span");
                            expect(children.length).toBeGreaterThanOrEqual(2);

                            // The first child span should contain the icon
                            const iconElement = children[0];
                            expect(iconElement).not.toBeNull();
                            expect(iconElement.textContent).not.toBe("");

                            // Verify the icon element has the "leading-none" class
                            expect(iconElement.classList.contains("leading-none")).toBe(true);

                            // Verify the icon is one of the expected icons
                            const expectedIcons = ["✓", "✕", "⟳", "○"];
                            const iconText = iconElement.textContent || "";
                            expect(expectedIcons).toContain(iconText);
                        }
                    }
                ),
                { numRuns: 100 } // Minimum 100 iterations as specified
            );
        });

        it("should have different icons for different status categories", () => {
            fc.assert(
                fc.property(
                    fc.constantFrom<DeploymentStatus>(
                        "started",
                        "running",
                        "success",
                        "failed",
                        "destroyed",
                        "destroy_failed"
                    ),
                    (status) => {
                        const { container } = render(<StatusBadge status={status} />);
                        const badge = container.querySelector("span");

                        expect(badge).not.toBeNull();

                        if (badge) {
                            const iconElement = badge.querySelector("span.leading-none");
                            expect(iconElement).not.toBeNull();

                            if (iconElement) {
                                const iconText = iconElement.textContent || "";

                                // Verify icon matches expected icon for status
                                if (status === "success") {
                                    expect(iconText).toBe("✓");
                                } else if (status === "failed" || status === "destroy_failed") {
                                    expect(iconText).toBe("✕");
                                } else if (status === "running" || status === "started") {
                                    expect(iconText).toBe("⟳");
                                } else if (status === "destroyed") {
                                    expect(iconText).toBe("○");
                                }
                            }
                        }
                    }
                ),
                { numRuns: 100 }
            );
        });
    });
});

describe("StatusBadge unit tests", () => {
    describe("Status text humanization", () => {
        /**
         * Tests that status enum values are properly humanized for display
         */
        it('should display "Destroy Failed" for destroy_failed status', () => {
            const { container } = render(<StatusBadge status="destroy_failed" />);
            expect(container.textContent).toContain("Destroy Failed");
        });

        it('should display "Success" for success status', () => {
            const { container } = render(<StatusBadge status="success" />);
            expect(container.textContent).toContain("Success");
        });

        it('should display "Failed" for failed status', () => {
            const { container } = render(<StatusBadge status="failed" />);
            expect(container.textContent).toContain("Failed");
        });

        it('should display "Running" for running status', () => {
            const { container } = render(<StatusBadge status="running" />);
            expect(container.textContent).toContain("Running");
        });

        it('should display "Started" for started status', () => {
            const { container } = render(<StatusBadge status="started" />);
            expect(container.textContent).toContain("Started");
        });

        it('should display "Destroyed" for destroyed status', () => {
            const { container } = render(<StatusBadge status="destroyed" />);
            expect(container.textContent).toContain("Destroyed");
        });

        it("should have human-readable labels for all status values", () => {
            const statuses: DeploymentStatus[] = [
                "success",
                "failed",
                "destroy_failed",
                "running",
                "started",
                "destroyed",
            ];

            const expectedLabels: Record<DeploymentStatus, string> = {
                success: "Success",
                failed: "Failed",
                destroy_failed: "Destroy Failed",
                running: "Running",
                started: "Started",
                destroyed: "Destroyed",
            };

            statuses.forEach((status) => {
                const { container } = render(<StatusBadge status={status} />);
                const expectedLabel = expectedLabels[status];
                expect(container.textContent).toContain(expectedLabel);
            });
        });
    });
});
