import { useState, useRef, useCallback } from 'react';

/**
 * Custom hook for audio playback management.
 * Plays synthesized audio chimes for timer alarms / feedback or HTML5 audio streams.
 */
export function useAudio() {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioCtxRef = useRef(null);
  const audioElementRef = useRef(null);

  /**
   * Play audio feedback sound or stream audio URL.
   * @param {string} [audioUrl] - Optional URL to audio stream.
   */
  const playAudio = useCallback((audioUrl) => {
    setIsPlaying(true);

    if (audioUrl) {
      try {
        if (audioElementRef.current) {
          audioElementRef.current.pause();
        }
        const audio = new Audio(audioUrl);
        audioElementRef.current = audio;
        audio.play().then(() => {
          audio.onended = () => setIsPlaying(false);
        }).catch((err) => {
          console.warn('Audio playback error:', err);
          setIsPlaying(false);
        });
      } catch (e) {
        setIsPlaying(false);
      }
      return;
    }

    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioCtxRef.current = new AudioContext();
        const ctx = audioCtxRef.current;
        
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(659.25, ctx.currentTime); // E5
        osc.frequency.exponentialRampToValueAtTime(783.99, ctx.currentTime + 0.15); // G5

        gain.gain.setValueAtTime(0.08, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start();
        osc.stop(ctx.currentTime + 0.6);
      }
    } catch (err) {
      console.warn('Audio synthesis fallback triggered:', err);
    }

    const timeout = setTimeout(() => {
      setIsPlaying(false);
    }, 1200);

    return () => clearTimeout(timeout);
  }, []);

  const stopAudio = useCallback(() => {
    if (audioElementRef.current) {
      audioElementRef.current.pause();
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      try {
        audioCtxRef.current.close();
      } catch (e) {
        // ignore
      }
    }
    setIsPlaying(false);
  }, []);

  return {
    isPlaying,
    playAudio,
    stopAudio,
  };
}
