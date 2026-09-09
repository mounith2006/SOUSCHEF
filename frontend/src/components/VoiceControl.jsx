import React from 'react';
import { Mic, Info, Lightbulb, Loader2, Volume2, AlertCircle } from 'lucide-react';

/**
 * VoiceControl Component
 * Renders the Left Column voice control panel matching the reference design layout.
 * 
 * @param {Object} props
 * @param {string} props.status - Current state: 'Ready' | 'Listening...' | 'Processing...' | 'Speaking...' | 'Error'
 * @param {Function} props.onMicClick - Callback fired when microphone button is clicked
 */
export default function VoiceControl({ status = 'Ready', onMicClick }) {
  const isListening = status === 'Listening...';
  const isProcessing = status === 'Processing...';
  const isSpeaking = status === 'Speaking...';
  const isError = status === 'Error';

  const getStatusText = () => {
    switch (status) {
      case 'Listening...':
        return { label: 'Listening to your voice...', color: 'text-[#22C55E]' };
      case 'Processing...':
        return { label: 'Processing request...', color: 'text-[#F97316]' };
      case 'Speaking...':
        return { label: 'SousChef is speaking...', color: 'text-amber-600' };
      case 'Error':
        return { label: 'Speech recognition error', color: 'text-[#EF4444]' };
      case 'Ready':
      default:
        return { label: 'Ready to listen', color: 'text-[#22C55E]' };
    }
  };

  const statusInfo = getStatusText();

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-3xl p-5 md:p-6 shadow-soft flex flex-col justify-between h-full">
      
      {/* Header */}
      <div>
        <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-4 mb-6">
          <div className="flex items-center gap-2">
            <Mic className="w-5 h-5 text-[#F97316]" />
            <h3 className="text-lg md:text-xl font-bold text-[#F97316]">
              Voice Control
            </h3>
          </div>
          <button
            type="button"
            className="p-1 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
            title="Voice Information"
          >
            <Info className="w-4 h-4" />
          </button>
        </div>

        {/* Circular Mic Button Container */}
        <div className="flex flex-col items-center justify-center my-6">
          <div className="relative flex items-center justify-center p-4">
            
            {/* Outer Subtle Rings */}
            <div className={`
              absolute inset-0 rounded-full border-2 transition-all duration-500
              ${isListening ? 'border-[#22C55E]/40 animate-ping-slow scale-110' : 'border-[#FFEDD5] scale-100'}
            `} />
            
            <div className="w-48 h-48 sm:w-52 sm:h-52 rounded-full border border-[#FFEDD5] bg-[#FFFDF8] flex items-center justify-center shadow-soft-sm">
              
              {/* Primary Mic Action Button */}
              <button
                type="button"
                onClick={onMicClick}
                disabled={isListening || isProcessing}
                className={`
                  w-36 h-36 sm:w-40 sm:h-40 rounded-full flex flex-col items-center justify-center gap-2
                  transition-all duration-300 transform shadow-md focus:outline-none focus:ring-4 focus:ring-[#FFEDD5]
                  ${isListening
                    ? 'bg-[#22C55E] text-white shadow-green-glow scale-105'
                    : isProcessing
                    ? 'bg-[#F97316] text-white shadow-orange-glow cursor-wait'
                    : isSpeaking
                    ? 'bg-amber-500 text-white shadow-lg animate-pulse'
                    : isError
                    ? 'bg-[#EF4444] text-white'
                    : 'bg-white hover:bg-[#FFFDF8] text-[#F97316] border-2 border-[#FFEDD5] hover:border-[#F97316] hover:scale-105 active:scale-95'
                  }
                `}
              >
                {isProcessing ? (
                  <Loader2 className="w-10 h-10 animate-spin" />
                ) : isSpeaking ? (
                  <Volume2 className="w-10 h-10 animate-bounce" />
                ) : isError ? (
                  <AlertCircle className="w-10 h-10 text-white" />
                ) : (
                  <>
                    <Mic className="w-10 h-10 text-[#F97316]" />
                    <span className="text-xs font-black tracking-wider uppercase text-[#F97316]">
                      CLICK TO TALK
                    </span>
                  </>
                )}
              </button>

            </div>
          </div>

          {/* Status Label */}
          <div className="mt-4 text-center">
            <span className="text-sm font-bold text-[#1F2937]">
              Status:{' '}
              <span className={`font-extrabold ${statusInfo.color}`}>
                {statusInfo.label}
              </span>
            </span>
          </div>
        </div>
      </div>

      {/* How To Use Bottom Card */}
      <div className="mt-6 bg-[#FFFDF8] border border-[#FFEDD5] rounded-2xl p-4 flex items-start gap-3">
        <Lightbulb className="w-5 h-5 text-[#F97316] flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="text-xs font-extrabold text-[#1F2937] mb-1">
            How to use
          </h4>
          <p className="text-xs text-[#6B7280] leading-relaxed">
            Click the microphone button and start speaking. I'll listen and help you cook!
          </p>
        </div>
      </div>

    </div>
  );
}
