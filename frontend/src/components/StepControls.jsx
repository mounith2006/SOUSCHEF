import React from 'react';
import { ChevronLeft, ChevronRight, CheckCircle2, FastForward, Loader2 } from 'lucide-react';
import { useCooking } from '../context/CookingContext';

/**
 * StepControls Component
 * Provides Previous, Skip, and Complete/Next controls for cooking session progression.
 */
export default function StepControls() {
  const {
    currentRecipe,
    currentStepIndex,
    completeStep,
    previousStep,
    skipStep,
    loading
  } = useCooking();

  if (!currentRecipe || !currentRecipe.steps) return null;

  const totalSteps = currentRecipe.steps.length;
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === totalSteps - 1;

  return (
    <div className="w-full max-w-3xl mx-auto my-4 px-4">
      <div className="bg-white border border-[#E5E7EB] rounded-2xl p-4 md:p-5 shadow-soft flex flex-col sm:flex-row items-center justify-between gap-3">
        
        {/* Previous Step Button */}
        <button
          type="button"
          onClick={previousStep}
          disabled={isFirstStep || loading.session}
          className={`
            w-full sm:w-auto px-5 py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-1.5 border-2
            ${isFirstStep || loading.session
              ? 'border-gray-200 text-gray-400 cursor-not-allowed bg-gray-50'
              : 'border-[#E5E7EB] text-[#1F2937] hover:bg-gray-100 active:scale-95'
            }
          `}
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Previous Step</span>
        </button>

        {/* Skip Step Button */}
        <button
          type="button"
          onClick={skipStep}
          disabled={loading.session}
          className="w-full sm:w-auto px-4 py-3 rounded-xl font-bold text-xs md:text-sm text-[#6B7280] hover:text-[#1F2937] hover:bg-gray-100 transition-all active:scale-95 flex items-center justify-center gap-1"
        >
          <FastForward className="w-4 h-4" />
          <span>Skip Step</span>
        </button>

        {/* Complete Step / Finish Recipe Button */}
        <button
          type="button"
          onClick={completeStep}
          disabled={loading.session}
          className={`
            w-full sm:w-auto px-7 py-3.5 rounded-xl font-extrabold text-sm md:text-base text-white shadow-md transition-all flex items-center justify-center gap-2 active:scale-95
            ${isLastStep
              ? 'bg-[#22C55E] hover:bg-emerald-600 shadow-green-glow'
              : 'bg-[#F97316] hover:bg-[#EA580C] shadow-orange-glow'
            }
            ${loading.session ? 'cursor-wait opacity-80' : ''}
          `}
        >
          {loading.session ? (
            <Loader2 className="w-5 h-5 animate-spin text-white" />
          ) : isLastStep ? (
            <>
              <CheckCircle2 className="w-5 h-5" />
              <span>Finish Cooking Recipe 🎉</span>
            </>
          ) : (
            <>
              <span>Complete Step</span>
              <ChevronRight className="w-5 h-5" />
            </>
          )}
        </button>

      </div>
    </div>
  );
}
