/**
 * Timer Service Module
 * Handles creation, pause, resume, and clear operations for cooking timers.
 * 
 * BACKEND INTEGRATION READY:
 * Operates client-side for the MVP.
 * When backend timer endpoints exist, functions will delegate to POST/DELETE /api/timers.
 */

/**
 * Create a new cooking timer object.
 * @param {string} label - Name or step context for timer (e.g. "Simmer Sauce")
 * @param {number} durationSeconds - Total duration in seconds
 * @returns {Promise<{ id: string, label: string, duration: number, remaining: number, isRunning: boolean }>}
 */
export async function createTimer(label, durationSeconds) {
  const duration = Math.max(1, Math.floor(durationSeconds));
  return {
    id: `timer-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
    label: label || 'Cooking Timer',
    duration,
    remaining: duration,
    isRunning: true,
    createdAt: new Date().toISOString(),
  };
}

/**
 * Pause an active timer.
 * @param {string} timerId
 * @returns {Promise<{ id: string, isRunning: boolean }>}
 */
export async function pauseTimer(timerId) {
  return { id: timerId, isRunning: false };
}

/**
 * Resume a paused timer.
 * @param {string} timerId
 * @returns {Promise<{ id: string, isRunning: boolean }>}
 */
export async function resumeTimer(timerId) {
  return { id: timerId, isRunning: true };
}

/**
 * Clear/delete a timer.
 * @param {string} timerId
 * @returns {Promise<{ id: string, cleared: boolean }>}
 */
export async function clearTimer(timerId) {
  return { id: timerId, cleared: true };
}
