import { useEffect } from 'react';
import { useCooking } from '../context/CookingContext';
import { useAudio } from './useAudio';

/**
 * Custom hook to manage active timer intervals and alarm notifications.
 */
export function useTimer() {
  const { activeTimers, updateTimersTick } = useCooking();
  const { playAudio } = useAudio();

  useEffect(() => {
    // Check if any timer is actively running
    const hasRunningTimers = activeTimers.some((t) => t.isRunning && t.remaining > 0);

    if (!hasRunningTimers) return;

    const interval = setInterval(() => {
      updateTimersTick((prevTimers) =>
        prevTimers.map((timer) => {
          if (!timer.isRunning || timer.remaining <= 0) return timer;

          const newRemaining = timer.remaining - 1;

          // Sound alarm chime when timer reaches zero
          if (newRemaining === 0) {
            try {
              playAudio();
            } catch (e) {
              console.warn('Alarm chime play error:', e);
            }
          }

          return {
            ...timer,
            remaining: newRemaining,
            isRunning: newRemaining > 0 ? timer.isRunning : false,
          };
        })
      );
    }, 1000);

    return () => clearInterval(interval);
  }, [activeTimers, updateTimersTick, playAudio]);

  return { activeTimers };
}
