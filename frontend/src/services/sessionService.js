/**
 * Session Service Module
 * Manages cooking session progression and step transitions.
 * 
 * CENTRAL FRONTEND RULE COMPLIANCE:
 * The backend remains the authority for recipe progress, session lifecycle, and step transitions.
 * Future backend integration will connect these async methods to:
 * - POST /api/sessions/start
 * - POST /api/sessions/{id}/next
 * - POST /api/sessions/{id}/previous
 * - POST /api/sessions/{id}/skip
 * - POST /api/sessions/{id}/end
 */

/**
 * Start a new cooking session for a given recipe ID.
 * @param {string} recipeId - The ID of the recipe being cooked.
 * @returns {Promise<{ sessionId: string, status: string, currentStepIndex: number }>}
 */
export async function startSession(recipeId) {
  // Simulate network latency
  await new Promise((resolve) => setTimeout(resolve, 600));

  return {
    sessionId: `session-${Date.now()}`,
    recipeId,
    status: 'cooking',
    currentStepIndex: 0,
    startedAt: new Date().toISOString(),
  };
}

/**
 * Transition to the next step / complete current step.
 * @param {string} sessionId
 * @param {number} currentStepIndex
 * @param {number} totalSteps
 * @returns {Promise<{ currentStepIndex: number, isCompleted: boolean }>}
 */
export async function completeStep(sessionId, currentStepIndex, totalSteps) {
  await new Promise((resolve) => setTimeout(resolve, 300));

  const nextIndex = currentStepIndex + 1;
  const isCompleted = nextIndex >= totalSteps;

  return {
    sessionId,
    currentStepIndex: isCompleted ? currentStepIndex : nextIndex,
    isCompleted,
  };
}

/**
 * Transition to the previous step.
 * @param {string} sessionId
 * @param {number} currentStepIndex
 * @returns {Promise<{ currentStepIndex: number }>}
 */
export async function previousStep(sessionId, currentStepIndex) {
  await new Promise((resolve) => setTimeout(resolve, 300));

  const prevIndex = Math.max(0, currentStepIndex - 1);

  return {
    sessionId,
    currentStepIndex: prevIndex,
  };
}

/**
 * Skip the current step.
 * @param {string} sessionId
 * @param {number} currentStepIndex
 * @param {number} totalSteps
 * @returns {Promise<{ currentStepIndex: number, isCompleted: boolean }>}
 */
export async function skipStep(sessionId, currentStepIndex, totalSteps) {
  await new Promise((resolve) => setTimeout(resolve, 300));

  const nextIndex = currentStepIndex + 1;
  const isCompleted = nextIndex >= totalSteps;

  return {
    sessionId,
    currentStepIndex: isCompleted ? currentStepIndex : nextIndex,
    isCompleted,
    skipped: true,
  };
}

/**
 * End the current cooking session.
 * @param {string} sessionId
 * @returns {Promise<{ success: boolean }>}
 */
export async function endSession(sessionId) {
  await new Promise((resolve) => setTimeout(resolve, 400));

  return {
    sessionId,
    status: 'ended',
    endedAt: new Date().toISOString(),
    success: true,
  };
}
