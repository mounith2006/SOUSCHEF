/**
 * Conversation Service Module
 * Handles message exchange between frontend UI and AI Conversation Engine.
 * 
 * NOTE: Returns context-aware culinary mock responses until an HTTP conversation router is connected.
 */

/**
 * Send user query to SOUSCHEF AI engine and retrieve assistant response object.
 * 
 * FUTURE BACKEND INTEGRATION:
 * return await apiFetch('/api/conversation/message', {
 *   method: 'POST',
 *   body: JSON.stringify({ message: text, sessionId })
 * });
 * 
 * @param {string} text - User message text
 * @param {string} [sessionId] - Active session ID
 * @returns {Promise<{ id: string, sender: 'souschef', text: string, timestamp: string }>}
 */
export async function sendMessage(text, sessionId = 'default-session') {
  // Simulate network processing delay (1.2 seconds)
  await new Promise((resolve) => setTimeout(resolve, 1200));

  let responseText = "I'm right here in your kitchen! Let's get cooking.";

  const lowerText = text.toLowerCase();
  
  if (lowerText.includes("next") || lowerText.includes("do next")) {
    responseText = "Next, chop 2 cloves of garlic finely and heat 1 tablespoon of olive oil in your skillet over medium heat until shimmering.";
  } else if (lowerText.includes("sauté") || lowerText.includes("onions") || lowerText.includes("how long")) {
    responseText = "Sauté the onions for about 5 to 7 minutes until soft and translucent, stirring occasionally to prevent burning.";
  } else if (lowerText.includes("timer") || lowerText.includes("min") || lowerText.includes("minute")) {
    responseText = "I've noted that time for you! You can also click the quick timer button on your step card.";
  } else if (lowerText.includes("substitute") || lowerText.includes("butter") || lowerText.includes("oil")) {
    responseText = "Yes! You can substitute olive oil for butter in a 1:1 ratio. Extra virgin olive oil adds a wonderful Mediterranean flavor.";
  } else if (lowerText.includes("temperature") || lowerText.includes("skillet") || lowerText.includes("heat")) {
    responseText = "Keep the skillet at medium heat (around 350°F / 175°C). It should sizzle gently when ingredients touch the pan.";
  } else if (lowerText.includes("chicken") || lowerText.includes("salmon") || lowerText.includes("done")) {
    responseText = "The internal temperature should reach 165°F (74°C) for chicken, or 145°F (63°C) for fish. Juices should run clear!";
  } else if (lowerText.length > 0) {
    responseText = `Regarding "${text}": Always keep your pan at medium heat and keep tasting as you season!`;
  }

  return {
    id: `msg-${Date.now()}`,
    sender: 'souschef',
    text: responseText,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  };
}
