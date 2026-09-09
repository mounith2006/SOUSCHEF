import React from 'react';
import { Clock, Users, Flame, Play, ArrowLeft, CheckCircle2, Utensils } from 'lucide-react';
import { useCooking } from '../context/CookingContext';

/**
 * RecipeReview Component (SCREEN 2 - Recipe Review)
 * Displays the generated recipe preview (title, time, ingredients list, step outline)
 * and provides primary action "Start Cooking" or secondary action "← Back".
 */
export default function RecipeReview() {
  const { currentRecipe, startCooking, cancelRecipeReview, loading } = useCooking();

  if (!currentRecipe) return null;

  return (
    <div className="w-full max-w-3xl mx-auto my-6 sm:my-8 px-4 animate-fade-in">
      <div className="bg-white border border-[#E5E7EB] rounded-3xl p-6 sm:p-8 shadow-soft relative">
        
        {/* Top Header Navigation & Title */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-[#E5E7EB] pb-6 mb-6">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FFEDD5] text-[#F97316] uppercase tracking-wider mb-2">
              <Utensils className="w-3.5 h-3.5" /> Recipe Review
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-[#1F2937]">
              {currentRecipe.title}
            </h2>
            <p className="text-sm sm:text-base text-[#6B7280] mt-1">
              {currentRecipe.description}
            </p>
          </div>

          <button
            type="button"
            onClick={cancelRecipeReview}
            disabled={loading.session}
            className="self-start px-3.5 py-2 rounded-xl text-xs font-bold text-[#6B7280] hover:text-[#1F2937] hover:bg-gray-100 transition-colors border border-[#E5E7EB] flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Request</span>
          </button>
        </div>

        {/* Recipe Meta Badges (Time, Servings, Difficulty) */}
        <div className="grid grid-cols-3 gap-3 mb-6 bg-[#FFFDF8] border border-[#E5E7EB] rounded-2xl p-4 text-center">
          <div className="flex flex-col items-center justify-center">
            <Clock className="w-5 h-5 text-[#F97316] mb-1" />
            <span className="text-[11px] text-[#6B7280] uppercase font-bold tracking-wider">Cook Time</span>
            <span className="text-sm sm:text-base font-extrabold text-[#1F2937]">{currentRecipe.cookTime}</span>
          </div>

          <div className="flex flex-col items-center justify-center border-x border-[#E5E7EB]">
            <Users className="w-5 h-5 text-[#F97316] mb-1" />
            <span className="text-[11px] text-[#6B7280] uppercase font-bold tracking-wider">Servings</span>
            <span className="text-sm sm:text-base font-extrabold text-[#1F2937]">{currentRecipe.servings} portions</span>
          </div>

          <div className="flex flex-col items-center justify-center">
            <Flame className="w-5 h-5 text-[#F97316] mb-1" />
            <span className="text-[11px] text-[#6B7280] uppercase font-bold tracking-wider">Difficulty</span>
            <span className="text-sm sm:text-base font-extrabold text-[#1F2937]">{currentRecipe.difficulty}</span>
          </div>
        </div>

        {/* Main Content Grid: Ingredients & Steps Preview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          
          {/* Ingredients Column */}
          <div className="bg-[#FFFDF8] border border-[#E5E7EB] rounded-2xl p-5">
            <h3 className="text-lg font-bold text-[#1F2937] mb-3 flex items-center gap-2">
              <span className="text-[#F97316] font-extrabold">🥗</span> Ingredients Needed
            </h3>
            <ul className="space-y-2 text-sm text-[#1F2937]">
              {currentRecipe.ingredients.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2 border-b border-[#E5E7EB]/50 pb-1.5 last:border-none">
                  <CheckCircle2 className="w-4 h-4 text-[#22C55E] flex-shrink-0 mt-0.5" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Steps Overview Column */}
          <div className="bg-[#FFFDF8] border border-[#E5E7EB] rounded-2xl p-5">
            <h3 className="text-lg font-bold text-[#1F2937] mb-3 flex items-center gap-2">
              <span className="text-[#F97316] font-extrabold">📋</span> Recipe Steps ({currentRecipe.steps.length})
            </h3>
            <div className="space-y-3 max-h-[260px] overflow-y-auto pr-1">
              {currentRecipe.steps.map((step) => (
                <div key={step.stepNumber} className="flex gap-3 text-xs sm:text-sm text-[#1F2937]">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#FFEDD5] text-[#F97316] font-bold flex items-center justify-center">
                    {step.stepNumber}
                  </span>
                  <p className="line-clamp-2 leading-relaxed">
                    {step.instruction}
                  </p>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Bottom Action Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-[#E5E7EB] pt-6">
          <button
            type="button"
            onClick={cancelRecipeReview}
            disabled={loading.session}
            className="w-full sm:w-auto px-6 py-3 rounded-2xl border-2 border-[#E5E7EB] text-[#1F2937] font-bold hover:bg-gray-50 transition-all active:scale-95 flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>

          <button
            type="button"
            onClick={startCooking}
            disabled={loading.session}
            className="w-full sm:w-auto px-8 py-3.5 rounded-2xl bg-[#F97316] hover:bg-[#EA580C] text-white font-extrabold shadow-orange-glow transition-all active:scale-95 flex items-center justify-center gap-2 text-base sm:text-lg"
          >
            <Play className="w-5 h-5 fill-white" />
            <span>Start Cooking</span>
          </button>
        </div>

      </div>
    </div>
  );
}
