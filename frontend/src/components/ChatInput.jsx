import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2, Loader2, Sparkles } from 'lucide-react';

export default function ChatInput({ onSendMessage, isLoading, onClearChat, disabled }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;
    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="bg-white border-t border-slate-200 px-4 py-4 sm:px-8">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
        <div className="relative flex items-center bg-slate-50 border border-slate-200 rounded-2xl p-2 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500 transition-all">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? "Chat unavailable (check backend connection)" : "Ask a question about your documents... (Press Enter to send)"}
            disabled={isLoading || disabled}
            className="w-full bg-transparent resize-none px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none max-h-36 disabled:opacity-50"
          />

          <div className="flex items-center space-x-1.5 flex-shrink-0 self-end mb-1 mr-1">
            {onClearChat && (
              <button
                type="button"
                onClick={onClearChat}
                disabled={isLoading}
                title="Clear conversation"
                className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-200/60 transition-colors disabled:opacity-40"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}

            <button
              type="submit"
              disabled={!input.trim() || isLoading || disabled}
              className={`
                p-2 rounded-xl flex items-center justify-center transition-all duration-150
                ${input.trim() && !isLoading && !disabled
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm shadow-indigo-200 cursor-pointer'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }
              `}
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between mt-2 px-2 text-[11px] text-slate-400">
          <div className="flex items-center space-x-1">
            <Sparkles className="w-3 h-3 text-indigo-500" />
            <span>Agent answers with LangChain context retrieval and page sources</span>
          </div>
          <span>Shift + Enter for new line</span>
        </div>
      </form>
    </div>
  );
}

