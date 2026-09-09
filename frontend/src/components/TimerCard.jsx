import React from 'react';
import { Play, Pause, Trash2, BellRing, Clock } from 'lucide-react';
import { useCooking } from '../context/CookingContext';

/**
 * TimerCard Component
 * Displays an individual active cooking timer with formatted countdown (MM:SS),
 * progress ring/bar, and Pause / Resume / Clear action controls.
 * 
 * @param {Object} props
 * @param {Object} props.timer - Timer object { id, label, duration, remaining, isRunning }
 */
export default function TimerCard({ timer }) {
  const { pauseTimer, resumeTimer, clearTimer } = useCooking();

  const isFinished = timer.remaining <= 0;
  
  // Format remaining time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const progressPercent = Math.round(((timer.duration - timer.remaining) / timer.duration) * 100);

  return (
    <div className={`
      relative rounded-2xl border p-4 shadow-soft transition-all duration-300 overflow-hidden flex flex-col justify-between
      ${isFinished
        ? 'bg-red-50 border-red-300 animate-pulse'
        : timer.isRunning
        ? 'bg-white border-[#E5E7EB]'
        : 'bg-[#FFFDF8] border-[#E5E7EB] opacity-90'
      }
    `}>
      {/* Top Header: Label & Clear Button */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 overflow-hidden">
          <Clock className={`w-4 h-4 flex-shrink-0 ${isFinished ? 'text-[#EF4444]' : 'text-[#F97316]'}`} />
          <h4 className="text-xs font-bold text-[#1F2937] truncate" title={timer.label}>
            {timer.label}
          </h4>
        </div>

        <button
          type="button"
          onClick={() => clearTimer(timer.id)}
          className="p-1 rounded-lg text-gray-400 hover:text-[#EF4444] hover:bg-red-50 transition-colors"
          title="Clear Timer"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Center Countdown Display */}
      <div className="my-2 text-center">
        {isFinished ? (
          <div className="flex items-center justify-center gap-2 text-[#EF4444] font-extrabold text-xl animate-bounce">
            <BellRing className="w-6 h-6" />
            <span>TIME'S UP!</span>
          </div>
        ) : (
          <div className="text-3xl font-extrabold font-mono tracking-wider text-[#1F2937]">
            {formatTime(timer.remaining)}
          </div>
        )}

        {/* Progress Bar */}
        <div className="w-full h-2 bg-gray-100 rounded-full mt-3 overflow-hidden">
          <div
            className={`h-full transition-all duration-1000 rounded-full ${
              isFinished ? 'bg-[#EF4444]' : timer.isRunning ? 'bg-[#F97316]' : 'bg-amber-400'
            }`}
            style={{ width: `${Math.min(100, progressPercent)}%` }}
          />
        </div>
      </div>

      {/* Bottom Action Controls */}
      <div className="mt-3 flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
        <span className="text-[11px] font-semibold text-gray-500">
          Total: {Math.ceil(timer.duration / 60)}m
        </span>

        {!isFinished && (
          <div>
            {timer.isRunning ? (
              <button
                type="button"
                onClick={() => pauseTimer(timer.id)}
                className="px-3 py-1 rounded-lg bg-amber-100 text-amber-800 hover:bg-amber-200 text-xs font-bold transition-all flex items-center gap-1"
              >
                <Pause className="w-3.5 h-3.5" /> Pause
              </button>
            ) : (
              <button
                type="button"
                onClick={() => resumeTimer(timer.id)}
                className="px-3 py-1 rounded-lg bg-emerald-100 text-emerald-800 hover:bg-emerald-200 text-xs font-bold transition-all flex items-center gap-1"
              >
                <Play className="w-3.5 h-3.5 fill-emerald-800" /> Resume
              </button>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
