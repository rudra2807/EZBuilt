/**
 * Time utility functions for deployment history feature
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

/**
 * Format a timestamp as relative time (e.g., "2 hours ago", "3 days ago")
 * Requirement 5.1: Display created timestamp in relative format
 *
 * @param timestamp - ISO 8601 timestamp string
 * @returns Relative time string (e.g., "2 minutes ago")
 */
export function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const past = new Date(timestamp);
  const diffMs = now.getTime() - past.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);

  if (diffSeconds < 60) {
    return diffSeconds === 1 ? "1 second ago" : `${diffSeconds} seconds ago`;
  }

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) {
    return diffMinutes === 1 ? "1 minute ago" : `${diffMinutes} minutes ago`;
  }

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) {
    return diffDays === 1 ? "1 day ago" : `${diffDays} days ago`;
  }

  const diffWeeks = Math.floor(diffDays / 7);
  return diffWeeks === 1 ? "1 week ago" : `${diffWeeks} weeks ago`;
}

/**
 * Calculate duration between two timestamps and format as human-readable string
 * Requirements 5.2, 5.5: Calculate and display duration for completed deployments
 *
 * @param created - ISO 8601 timestamp when deployment started
 * @param completed - ISO 8601 timestamp when deployment finished
 * @returns Duration string (e.g., "5m 23s", "1h 15m", "45s")
 */
export function calculateDuration(created: string, completed: string): string {
  const createdDate = new Date(created);
  const completedDate = new Date(completed);
  const diffMs = completedDate.getTime() - createdDate.getTime();
  const totalSeconds = Math.floor(diffMs / 1000);

  if (totalSeconds < 60) {
    return `${totalSeconds}s`;
  }

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return seconds > 0
      ? `${hours}h ${minutes}m ${seconds}s`
      : `${hours}h ${minutes}m`;
  }

  return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
}

/**
 * Calculate elapsed time since creation for in-progress deployments
 * Requirement 5.4: Display elapsed time for running/started deployments
 *
 * @param created - ISO 8601 timestamp when deployment started
 * @returns Elapsed time string (e.g., "Running for 2m 15s", "Running for 1h 5m")
 */
export function calculateElapsedTime(created: string): string {
  const now = new Date();
  const createdDate = new Date(created);
  const diffMs = now.getTime() - createdDate.getTime();
  const totalSeconds = Math.floor(diffMs / 1000);

  if (totalSeconds < 60) {
    return `Running for ${totalSeconds}s`;
  }

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return seconds > 0
      ? `Running for ${hours}h ${minutes}m ${seconds}s`
      : `Running for ${hours}h ${minutes}m`;
  }

  return seconds > 0
    ? `Running for ${minutes}m ${seconds}s`
    : `Running for ${minutes}m`;
}
