import React from 'react';
import { ChefHat, Clock, CheckCircle2, ChevronLeft, RotateCcw, ChevronRight, FastForward, Loader2 } from 'lucide-react';
import { useCooking } from '../context/CookingContext';

/**
 * CurrentStepCard Component
 * Implements the Center Column cooking session workspace matching the reference design layout.
 */
export default function CurrentStepCard() {
  const {
    currentRecipe,
    currentStepIndex,
    completeStep,
    previousStep,
    skipStep,
    loading
  } = useCooking();

  if (!currentRecipe || !currentRecipe.steps || !currentRecipe.steps[currentStepIndex]) {
    return null;
  }

  const step = currentRecipe.steps[currentStepIndex];
  const totalSteps = currentRecipe.steps.length;
  const progressPercent = Math.round(((currentStepIndex + 1) / totalSteps) * 100);

  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === totalSteps - 1;

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-3xl p-5 md:p-6 shadow-soft flex flex-col justify-between h-full">
      
      <div>
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-4 mb-5">
          <div className="flex items-center gap-2">
            <span className="text-xl select-none">🍳</span>
            <h3 className="text-lg md:text-xl font-bold text-[#F97316]">
              Current Cooking Session
            </h3>
          </div>
        </div>

        {/* Dish Summary Banner Card */}
        <div className="bg-[#FFFDF8] border border-[#E5E7EB] rounded-2xl p-4 mb-5 flex items-center gap-4 shadow-soft-sm">
          <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl bg-[#FFEDD5] text-[#F97316] flex items-center justify-center flex-shrink-0 font-bold text-2xl shadow-sm">
            🍝
          </div>
          
          <div className="flex-1">
            <h4 className="text-lg sm:text-xl font-black text-[#1F2937]">
              {currentRecipe.title}
            </h4>
            <p className="text-xs sm:text-sm text-[#6B7280]">
              {currentRecipe.description || 'Delicious & Easy'}
            </p>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 mt-1 rounded-full text-xs font-bold bg-[#FFEDD5] text-[#F97316]">
              <Clock className="w-3.5 h-3.5" />
              <span>~ {currentRecipe.cookTime}</span>
            </div>
          </div>
        </div>

        {/* Progress Tracker */}
        <div className="mb-5">
          <div className="flex items-center justify-between mb-1.5 text-xs font-bold">
            <span className="text-[#1F2937]">
              Step <span className="text-[#F97316] font-extrabold">{step.stepNumber}</span> of {totalSteps}
            </span>
            <span className="text-[#F97316]">{progressPercent}% Completed</span>
          </div>
          
          <div className="w-full h-3 bg-[#E5E7EB] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#F97316] to-[#EA580C] transition-all duration-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Current Instruction Container */}
        <div className="mb-5">
          <span className="text-xs font-bold text-[#F97316] uppercase tracking-wider block mb-2">
            Current Instruction
          </span>
          <div className="bg-[#FFFDF8] border border-[#FFEDD5] rounded-2xl p-4 sm:p-5 flex items-start gap-3.5 shadow-soft-sm">
            <div className="w-9 h-9 rounded-full bg-[#FFEDD5] text-[#F97316] flex items-center justify-center flex-shrink-0 mt-0.5">
              <ChefHat className="w-5 h-5" />
            </div>
            <p className="text-base sm:text-lg font-bold text-[#1F2937] leading-relaxed">
              {step.instruction}
            </p>
          </div>
        </div>

        {/* Action Controls Row */}
        <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-6">
          {/* Previous Button */}
          <button
            type="button"
            onClick={previousStep}
            disabled={isFirstStep || loading.session}
            className={`
              py-2.5 px-3 rounded-xl border text-xs sm:text-sm font-bold transition-all flex items-center justify-center gap-1
              ${isFirstStep || loading.session
                ? 'border-gray-200 text-gray-400 bg-gray-50 cursor-not-allowed'
                : 'border-[#FFEDD5] text-[#F97316] hover:bg-[#FFEDD5]/40 active:scale-95'
              }
            `}
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          {/* Repeat / Skip Button */}
          <button
            type="button"
            onClick={skipStep}
            disabled={loading.session}
            className="py-2.5 px-3 rounded-xl border border-[#FFEDD5] text-[#F97316] hover:bg-[#FFEDD5]/40 text-xs sm:text-sm font-bold transition-all flex items-center justify-center gap-1 active:scale-95"
          >
            <FastForward className="w-4 h-4" />
            <span>Skip</span>
          </button>

          {/* Next / Complete Button */}
          <button
            type="button"
            onClick={completeStep}
            disabled={loading.session}
            className={`
              py-2.5 px-3 rounded-xl text-white text-xs sm:text-sm font-bold shadow-md transition-all flex items-center justify-center gap-1 active:scale-95
              ${isLastStep ? 'bg-[#22C55E] hover:bg-emerald-600' : 'bg-[#F97316] hover:bg-[#EA580C] shadow-orange-glow'}
            `}
          >
            {loading.session ? (
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            ) : (
              <>
                <span>{isLastStep ? 'Finish' : 'Next'}</span>
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>

      </div>

      {/* All Steps Compact Overview Section */}
      <div className="pt-4 border-t border-[#E5E7EB]">
        <span className="text-xs font-extrabold text-[#1F2937] block mb-3">
          All Steps
        </span>

        <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1">
          {currentRecipe.steps.map((st, idx) => {
            const isCompleted = idx < currentStepIndex;
            const isCurrent = idx === currentStepIndex;

            return (
              <div
                key={st.stepNumber}
                className={`
                  flex items-center justify-between p-2.5 rounded-xl text-xs transition-all border
                  ${isCurrent
                    ? 'bg-[#FFEDD5]/60 border-[#F97316] text-[#1F2937] font-bold shadow-sm'
                    : isCompleted
                    ? 'bg-gray-50 border-transparent text-gray-500'
                    : 'bg-white border-gray-100 text-gray-400'
                  }
                `}
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <span className={`
                    w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold flex-shrink-0
                    ${isCurrent ? 'bg-[#F97316] text-white' : 'bg-gray-200 text-gray-600'}
                  `}>
                    {st.stepNumber}
                  </span>
                  <span className="truncate">{st.instruction}</span>
                </div>

                {isCompleted && (
                  <CheckCircle2 className="w-4 h-4 text-[#22C55E] flex-shrink-0 ml-2" />
                )}
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
