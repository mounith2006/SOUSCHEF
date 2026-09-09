import React, { useState, useEffect, useRef } from 'react';
import { ChefHat, User, Sparkles, Send, Trash2, CheckCheck } from 'lucide-react';
import { useCooking } from '../context/CookingContext';

/**
 * Conversation Component
 * Implements the Right Column conversation workspace matching the reference design layout.
 */
export default function Conversation() {
  const { messages, sendChatMessage, clearMessages, loading } = useCooking();
  const [inputText, setInputText] = useState('');
  const scrollRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive or loading state changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages, loading.chat]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || loading.chat) return;
    const text = inputText.trim();
    setInputText('');
    await sendChatMessage(text);
  };

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-3xl p-5 md:p-6 shadow-soft flex flex-col justify-between h-full">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-4 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl select-none">💬</span>
          <h3 className="text-lg md:text-xl font-bold text-[#F97316]">
            Conversation
          </h3>
        </div>

        <button
          type="button"
          onClick={clearMessages}
          className="text-xs font-semibold text-[#6B7280] hover:text-[#EF4444] flex items-center gap-1 transition-colors px-2 py-1 rounded-lg hover:bg-red-50"
          title="Clear Chat History"
        >
          <span>Clear Chat</span>
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Scrollable Message Transcript Window */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 max-h-[380px] min-h-[220px] overflow-y-auto pr-1 sm:pr-2 scroll-smooth"
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center text-[#6B7280]">
            <div className="w-12 h-12 rounded-full bg-[#FFEDD5] text-[#F97316] flex items-center justify-center mb-2">
              <ChefHat className="w-6 h-6" />
            </div>
            <p className="text-sm font-bold text-[#1F2937]">Hello! I'm SOUSCHEF 👋</p>
            <p className="text-xs text-[#6B7280] mt-1 max-w-xs">
              Ask me any question or ask for cooking tips while you prepare your meal!
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isSousChef = msg.sender === 'souschef';

            return (
              <div
                key={msg.id}
                className={`flex gap-2.5 text-xs sm:text-sm ${
                  isSousChef ? 'justify-start' : 'justify-end'
                }`}
              >
                {/* SOUSCHEF Avatar */}
                {isSousChef && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[#FFEDD5] text-[#F97316] border border-[#FFEDD5] flex items-center justify-center shadow-sm mt-0.5">
                    <ChefHat className="w-4 h-4" />
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`max-w-[82%] sm:max-w-[78%] rounded-2xl p-3.5 shadow-soft-sm border transition-all duration-200 ${
                    isSousChef
                      ? 'bg-[#FFFDF8] text-[#1F2937] border-[#E5E7EB] rounded-tl-sm'
                      : 'bg-[#F0F7FF] text-[#1F2937] border-[#BFDBFE] rounded-tr-sm'
                  }`}
                >
                  <p className="leading-relaxed whitespace-pre-wrap font-normal">
                    {msg.text}
                  </p>

                  <div className="flex items-center justify-end gap-1 mt-1 text-[10px] text-gray-400">
                    <span>{msg.timestamp || 'Just now'}</span>
                    {!isSousChef && <CheckCheck className="w-3.5 h-3.5 text-blue-500" />}
                  </div>
                </div>

                {/* User Avatar */}
                {!isSousChef && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[#3B82F6] text-white flex items-center justify-center shadow-sm mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Thinking Indicator */}
        {loading.chat && (
          <div className="flex gap-2.5 text-xs justify-start animate-fade-in">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[#FFEDD5] text-[#F97316] flex items-center justify-center">
              <ChefHat className="w-4 h-4 animate-pulse" />
            </div>
            <div className="bg-[#FFFDF8] border border-[#E5E7EB] rounded-2xl rounded-tl-sm p-3 text-[#6B7280] flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-[#F97316] animate-spin" />
              <span>SOUSCHEF is thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Text Input Bar */}
      <form onSubmit={handleSend} className="mt-4 pt-3 border-t border-[#E5E7EB] flex items-center gap-2">
        <input
          type="text"
          placeholder="Type your message..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={loading.chat}
          className="flex-1 px-4 py-2.5 text-xs sm:text-sm bg-[#FFFDF8] border border-[#E5E7EB] rounded-xl focus:outline-none focus:border-[#F97316] text-[#1F2937]"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || loading.chat}
          className={`
            p-2.5 rounded-xl font-bold text-white transition-all flex items-center justify-center shadow-sm
            ${!inputText.trim() || loading.chat
              ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
              : 'bg-[#F97316] hover:bg-[#EA580C] active:scale-95'
            }
          `}
        >
          <Send className="w-4 h-4 fill-white" />
        </button>
      </form>

    </div>
  );
}
