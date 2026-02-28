/**
 * Property-based tests for time utility functions
 * Feature: deployment-history
 */

import * as fc from "fast-check";
import {
  formatRelativeTime,
  calculateDuration,
  calculateElapsedTime,
} from "./timeUtils";

describe("timeUtils property-based tests", () => {
  describe("Property 15: Relative Time Formatting", () => {
    /**
     * Feature: deployment-history, Property 15: Relative Time Formatting
     *
     * For any Deployment with a created_at timestamp, the displayed time should be
     * in relative format (e.g., "X minutes ago", "X hours ago", "X days ago").
     */
    it("should format timestamps from 1 second to 30 days ago with correct pattern", () => {
      fc.assert(
        fc.property(
          // Generate random timestamps from 1 second to 30 days ago
          fc.integer({ min: 1, max: 30 * 24 * 60 * 60 }), // 1 second to 30 days in seconds
          (secondsAgo) => {
            // Create a timestamp in the past
            const now = new Date();
            const pastTimestamp = new Date(now.getTime() - secondsAgo * 1000);
            const isoTimestamp = pastTimestamp.toISOString();

            // Format the relative time
            const result = formatRelativeTime(isoTimestamp);

            // Verify output matches expected pattern
            const validPatterns = [
              /^\d+ seconds? ago$/,
              /^\d+ minutes? ago$/,
              /^\d+ hours? ago$/,
              /^\d+ days? ago$/,
              /^\d+ weeks? ago$/,
            ];

            const matchesPattern = validPatterns.some((pattern) =>
              pattern.test(result),
            );

            // Assert the result matches one of the valid patterns
            expect(matchesPattern).toBe(true);

            // Additional validation: verify the time unit is appropriate for the duration
            if (secondsAgo < 60) {
              expect(result).toMatch(/^\d+ seconds? ago$/);
            } else if (secondsAgo < 60 * 60) {
              expect(result).toMatch(/^\d+ minutes? ago$/);
            } else if (secondsAgo < 24 * 60 * 60) {
              expect(result).toMatch(/^\d+ hours? ago$/);
            } else if (secondsAgo < 7 * 24 * 60 * 60) {
              expect(result).toMatch(/^\d+ days? ago$/);
            } else {
              expect(result).toMatch(/^\d+ weeks? ago$/);
            }
          },
        ),
        { numRuns: 100 }, // Minimum 100 iterations as specified
      );
    });

    it("should handle singular and plural forms correctly", () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 30 * 24 * 60 * 60 }),
          (secondsAgo) => {
            const now = new Date();
            const pastTimestamp = new Date(now.getTime() - secondsAgo * 1000);
            const result = formatRelativeTime(pastTimestamp.toISOString());

            // Extract the number from the result
            const match = result.match(/^(\d+) (\w+) ago$/);
            expect(match).not.toBeNull();

            if (match) {
              const [, numStr, unit] = match;
              const num = parseInt(numStr, 10);

              // Verify singular/plural agreement
              if (num === 1) {
                expect(unit).toMatch(/^(second|minute|hour|day|week)$/);
              } else {
                expect(unit).toMatch(/^(seconds|minutes|hours|days|weeks)$/);
              }
            }
          },
        ),
        { numRuns: 100 },
      );
    });

    it("should produce consistent results for the same timestamp", () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 30 * 24 * 60 * 60 }),
          (secondsAgo) => {
            const now = new Date();
            const pastTimestamp = new Date(now.getTime() - secondsAgo * 1000);
            const isoTimestamp = pastTimestamp.toISOString();

            // Call the function multiple times with the same input
            const result1 = formatRelativeTime(isoTimestamp);
            const result2 = formatRelativeTime(isoTimestamp);

            // Results should be identical (within the same test execution)
            expect(result1).toBe(result2);
          },
        ),
        { numRuns: 100 },
      );
    });
  });

  describe("Property 16: Duration Calculation for Completed Deployments", () => {
    /**
     * Feature: deployment-history, Property 16: Duration Calculation for Completed Deployments
     *
     * For any Deployment with status "success", "destroyed", "failed", or "destroy_failed",
     * the calculated duration should equal the time difference between created_at and
     * completed_at (or updated_at if completed_at is null).
     */
    it("should calculate duration as exact time difference in seconds", () => {
      fc.assert(
        fc.property(
          // Generate random timestamp pairs (created_at, completed_at)
          fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
          fc.integer({ min: 1, max: 24 * 60 * 60 }), // Duration from 1 second to 24 hours
          (createdDate, durationSeconds) => {
            // Create completed timestamp by adding duration to created
            const completedDate = new Date(
              createdDate.getTime() + durationSeconds * 1000,
            );

            const createdIso = createdDate.toISOString();
            const completedIso = completedDate.toISOString();

            // Calculate duration using the function
            const result = calculateDuration(createdIso, completedIso);

            // Parse the result to extract total seconds
            const parseDuration = (durationStr: string): number => {
              let totalSecs = 0;
              const hourMatch = durationStr.match(/(\d+)h/);
              const minuteMatch = durationStr.match(/(\d+)m/);
              const secondMatch = durationStr.match(/(\d+)s/);

              if (hourMatch) totalSecs += parseInt(hourMatch[1], 10) * 3600;
              if (minuteMatch) totalSecs += parseInt(minuteMatch[1], 10) * 60;
              if (secondMatch) totalSecs += parseInt(secondMatch[1], 10);

              return totalSecs;
            };

            const calculatedSeconds = parseDuration(result);

            // Verify calculated duration equals the actual time difference
            expect(calculatedSeconds).toBe(durationSeconds);
          },
        ),
        { numRuns: 100 }, // Minimum 100 iterations as specified
      );
    });

    it("should handle very short durations (less than 1 minute)", () => {
      fc.assert(
        fc.property(
          fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
          fc.integer({ min: 1, max: 59 }), // 1-59 seconds
          (createdDate, durationSeconds) => {
            const completedDate = new Date(
              createdDate.getTime() + durationSeconds * 1000,
            );

            const result = calculateDuration(
              createdDate.toISOString(),
              completedDate.toISOString(),
            );

            // For durations under 60 seconds, format should be "Xs"
            expect(result).toBe(`${durationSeconds}s`);
          },
        ),
        { numRuns: 100 },
      );
    });

    it("should handle durations with hours, minutes, and seconds", () => {
      fc.assert(
        fc.property(
          fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
          fc.integer({ min: 1, max: 23 }), // hours
          fc.integer({ min: 0, max: 59 }), // minutes
          fc.integer({ min: 0, max: 59 }), // seconds
          (createdDate, hours, minutes, seconds) => {
            const totalSeconds = hours * 3600 + minutes * 60 + seconds;
            const completedDate = new Date(
              createdDate.getTime() + totalSeconds * 1000,
            );

            const result = calculateDuration(
              createdDate.toISOString(),
              completedDate.toISOString(),
            );

            // Verify the result contains the correct components
            if (hours > 0) {
              expect(result).toContain(`${hours}h`);
              expect(result).toContain(`${minutes}m`);
              if (seconds > 0) {
                expect(result).toContain(`${seconds}s`);
              }
            } else if (minutes > 0) {
              expect(result).toContain(`${minutes}m`);
              if (seconds > 0) {
                expect(result).toContain(`${seconds}s`);
              }
            } else {
              expect(result).toBe(`${seconds}s`);
            }
          },
        ),
        { numRuns: 100 },
      );
    });

    it("should handle completed timestamp before created timestamp (edge case)", () => {
      fc.assert(
        fc.property(
          fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
          fc.integer({ min: 1, max: 3600 }),
          (completedDate, secondsBefore) => {
            // Create a scenario where completed is before created (invalid but should handle gracefully)
            const createdDate = new Date(
              completedDate.getTime() + secondsBefore * 1000,
            );

            const result = calculateDuration(
              createdDate.toISOString(),
              completedDate.toISOString(),
            );

            // The function should handle negative durations
            // (implementation may vary, but should not crash)
            expect(result).toBeDefined();
            expect(typeof result).toBe("string");
          },
        ),
        { numRuns: 100 },
      );
    });

    it("should produce consistent results for the same timestamp pair", () => {
      fc.assert(
        fc.property(
          fc.date({ min: new Date("2020-01-01"), max: new Date("2025-12-31") }),
          fc.integer({ min: 1, max: 24 * 60 * 60 }),
          (createdDate, durationSeconds) => {
            const completedDate = new Date(
              createdDate.getTime() + durationSeconds * 1000,
            );

            const createdIso = createdDate.toISOString();
            const completedIso = completedDate.toISOString();

            // Call the function multiple times with the same input
            const result1 = calculateDuration(createdIso, completedIso);
            const result2 = calculateDuration(createdIso, completedIso);

            // Results should be identical
            expect(result1).toBe(result2);
          },
        ),
        { numRuns: 100 },
      );
    });
  });
});

describe("Property 17: Duration Formatting", () => {
  /**
   * Feature: deployment-history, Property 17: Duration Formatting
   *
   * For any calculated duration, the displayed format should be human-readable
   * using appropriate units (e.g., "5m 23s", "1h 15m", "45s").
   */
  it("should format durations from 1 second to 24 hours with appropriate units", () => {
    fc.assert(
      fc.property(
        // Generate random durations from 1 second to 24 hours
        fc.integer({ min: 1, max: 24 * 60 * 60 }), // 1 second to 24 hours in seconds
        (durationSeconds) => {
          // Create timestamp pair with the specified duration
          const createdDate = new Date("2024-01-01T00:00:00Z");
          const completedDate = new Date(
            createdDate.getTime() + durationSeconds * 1000,
          );

          const result = calculateDuration(
            createdDate.toISOString(),
            completedDate.toISOString(),
          );

          // Verify output contains appropriate units
          const validPattern = /^(\d+h\s\d+m(\s\d+s)?|\d+m(\s\d+s)?|\d+s)$/;
          expect(result.trim()).toMatch(validPattern);

          // Parse the result to verify correctness
          const hours = Math.floor(durationSeconds / 3600);
          const minutes = Math.floor((durationSeconds % 3600) / 60);
          const seconds = durationSeconds % 60;

          // Verify the values match expected calculation
          if (hours > 0) {
            expect(result).toContain(`${hours}h`);
            expect(result).toContain(`${minutes}m`);
            if (seconds > 0) {
              expect(result).toContain(`${seconds}s`);
            }
          } else if (minutes > 0) {
            expect(result).toContain(`${minutes}m`);
            if (seconds > 0) {
              expect(result).toContain(`${seconds}s`);
            }
          } else {
            expect(result).toBe(`${seconds}s`);
          }
        },
      ),
      { numRuns: 100 }, // Minimum 100 iterations as specified
    );
  });

  it("should format seconds-only durations correctly", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 59 }), // 1-59 seconds
        (seconds) => {
          const createdDate = new Date("2024-01-01T00:00:00Z");
          const completedDate = new Date(
            createdDate.getTime() + seconds * 1000,
          );

          const result = calculateDuration(
            createdDate.toISOString(),
            completedDate.toISOString(),
          );

          // Should be in format "Xs"
          expect(result).toBe(`${seconds}s`);
          expect(result).not.toContain("m");
          expect(result).not.toContain("h");
        },
      ),
      { numRuns: 100 },
    );
  });

  it("should format minutes and seconds durations correctly", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 59 }), // minutes
        fc.integer({ min: 0, max: 59 }), // seconds
        (minutes, seconds) => {
          const totalSeconds = minutes * 60 + seconds;
          const createdDate = new Date("2024-01-01T00:00:00Z");
          const completedDate = new Date(
            createdDate.getTime() + totalSeconds * 1000,
          );

          const result = calculateDuration(
            createdDate.toISOString(),
            completedDate.toISOString(),
          );

          // Should contain minutes
          expect(result).toContain(`${minutes}m`);
          expect(result).not.toContain("h");

          // Should contain seconds if non-zero
          if (seconds > 0) {
            expect(result).toContain(`${seconds}s`);
          } else {
            expect(result).not.toContain("s");
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("should format hours, minutes, and seconds durations correctly", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 24 }), // hours
        fc.integer({ min: 0, max: 59 }), // minutes
        fc.integer({ min: 0, max: 59 }), // seconds
        (hours, minutes, seconds) => {
          const totalSeconds = hours * 3600 + minutes * 60 + seconds;
          const createdDate = new Date("2024-01-01T00:00:00Z");
          const completedDate = new Date(
            createdDate.getTime() + totalSeconds * 1000,
          );

          const result = calculateDuration(
            createdDate.toISOString(),
            completedDate.toISOString(),
          );

          // Should contain hours and minutes
          expect(result).toContain(`${hours}h`);
          expect(result).toContain(`${minutes}m`);

          // Should contain seconds if non-zero
          if (seconds > 0) {
            expect(result).toContain(`${seconds}s`);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("should not include leading zeros or empty units", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 24 * 60 * 60 }),
        (durationSeconds) => {
          const createdDate = new Date("2024-01-01T00:00:00Z");
          const completedDate = new Date(
            createdDate.getTime() + durationSeconds * 1000,
          );

          const result = calculateDuration(
            createdDate.toISOString(),
            completedDate.toISOString(),
          );

          // Should not have leading zeros
          expect(result).not.toMatch(/\b0+\d/);

          // Should not have "0h " or " 0m " as components (with spaces to avoid false positives)
          expect(result).not.toMatch(/\b0h\s/);
          expect(result).not.toMatch(/\s0m\s/);
          expect(result).not.toMatch(/\s0s\b/);

          // Should not be empty
          expect(result.length).toBeGreaterThan(0);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("should use consistent spacing between units", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 3600, max: 24 * 60 * 60 }), // At least 1 hour
        (durationSeconds) => {
          const createdDate = new Date("2024-01-01T00:00:00Z");
          const completedDate = new Date(
            createdDate.getTime() + durationSeconds * 1000,
          );

          const result = calculateDuration(
            createdDate.toISOString(),
            completedDate.toISOString(),
          );

          // If multiple units are present, they should be separated by a single space
          if (result.includes("h") && result.includes("m")) {
            expect(result).toMatch(/\d+h \d+m/);
          }
          if (result.includes("m") && result.includes("s")) {
            expect(result).toMatch(/\d+m \d+s/);
          }
          if (result.includes("h") && result.includes("s")) {
            expect(result).toMatch(/\d+h \d+m \d+s/);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
