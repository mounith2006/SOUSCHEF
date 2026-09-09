import React, { createContext, useContext, useState, useCallback } from 'react';
import * as recipeService from '../services/recipeService';
import * as sessionService from '../services/sessionService';
import * as timerService from '../services/timerService';
import * as conversationService from '../services/conversationService';

const CookingContext = createContext(null);

export function CookingProvider({ children }) {
  // Session State Flow: 'idle' | 'reviewing' | 'cooking' | 'completed'
  const [sessionStatus, setSessionStatus] = useState('idle');
  const [sessionId, setSessionId] = useState(null);
  const [currentRecipe, setCurrentRecipe] = useState(null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Timers State
  const [activeTimers, setActiveTimers] = useState([]);

  // Conversation Messages State (starts empty, populates ONLY on user interaction)
  const [messages, setMessages] = useState([]);

  // UI Loading & Error States
  const [loading, setLoading] = useState({
    recipe: false,
    session: false,
    chat: false,
  });
  const [error, setError] = useState(null);

  const clearError = useCallback(() => setError(null), []);

  const setOpLoading = (key, val) => {
    setLoading((prev) => ({ ...prev, [key]: val }));
  };

  /**
   * 1. Request Recipe Input -> Generates Recipe Review Card
   */
  const requestRecipe = useCallback(async (promptText) => {
    clearError();
    setOpLoading('recipe', true);

    try {
      const recipe = await recipeService.requestRecipe(promptText);
      setCurrentRecipe(recipe);
      setSessionStatus('reviewing');
    } catch (err) {
      setError(err.message || 'Failed to request recipe. Please try again.');
    } finally {
      setOpLoading('recipe', false);
    }
  }, [clearError]);

  /**
   * Cancel Recipe Review -> Returns to Idle State
   */
  const cancelRecipeReview = useCallback(() => {
    setCurrentRecipe(null);
    setSessionStatus('idle');
    clearError();
  }, [clearError]);

  /**
   * 2. Start Cooking Session
   */
  const startCooking = useCallback(async () => {
    if (!currentRecipe) return;
    clearError();
    setOpLoading('session', true);

    try {
      const sessionData = await sessionService.startSession(currentRecipe.id);
      setSessionId(sessionData.sessionId);
      setCurrentStepIndex(0);
      setSessionStatus('cooking');
    } catch (err) {
      setError(err.message || 'Failed to start cooking session.');
    } finally {
      setOpLoading('session', false);
    }
  }, [currentRecipe, clearError]);

  /**
   * 3. Step Navigation: Complete Current Step
   */
  const completeStep = useCallback(async () => {
    if (!currentRecipe || !sessionId) return;
    clearError();
    setOpLoading('session', true);

    const totalSteps = currentRecipe.steps.length;

    try {
      const result = await sessionService.completeStep(sessionId, currentStepIndex, totalSteps);
      
      if (result.isCompleted) {
        setSessionStatus('completed');
      } else {
        setCurrentStepIndex(result.currentStepIndex);
      }
    } catch (err) {
      setError(err.message || 'Failed to advance to next step.');
    } finally {
      setOpLoading('session', false);
    }
  }, [currentRecipe, sessionId, currentStepIndex, clearError]);

  /**
   * 4. Step Navigation: Previous Step
   */
  const previousStep = useCallback(async () => {
    if (!currentRecipe || !sessionId || currentStepIndex === 0) return;
    clearError();
    setOpLoading('session', true);

    try {
      const result = await sessionService.previousStep(sessionId, currentStepIndex);
      setCurrentStepIndex(result.currentStepIndex);
    } catch (err) {
      setError(err.message || 'Failed to return to previous step.');
    } finally {
      setOpLoading('session', false);
    }
  }, [currentRecipe, sessionId, currentStepIndex, clearError]);

  /**
   * 5. Step Navigation: Skip Step
   */
  const skipStep = useCallback(async () => {
    if (!currentRecipe || !sessionId) return;
    clearError();
    setOpLoading('session', true);

    const totalSteps = currentRecipe.steps.length;

    try {
      const result = await sessionService.skipStep(sessionId, currentStepIndex, totalSteps);
      
      if (result.isCompleted) {
        setSessionStatus('completed');
      } else {
        setCurrentStepIndex(result.currentStepIndex);
      }
    } catch (err) {
      setError(err.message || 'Failed to skip step.');
    } finally {
      setOpLoading('session', false);
    }
  }, [currentRecipe, sessionId, currentStepIndex, clearError]);

  /**
   * 6. End Session Teardown -> Resets State to 'idle'
   */
  const endSession = useCallback(async () => {
    clearError();
    setOpLoading('session', true);

    try {
      if (sessionId) {
        await sessionService.endSession(sessionId);
      }
    } catch (err) {
      console.warn('Session end call error:', err);
    } finally {
      setSessionStatus('idle');
      setSessionId(null);
      setCurrentRecipe(null);
      setCurrentStepIndex(0);
      setActiveTimers([]);
      setOpLoading('session', false);
    }
  }, [sessionId, clearError]);

  /**
   * 7. Send Chat Message
   */
  const sendChatMessage = useCallback(async (userText) => {
    if (!userText || !userText.trim()) return;
    clearError();

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg = {
      id: `user-msg-${Date.now()}`,
      sender: 'user',
      text: userText.trim(),
      timestamp,
    };

    setMessages((prev) => [...prev, userMsg]);
    setOpLoading('chat', true);

    try {
      const response = await conversationService.sendMessage(userText, sessionId || 'default-session');
      setMessages((prev) => [...prev, response]);
    } catch (err) {
      setError('Could not get response from SOUSCHEF assistant.');
    } finally {
      setOpLoading('chat', false);
    }
  }, [sessionId, clearError]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  /**
   * 8. Timer Management
   */
  const addTimer = useCallback(async (label, durationSeconds) => {
    try {
      const newTimer = await timerService.createTimer(label, durationSeconds);
      setActiveTimers((prev) => [...prev, newTimer]);
    } catch (err) {
      setError('Failed to create timer.');
    }
  }, []);

  const pauseTimer = useCallback(async (timerId) => {
    await timerService.pauseTimer(timerId);
    setActiveTimers((prev) =>
      prev.map((t) => (t.id === timerId ? { ...t, isRunning: false } : t))
    );
  }, []);

  const resumeTimer = useCallback(async (timerId) => {
    await timerService.resumeTimer(timerId);
    setActiveTimers((prev) =>
      prev.map((t) => (t.id === timerId ? { ...t, isRunning: true } : t))
    );
  }, []);

  const clearTimer = useCallback(async (timerId) => {
    await timerService.clearTimer(timerId);
    setActiveTimers((prev) => prev.filter((t) => t.id !== timerId));
  }, []);

  const updateTimersTick = useCallback((tickFn) => {
    setActiveTimers(tickFn);
  }, []);

  const value = {
    sessionStatus,
    sessionId,
    currentRecipe,
    currentStepIndex,
    activeTimers,
    messages,
    loading,
    error,
    clearError,
    setError,
    requestRecipe,
    cancelRecipeReview,
    startCooking,
    completeStep,
    previousStep,
    skipStep,
    endSession,
    sendChatMessage,
    clearMessages,
    addTimer,
    pauseTimer,
    resumeTimer,
    clearTimer,
    updateTimersTick,
  };

  return <CookingContext.Provider value={value}>{children}</CookingContext.Provider>;
}

export function useCooking() {
  const context = useContext(CookingContext);
  if (!context) {
    throw new Error('useCooking must be used within a CookingProvider');
  }
  return context;
}
