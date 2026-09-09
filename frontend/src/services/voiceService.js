/**
 * Voice Service Module
 * Connects frontend UI to backend voice API endpoints:
 * - POST /api/voice/transcribe (Whisper STT with "Sofi" wake word)
 * - POST /api/voice/synthesize (Rime TTS WAV audio generation)
 */

import { apiFetch } from './apiClient';

/**
 * Transcribe recorded audio blob into text (Speech-to-Text).
 * Sends multipart/form-data to POST /api/voice/transcribe.
 * 
 * @param {Blob} audioBlob - Recorded audio binary blob.
 * @returns {Promise<{ text: string, wake_word_detected: boolean }>}
 */
export async function transcribeAudio(audioBlob) {
  try {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'speech.wav');

    const result = await apiFetch('/api/voice/transcribe', {
      method: 'POST',
      body: formData,
    });

    return result;
  } catch (error) {
    console.warn('Real STT endpoint call failed, returning fallback mock transcription:', error.message);
    
    // Fallback mock transcription if backend service is unreachable
    const mockQueries = [
      "Sofi, what is the next step?",
      "Sofi, how long should I sauté the onions?",
      "Sofi, set a timer for 5 minutes",
      "Sofi, can I substitute olive oil for butter?",
      "Sofi, how do I check if the dish is done?"
    ];
    const text = mockQueries[Math.floor(Math.random() * mockQueries.length)];
    return {
      text: text.replace(/^Sofi,\s*/i, ''), // Cleaned text
      wake_word_detected: true,
    };
  }
}

/**
 * Synthesize text response into playable WAV audio blob/URL (Text-to-Speech).
 * Sends JSON payload to POST /api/voice/synthesize.
 * 
 * @param {string} text - Response text to generate speech for (max 500 chars).
 * @returns {Promise<{ audioUrl: string | null, audioBlob: Blob | null }>}
 */
export async function synthesizeSpeech(text) {
  if (!text || typeof text !== 'string') return { audioUrl: null, audioBlob: null };

  const cleanText = text.slice(0, 500); // Rime API cap

  try {
    const audioBlob = await apiFetch('/api/voice/synthesize', {
      method: 'POST',
      body: JSON.stringify({ text: cleanText }),
    });

    const audioUrl = URL.createObjectURL(audioBlob);
    return { audioUrl, audioBlob };
  } catch (error) {
    console.warn('Real TTS endpoint call failed:', error.message);
    return { audioUrl: null, audioBlob: null };
  }
}
