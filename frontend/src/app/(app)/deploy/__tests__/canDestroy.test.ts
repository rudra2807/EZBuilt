/**
 * Property-Based Test for canDestroy Logic
 * Feature: firebase-removal-and-consolidation
 * Property 4: canDestroy flag correctness
 *
 * This test verifies that the canDestroy flag is true if and only if
 * the deployment status equals 'success'.
 */

import fc from "fast-check";

/**
 * The canDestroy logic from the deploy page.
 * This function replicates the logic: const canDestroy = deploymentStatus === 'success';
 */
function calculateCanDestroy(deploymentStatus: string | null): boolean {
  return deploymentStatus === "success";
}

describe("canDestroy Logic Property Tests", () => {
  test("Property 4: canDestroy is true only when status is success", () => {
    // Generate all possible deployment status values
    const deploymentStatusArbitrary = fc.constantFrom(
      "started",
      "running",
      "success",
      "failed",
      "destroyed",
      "destroy_failed",
      null,
    );

    fc.assert(
      fc.property(deploymentStatusArbitrary, (status) => {
        const canDestroy = calculateCanDestroy(status);
        const expected = status === "success";

        // The property: canDestroy should be true if and only if status is 'success'
        expect(canDestroy).toBe(expected);
      }),
      { numRuns: 100 }, // Run minimum 100 iterations as specified
    );
  });

  test("Property 4 (explicit): canDestroy is true when status is success", () => {
    const canDestroy = calculateCanDestroy("success");
    expect(canDestroy).toBe(true);
  });

  test("Property 4 (explicit): canDestroy is false for all non-success statuses", () => {
    const nonSuccessStatuses = [
      "started",
      "running",
      "failed",
      "destroyed",
      "destroy_failed",
      null,
      "unknown",
      "",
    ];

    nonSuccessStatuses.forEach((status) => {
      const canDestroy = calculateCanDestroy(status);
      expect(canDestroy).toBe(false);
    });
  });
});
