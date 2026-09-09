import React from 'react';
import { AlertTriangle, X, Check } from 'lucide-react';
import { useCooking } from '../context/CookingContext';

/**
 * EndSessionDialog Component
 * Modal confirmation dialog to verify when user wants to terminate an active cooking session.
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether modal is visible
 * @param {Function} props.onClose - Callback to close modal without ending session
 */
export default function EndSessionDialog({ isOpen, onClose }) {
  const { endSession, currentRecipe, loading } = useCooking();

  if (!isOpen) return null;

  const handleConfirmEnd = async () => {
    await endSession();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white border border-[#E5E7EB] rounded-3xl p-6 md:p-8 max-w-md w-full shadow-soft-lg relative">
        
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={loading.session}
          className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 rounded-xl hover:bg-gray-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Warning Icon */}
        <div className="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 border border-amber-200 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-8 h-8" />
        </div>

        {/* Title & Body */}
        <div className="text-center mb-6">
          <h3 className="text-xl md:text-2xl font-extrabold text-[#1F2937]">
            End Cooking Session?
          </h3>
          <p className="text-sm text-[#6B7280] mt-2 leading-relaxed">
            Are you sure you want to end your session for <span className="font-bold text-[#1F2937]">"{currentRecipe?.title || 'this recipe'}"</span>? Active timers and current step progress will be cleared.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading.session}
            className="w-full py-3 px-5 rounded-2xl border-2 border-[#E5E7EB] text-[#1F2937] font-bold hover:bg-gray-50 transition-all active:scale-95 text-sm"
          >
            Cancel & Continue
          </button>

          <button
            type="button"
            onClick={handleConfirmEnd}
            disabled={loading.session}
            className="w-full py-3 px-5 rounded-2xl bg-[#EF4444] hover:bg-red-600 text-white font-extrabold shadow-md transition-all active:scale-95 text-sm flex items-center justify-center gap-1.5"
          >
            <Check className="w-4 h-4" />
            <span>Confirm End Session</span>
          </button>
        </div>

      </div>
    </div>
  );
}
