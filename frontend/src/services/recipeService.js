/**
 * Recipe Service Module
 * Handles recipe request generation, search, and retrieval.
 * 
 * BACKEND INTEGRATION READY:
 * Currently returns structured mock recipe data.
 * When the backend team delivers POST /api/recipes/generate or GET /api/recipes/{id},
 * replace the mock implementation below with `apiFetch('/api/recipes/generate', { body: JSON.stringify({ prompt }) })`.
 */

// Library of mock recipes for realistic culinary testing
const MOCK_RECIPES = {
  pasta: {
    id: 'recipe-creamy-garlic-pasta',
    title: 'Creamy Garlic & Herb Pasta',
    description: 'A rich, comforting fettuccine tossed in a velvety garlic cream sauce with fresh parmesan and herbs.',
    cookTime: '25 mins',
    servings: 2,
    difficulty: 'Easy',
    ingredients: [
      '200g Fettuccine or Linguine pasta',
      '2 tbsp Extra Virgin Olive Oil',
      '4 cloves Garlic, finely minced',
      '1 cup Heavy Cream (or whole milk blend)',
      '1/2 cup Freshly grated Parmesan cheese',
      '1/2 tsp Sea salt & freshly ground black pepper',
      '2 tbsp Fresh Parsley, chopped'
    ],
    steps: [
      {
        stepNumber: 1,
        instruction: 'Bring a large pot of salted water to a rolling boil. Add pasta and cook for 8-10 minutes until al dente.',
        tip: 'Reserve 1/2 cup of starchy pasta water before draining.',
        suggestedTimerSeconds: 600
      },
      {
        stepNumber: 2,
        instruction: 'While pasta cooks, heat 2 tablespoons of olive oil in a skillet over medium heat. Add minced garlic and sauté for 1-2 minutes until fragrant and golden.',
        tip: 'Be careful not to burn the garlic!',
        suggestedTimerSeconds: 120
      },
      {
        stepNumber: 3,
        instruction: 'Pour in the heavy cream and bring to a gentle simmer for 3 minutes until slightly thickened.',
        tip: 'Stir gently with a whisk or wooden spoon.',
        suggestedTimerSeconds: 180
      },
      {
        stepNumber: 4,
        instruction: 'Lower heat to low, whisk in grated parmesan cheese until melted and smooth. Season with salt and pepper.',
        tip: 'Add a splash of pasta water if sauce feels too thick.',
        suggestedTimerSeconds: 0
      },
      {
        stepNumber: 5,
        instruction: 'Toss cooked pasta directly into the sauce. Garnish with fresh chopped parsley and serve hot!',
        tip: 'Garnish with extra parmesan if desired.',
        suggestedTimerSeconds: 0
      }
    ]
  },
  salmon: {
    id: 'recipe-pan-seared-salmon',
    title: 'Pan-Seared Lemon Garlic Salmon',
    description: 'Crispy skin salmon fillets cooked to perfection in a luscious lemon-butter glaze.',
    cookTime: '20 mins',
    servings: 2,
    difficulty: 'Medium',
    ingredients: [
      '2 Salmon fillets (skin-on, pat dry)',
      '1 tbsp Olive oil',
      '2 tbsp Butter',
      '3 cloves Garlic, minced',
      '1 Lemon (juiced and zested)',
      'Salt, pepper, and dill to taste'
    ],
    steps: [
      {
        stepNumber: 1,
        instruction: 'Pat salmon fillets thoroughly dry with paper towels. Season both sides generously with salt and fresh black pepper.',
        tip: 'Dry skin ensures maximum crispiness.',
        suggestedTimerSeconds: 0
      },
      {
        stepNumber: 2,
        instruction: 'Heat olive oil in a non-stick skillet over medium-high heat until shimmering. Place salmon skin-side down.',
        tip: 'Press gently for 10 seconds to keep skin flat.',
        suggestedTimerSeconds: 0
      },
      {
        stepNumber: 3,
        instruction: 'Sear undisturbed for 4 to 5 minutes until skin is crispy and golden.',
        tip: 'Don’t move the fish until it releases easily.',
        suggestedTimerSeconds: 300
      },
      {
        stepNumber: 4,
        instruction: 'Flip salmon, reduce heat to medium, add butter, garlic, lemon juice, and zest. Spoon melted butter glaze over fillets for 3 minutes.',
        tip: 'Internal temperature should reach 145°F (63°C).',
        suggestedTimerSeconds: 180
      },
      {
        stepNumber: 5,
        instruction: 'Remove from heat, rest for 2 minutes, garnish with fresh dill and lemon slices, and serve.',
        tip: 'Pairs wonderfully with asparagus or quinoa.',
        suggestedTimerSeconds: 120
      }
    ]
  },
  stirfry: {
    id: 'recipe-vegetable-stir-fry',
    title: 'Vibrant Sesame Vegetable Stir-Fry',
    description: 'Crispy colorful vegetables tossed in a sweet and savory ginger-sesame soy sauce.',
    cookTime: '15 mins',
    servings: 3,
    difficulty: 'Easy',
    ingredients: [
      '1 cup Broccoli florets',
      '1 Red Bell Pepper, sliced',
      '1 Snap Peas cup',
      '2 Carrots, julienned',
      '3 tbsp Soy Sauce',
      '1 tbsp Sesame Oil & 1 tbsp Honey',
      '1 tbsp Fresh Ginger, grated'
    ],
    steps: [
      {
        stepNumber: 1,
        instruction: 'Whisk together soy sauce, sesame oil, honey, grated ginger, and 1 tsp cornstarch in a small bowl for the stir-fry sauce.',
        tip: 'Mix thoroughly so no cornstarch lumps remain.',
        suggestedTimerSeconds: 0
      },
      {
        stepNumber: 2,
        instruction: 'Heat 1 tbsp oil in a large wok or skillet over high heat. Add carrots and broccoli first; stir-fry for 3 minutes.',
        tip: 'High heat creates authentic wok-hei flavor.',
        suggestedTimerSeconds: 180
      },
      {
        stepNumber: 3,
        instruction: 'Add bell peppers and snap peas. Continue stir-frying for another 2 to 3 minutes until tender-crisp.',
        tip: 'Vegetables should stay vibrant and crunchy.',
        suggestedTimerSeconds: 150
      },
      {
        stepNumber: 4,
        instruction: 'Pour in prepared sauce. Toss continuously for 1 minute until sauce thickens and coats all vegetables evenly.',
        tip: 'Remove from heat immediately to prevent overcooking.',
        suggestedTimerSeconds: 60
      },
      {
        stepNumber: 5,
        instruction: 'Serve immediately over steamed jasmine rice or noodles, sprinkled with toasted sesame seeds.',
        tip: 'Enjoy fresh and hot!',
        suggestedTimerSeconds: 0
      }
    ]
  }
};

/**
 * Request/Generate a recipe based on user prompt text.
 * 
 * FUTURE BACKEND CALL:
 * return await apiFetch('/api/recipes/generate', {
 *   method: 'POST',
 *   body: JSON.stringify({ prompt })
 * });
 * 
 * @param {string} prompt - User request query (e.g. "I want to cook pasta")
 * @returns {Promise<Object>} Generated recipe payload object
 */
export async function requestRecipe(prompt) {
  // Simulate network processing delay (1.2 seconds)
  await new Promise((resolve) => setTimeout(resolve, 1200));

  if (!prompt || typeof prompt !== 'string' || !prompt.trim()) {
    throw new Error('Please enter what you would like to cook.');
  }

  const query = prompt.toLowerCase();

  if (query.includes('salmon') || query.includes('fish') || query.includes('seafood')) {
    return { ...MOCK_RECIPES.salmon, requestedPrompt: prompt };
  } else if (query.includes('stir') || query.includes('veg') || query.includes('rice') || query.includes('asian')) {
    return { ...MOCK_RECIPES.stirfry, requestedPrompt: prompt };
  } else {
    // Default to pasta recipe with customized title if user asked for something specific
    const recipe = { ...MOCK_RECIPES.pasta, requestedPrompt: prompt };
    if (!query.includes('pasta')) {
      recipe.title = `${prompt.trim().charAt(0).toUpperCase() + prompt.trim().slice(1)} (SousChef Special)`;
    }
    return recipe;
  }
}
