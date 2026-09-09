import React, { useState } from 'react';
import { CookingProvider, useCooking } from './context/CookingContext';
import RecipeRequest from './components/RecipeRequest';
import RecipeReview from './components/RecipeReview';
import CurrentStepCard from './components/CurrentStepCard';
import TimerList from './components/TimerList';
import VoiceControl from './components/VoiceControl';
import Conversation from './components/Conversation';
import SystemStatusBar from './components/SystemStatusBar';
import EndSessionDialog from './components/EndSessionDialog';
import { useMicrophone } from './hooks/useMicrophone';
import { Settings, LogOut, CheckCircle2, RotateCcw } from 'lucide-react';

/**
 * Main Inner Content Component consuming CookingContext
 */
function MainContent() {
  const { sessionStatus, currentRecipe, endSession } = useCooking();
  const { status: micStatus, triggerVoiceFlow } = useMicrophone();
  const [isEndDialogOpen, setIsEndDialogOpen] = useState(false);

  const handleMicClick = () => {
    triggerVoiceFlow();
  };

  return (
    <div className="min-h-screen bg-[#FFFDF8] text-[#1F2937] flex flex-col justify-between items-center font-sans antialiased">
      
      {/* Top Header Bar Matching Reference Image */}
      <header className="w-full border-b border-[#E5E7EB]/60 bg-white/80 backdrop-blur-md sticky top-0 z-40 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          
          {/* Logo & Subtitle */}
          <div className="flex items-center gap-2.5">
            <span className="text-2xl select-none">🍳</span>
            <div>
              <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-[#F97316] leading-none">
                SOUSCHEF
              </h1>
              <span className="text-[11px] font-semibold text-[#6B7280]">
                AI Cooking Assistant
              </span>
            </div>
          </div>

          {/* System Ready Badge */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-white border border-[#E5E7EB] rounded-full text-xs font-semibold text-[#1F2937] shadow-soft-sm">
            <span className="w-2.5 h-2.5 rounded-full bg-[#22C55E] animate-pulse" />
            <span>System Ready</span>
          </div>

          {/* Top Actions */}
          <div className="flex items-center gap-2">
            {sessionStatus === 'cooking' && (
              <button
                type="button"
                onClick={() => setIsEndDialogOpen(true)}
                className="px-3.5 py-1.5 rounded-xl border border-red-200 text-[#EF4444] hover:bg-red-50 font-bold text-xs transition-all flex items-center gap-1.5 active:scale-95"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>End Session</span>
              </button>
            )}

            <button
              type="button"
              className="p-2 rounded-xl border border-[#E5E7EB] bg-white text-[#1F2937] hover:bg-gray-50 text-xs font-bold transition-all flex items-center gap-1.5"
              title="Settings"
            >
              <Settings className="w-4 h-4 text-[#6B7280]" />
              <span className="hidden md:inline">Settings</span>
            </button>
          </div>

        </div>
      </header>

      {/* Main Workspace Container */}
      <main className="w-full flex-1 max-w-7xl mx-auto px-4 py-6">
        
        {/* SCREEN 1 — IDLE / RECIPE REQUEST */}
        {sessionStatus === 'idle' && <RecipeRequest />}

        {/* SCREEN 2 — RECIPE REVIEW */}
        {sessionStatus === 'reviewing' && <RecipeReview />}

        {/* SCREEN 3 — COOKING SESSION (3-Column Desktop Workspace) */}
        {sessionStatus === 'cooking' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* LEFT COLUMN: Voice Control */}
            <div className="lg:col-span-3 order-2 lg:order-1 h-full">
              <VoiceControl
                status={micStatus}
                onMicClick={handleMicClick}
              />
            </div>

            {/* CENTER COLUMN: Current Cooking Session + Timers */}
            <div className="lg:col-span-5 order-1 lg:order-2 space-y-5">
              <CurrentStepCard />
              <TimerList />
            </div>

            {/* RIGHT COLUMN: Conversation Panel */}
            <div className="lg:col-span-4 order-3 lg:order-3 h-full">
              <Conversation />
            </div>

          </div>
        )}

        {/* SCREEN 4 — SESSION COMPLETED */}
        {sessionStatus === 'completed' && (
          <div className="w-full max-w-2xl mx-auto my-10 p-8 sm:p-10 bg-white border border-emerald-200 rounded-3xl shadow-soft text-center animate-fade-in">
            <div className="w-20 h-20 rounded-full bg-emerald-100 text-[#22C55E] flex items-center justify-center mx-auto mb-4 shadow-sm">
              <CheckCircle2 className="w-12 h-12" />
            </div>
            
            <h2 className="text-3xl sm:text-4xl font-extrabold text-[#1F2937]">
              🎉 Cooking Complete!
            </h2>
            <p className="text-base sm:text-lg text-[#6B7280] mt-2">
              Great job! You have finished cooking <span className="font-bold text-[#1F2937]">"{currentRecipe?.title || 'your dish'}"</span>. Bon appétit!
            </p>

            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                type="button"
                onClick={endSession}
                className="w-full sm:w-auto px-6 py-3.5 bg-[#F97316] hover:bg-[#EA580C] text-white font-extrabold rounded-2xl shadow-orange-glow transition-all active:scale-95 flex items-center justify-center gap-2 text-base"
              >
                <RotateCcw className="w-5 h-5" />
                <span>Cook Another Recipe</span>
              </button>
            </div>
          </div>
        )}

        {/* Bottom System Integration Status Bar */}
        <SystemStatusBar />

      </main>

      {/* End Session Confirmation Modal */}
      <EndSessionDialog
        isOpen={isEndDialogOpen}
        onClose={() => setIsEndDialogOpen(false)}
      />

    </div>
  );
}

/**
 * Root App Wrapper providing CookingProvider Context
 */
export default function App() {
  return (
    <CookingProvider>
      <MainContent />
    </CookingProvider>
  );
}
