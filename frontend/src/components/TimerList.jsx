import React, { useState } from 'react';
import { Timer, Plus, Clock } from 'lucide-react';
import { useCooking } from '../context/CookingContext';
import { useTimer } from '../hooks/useTimer';
import TimerCard from './TimerCard';

/**
 * TimerList Component
 * Displays compact cooking timers container below instructions in Screen 3 (Cooking Session).
 */
export default function TimerList() {
  const { addTimer } = useCooking();
  const { activeTimers } = useTimer();

  const [customLabel, setCustomLabel] = useState('');
  const [customMins, setCustomMins] = useState(5);
  const [showAddForm, setShowAddForm] = useState(false);

  const handleQuickAdd = (minutes) => {
    addTimer(`${minutes} Min Timer`, minutes * 60);
  };

  const handleCustomSubmit = (e) => {
    e.preventDefault();
    if (customMins <= 0) return;
    addTimer(customLabel.trim() || `${customMins} Min Timer`, customMins * 60);
    setCustomLabel('');
    setShowAddForm(false);
  };

  return (
    <div className="mt-5 bg-white border border-[#E5E7EB] rounded-2xl p-4 shadow-soft">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-3 mb-3">
        <div className="flex items-center gap-2">
          <Timer className="w-4 h-4 text-[#F97316]" />
          <h4 className="text-sm font-bold text-[#1F2937]">
            Active Timers
          </h4>
          <span className="text-[11px] font-bold text-[#6B7280] bg-[#FFFDF8] border border-[#E5E7EB] px-2 py-0.5 rounded-full">
            {activeTimers.length}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setShowAddForm((prev) => !prev)}
          className="px-2.5 py-1 rounded-lg bg-[#FFEDD5] text-[#F97316] hover:bg-[#F97316] hover:text-white font-bold text-xs transition-all flex items-center gap-1 active:scale-95"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>{showAddForm ? 'Close' : 'Add Timer'}</span>
        </button>
      </div>

      {/* Add Custom Timer Drawer */}
      {showAddForm && (
        <form onSubmit={handleCustomSubmit} className="mb-3 p-3 bg-[#FFFDF8] border border-[#FFEDD5] rounded-xl flex flex-col sm:flex-row items-center gap-2 animate-fade-in">
          <input
            type="text"
            placeholder="Timer Label (e.g. Boil Pasta)"
            value={customLabel}
            onChange={(e) => setCustomLabel(e.target.value)}
            className="w-full sm:flex-1 px-3 py-1.5 text-xs bg-white border border-gray-200 rounded-lg focus:outline-none focus:border-[#F97316]"
          />
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <input
              type="number"
              min="1"
              max="180"
              value={customMins}
              onChange={(e) => setCustomMins(Number(e.target.value))}
              className="w-16 px-2 py-1.5 text-xs bg-white border border-gray-200 rounded-lg focus:outline-none focus:border-[#F97316] text-center font-bold"
            />
            <span className="text-[11px] font-bold text-gray-500">mins</span>
          </div>
          <button
            type="submit"
            className="w-full sm:w-auto px-3 py-1.5 bg-[#F97316] text-white text-xs font-bold rounded-lg hover:bg-[#EA580C] transition-all"
          >
            Start
          </button>
        </form>
      )}

      {/* Quick Add Presets */}
      <div className="flex flex-wrap items-center gap-1.5 mb-3">
        <span className="text-[10px] font-bold text-[#6B7280] uppercase tracking-wider mr-1">Quick:</span>
        {[1, 3, 5, 10].map((mins) => (
          <button
            key={mins}
            type="button"
            onClick={() => handleQuickAdd(mins)}
            className="px-2.5 py-0.5 rounded-full bg-[#FFFDF8] border border-[#E5E7EB] text-[#1F2937] hover:border-[#F97316] hover:bg-[#FFEDD5]/50 text-[11px] font-bold transition-all active:scale-95 flex items-center gap-1"
          >
            <Clock className="w-3 h-3 text-[#F97316]" /> +{mins}m
          </button>
        ))}
      </div>

      {/* Active Timers Grid / Compact Empty State */}
      {activeTimers.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {activeTimers.map((timer) => (
            <TimerCard key={timer.id} timer={timer} />
          ))}
        </div>
      ) : (
        <div className="py-2.5 px-3 text-center border border-dashed border-[#E5E7EB] rounded-xl text-[#6B7280] text-xs">
          <span>No active timers</span>
        </div>
      )}

    </div>
  );
}
