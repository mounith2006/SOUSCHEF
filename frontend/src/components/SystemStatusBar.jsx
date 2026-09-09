import React from 'react';
import { Network, Mic, MessageSquare, Cpu } from 'lucide-react';

/**
 * SystemStatusBar Component
 * Renders the bottom integration status indicator matching the reference design.
 */
export default function SystemStatusBar() {
  return (
    <div className="w-full mt-8 bg-white border border-[#E5E7EB] rounded-2xl p-4 shadow-soft">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-xs">
        
        {/* Title */}
        <div className="flex items-center gap-2 font-bold text-[#1F2937] text-sm">
          <Network className="w-4 h-4 text-[#F97316]" />
          <span>System Integration Status</span>
        </div>

        {/* Status Indicators Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-8 w-full md:w-auto">
          
          {/* Voice API */}
          <div className="flex items-center gap-2 text-[#6B7280]">
            <Mic className="w-4 h-4 text-[#F97316]" />
            <div>
              <span className="font-semibold text-[#1F2937] block">Voice API</span>
              <span className="flex items-center gap-1.5 text-[11px]">
                <span className="w-2 h-2 rounded-full bg-[#22C55E]" />
                Connected (/api/voice)
              </span>
            </div>
          </div>

          {/* Conversation API */}
          <div className="flex items-center gap-2 text-[#6B7280]">
            <MessageSquare className="w-4 h-4 text-[#F97316]" />
            <div>
              <span className="font-semibold text-[#1F2937] block">Conversation API</span>
              <span className="flex items-center gap-1.5 text-[11px]">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                Local Assistant Engine
              </span>
            </div>
          </div>

          {/* Cooking Engine */}
          <div className="flex items-center gap-2 text-[#6B7280]">
            <Cpu className="w-4 h-4 text-[#F97316]" />
            <div>
              <span className="font-semibold text-[#1F2937] block">Cooking Engine</span>
              <span className="flex items-center gap-1.5 text-[11px]">
                <span className="w-2 h-2 rounded-full bg-[#22C55E]" />
                State Machine Ready
              </span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
