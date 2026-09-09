/**
 * API Client Utility
 * Standard HTTP fetch wrapper for communicating with the SOUSCHEF backend.
 * Uses environment variable VITE_API_BASE_URL or defaults to http://localhost:8000.
 */

const BASE_URL = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with JSON and error handling.
 * @param {string} endpoint - API path e.g. '/api/voice/synthesize'
 * @param {RequestInit} [options] - Fetch options
 * @returns {Promise<any>} Response JSON data or Blob
 */
export async function apiFetch(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  
  const headers = {
    ...options.headers,
  };

  // Default Content-Type to application/json if sending a JSON body
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP error! status: ${response.status}`;
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          errorMessage = typeof errorData.detail === 'string' 
            ? errorData.detail 
            : JSON.stringify(errorData.detail);
        }
      } catch (e) {
        // Fallback to HTTP error string
      }
      throw new Error(errorMessage);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    } else if (contentType && (contentType.includes('audio/') || contentType.includes('application/octet-stream'))) {
      return await response.blob();
    }

    return await response.text();
  } catch (error) {
    console.error(`API Fetch Error [${endpoint}]:`, error);
    throw error;
  }
}

export { BASE_URL };
