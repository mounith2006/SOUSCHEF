import React, { useState } from 'react';
import { ChefHat, Sparkles, Loader2, ArrowRight, Mic } from 'lucide-react';
import { useCooking } from '../context/CookingContext';
import { useMicrophone } from '../hooks/useMicrophone';

/**
 * RecipeRequest Component (SCREEN 1 - Default Screen)
 * Clean, uncluttered screen focused purely on requesting a recipe via text input or voice.
 */
export default function RecipeRequest() {
  const [prompt, setPrompt] = useState('');
  const { requestRecipe, loading, error } = useCooking();
  const { status: micStatus, triggerVoiceFlow } = useMicrophone();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || loading.recipe) return;
    await requestRecipe(prompt);
  };

  const handleChipClick = async (suggestionText) => {
    setPrompt(suggestionText);
    await requestRecipe(suggestionText);
  };

  const handleMicVoiceFlow = () => {
    triggerVoiceFlow({
      onComplete: () => {
        // Default quick voice prompt trigger if speech captured
        const sampleQuery = "Creamy Pasta";
        setPrompt(sampleQuery);
        requestRecipe(sampleQuery);
      }
    });
  };

  const quickSuggestions = [
    { label: '🍝 Creamy Pasta', query: 'Creamy Pasta' },
    { label: '🍗 Chicken Curry', query: 'Chicken Curry' },
    { label: '🐟 Pan-Seared Salmon', query: 'Pan-Seared Salmon' },
    { label: '🥦 Veggie Stir-Fry', query: 'Vegetable Stir-Fry' },
  ];

  return (
    <div className="w-full max-w-2xl mx-auto my-8 sm:my-12 px-4 animate-fade-in">
      <div className="bg-white border border-[#E5E7EB] rounded-3xl p-6 sm:p-10 shadow-soft text-center relative overflow-hidden">
        
        {/* Subtle Decorative Glow Background Accent */}
        <div className="absolute -top-16 -right-16 w-48 h-48 bg-[#FFEDD5]/60 rounded-full blur-3xl pointer-events-none" />

        {/* Logo & Header */}
        <div className="flex flex-col items-center justify-center mb-6">
          <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-[#FFEDD5] text-[#F97316] flex items-center justify-center mb-4 shadow-sm">
            <ChefHat className="w-10 h-10 sm:w-12 sm:h-12" />
          </div>
          
          <h1 className="text-3xl sm:text-4xl font-extrabold text-[#1F2937] tracking-tight">
            SOUSCHEF
          </h1>
          <p className="text-sm sm:text-base font-semibold text-[#6B7280] mt-1">
            Your AI Cooking Assistant
          </p>
        </div>

        {/* Main Question */}
        <h2 className="text-2xl sm:text-3xl font-extrabold text-[#1F2937] mb-6">
          What would you like to cook?
        </h2>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative flex items-center">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Creamy Pasta, Chicken Curry..."
              disabled={loading.recipe}
              className="w-full px-5 py-4 pl-5 pr-14 text-base sm:text-lg bg-[#FFFDF8] border-2 border-[#E5E7EB] rounded-2xl focus:outline-none focus:border-[#F97316] focus:ring-4 focus:ring-[#FFEDD5] transition-all text-[#1F2937] placeholder-[#9CA3AF]"
            />

            <button
              type="submit"
              disabled={!prompt.trim() || loading.recipe}
              className={`
                absolute right-2 px-4 py-2.5 rounded-xl font-bold text-white transition-all flex items-center gap-1.5 shadow-sm
                ${!prompt.trim() || loading.recipe
                  ? 'bg-gray-300 cursor-not-allowed opacity-70'
                  : 'bg-[#F97316] hover:bg-[#EA580C] active:scale-95 shadow-orange-glow'
                }
              `}
            >
              {loading.recipe ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <span className="hidden sm:inline">Generate</span>
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>

          {/* Voice Input Mic Shortcut */}
          <div className="flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleMicVoiceFlow}
              disabled={loading.recipe}
              className={`
                px-5 py-2.5 rounded-2xl border font-bold text-xs sm:text-sm transition-all flex items-center gap-2 shadow-soft-sm active:scale-95
                ${micStatus === 'Listening...'
                  ? 'bg-[#22C55E] text-white border-[#22C55E] animate-pulse'
                  : micStatus === 'Processing...'
                  ? 'bg-[#F97316] text-white border-[#F97316]'
                  : 'bg-[#FFFDF8] border-[#FFEDD5] text-[#F97316] hover:bg-[#FFEDD5]/50'
                }
              `}
            >
              <Mic className="w-4 h-4" />
              <span>Voice Request ({micStatus})</span>
            </button>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-[#EF4444] rounded-xl text-sm font-semibold text-left animate-bounce">
              ⚠️ {error}
            </div>
          )}

          {/* Quick Suggestion Chips */}
          <div className="pt-2 flex flex-wrap items-center justify-center gap-2">
            <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mr-1 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-[#F97316]" /> Try these:
            </span>
            {quickSuggestions.map((item) => (
              <button
                key={item.query}
                type="button"
                onClick={() => handleChipClick(item.query)}
                disabled={loading.recipe}
                className="px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#FFFDF8] border border-[#E5E7EB] text-[#1F2937] hover:border-[#F97316] hover:bg-[#FFEDD5]/50 transition-all active:scale-95 shadow-soft-sm"
              >
                {item.label}
              </button>
            ))}
          </div>
        </form>

      </div>
    </div>
  );
}
