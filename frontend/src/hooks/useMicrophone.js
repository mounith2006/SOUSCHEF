import { useState, useCallback, useRef } from 'react';

/**
 * Custom hook for microphone recording state & voice conversation lifecycle.
 * Visually handles state transitions: Ready -> Listening... -> Processing... -> Ready
 */
export function useMicrophone() {
  const [status, setStatus] = useState('Ready');
  const [error, setError] = useState(null);
  const flowTimeoutRef = useRef([]);

  const clearFlowTimeouts = useCallback(() => {
    flowTimeoutRef.current.forEach(clearTimeout);
    flowTimeoutRef.current = [];
  }, []);

  /**
   * Visual microphone click interaction handler.
   * Transitions state: Ready -> Listening... -> Processing... -> Ready
   */
  const triggerVoiceFlow = useCallback(({ onStatusChange, onComplete } = {}) => {
    clearFlowTimeouts();
    setError(null);

    // Step 1: Listening...
    setStatus('Listening...');
    if (onStatusChange) onStatusChange('Listening...');

    // Simulate listening duration
    const listenTimer = setTimeout(() => {
      // Step 2: Processing...
      setStatus('Processing...');
      if (onStatusChange) onStatusChange('Processing...');

      const processingTimer = setTimeout(() => {
        // Step 3: Return to Ready
        setStatus('Ready');
        if (onStatusChange) onStatusChange('Ready');
        if (onComplete) onComplete();
      }, 1500);

      flowTimeoutRef.current.push(processingTimer);
    }, 2000);

    flowTimeoutRef.current.push(listenTimer);
  }, [clearFlowTimeouts]);

  const resetStatus = useCallback(() => {
    clearFlowTimeouts();
    setStatus('Ready');
    setError(null);
  }, [clearFlowTimeouts]);

  return {
    status,
    setStatus,
    error,
    setError,
    isListening: status === 'Listening...',
    isProcessing: status === 'Processing...',
    isSpeaking: status === 'Speaking...',
    triggerVoiceFlow,
    resetStatus,
  };
}
