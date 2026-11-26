import React, { useState, useRef, useEffect } from 'react';
import { Bot, AlertCircle } from 'lucide-react';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import apiService from '../services/api';

const DEFAULT_WELCOME_MESSAGE = {
  role: 'assistant',
  content: "Hello! How can I help you today?",
  timestamp: new Date().toISOString(),
};

const SUGGESTIONS = [
  "Summarize the main points of the uploaded documents",
  "What key findings are highlighted in the report?",
  "List the action items and conclusions mentioned",
];

export default function Chat() {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('rag_chat_history');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return [DEFAULT_WELCOME_MESSAGE];
      }
    }
    return [DEFAULT_WELCOME_MESSAGE];
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('rag_chat_history', JSON.stringify(messages));
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (text) => {
    setError(null);
    const userMsg = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setIsLoading(true);

    try {
      // Send message to backend agent
      const historyForApi = newHistory
        .filter((m) => m !== DEFAULT_WELCOME_MESSAGE)
        .map((m) => ({ role: m.role, content: m.content }));

      const data = await apiService.sendMessage(text, historyForApi);

      const aiMsg = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.message || 'Error communicating with the chatbot.';
      setError(errorDetail);
      
      const errorMsg = {
        role: 'assistant',
        content: `Failed to get a response: ${errorDetail}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = () => {
    if (window.confirm('Are you sure you want to clear the chat conversation?')) {
      setMessages([DEFAULT_WELCOME_MESSAGE]);
      localStorage.removeItem('rag_chat_history');
      setError(null);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden animate-in fade-in duration-300">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white z-10">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-800">
              Chat
            </h2>
            <p className="text-[11px] text-slate-500">
              Answers are based on your uploaded knowledge
            </p>
          </div>
        </div>

        <button
          onClick={handleClearChat}
          className="text-xs text-slate-500 hover:text-slate-700 bg-slate-50 hover:bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200/60 transition-colors"
        >
          Clear Chat
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between text-xs text-rose-800 animate-in fade-in">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700 font-bold ml-2">
            ✕
          </button>
        </div>
      )}

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))}

        {/* Loading Bubble */}
        {isLoading && (
          <div className="flex justify-start items-center space-x-3 text-slate-500 text-xs py-2">
            <div className="w-8 h-8 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-teal-600 shadow-xs animate-pulse">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-slate-50 border border-slate-200/80 rounded-2xl px-4 py-3 flex items-center space-x-2" aria-label="Loading">
              <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce" />
              <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:-.3s]" />
              <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:-.5s]" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested prompts chip bar (only when only welcome message) */}
      {messages.length <= 1 && (
        <div className="px-6 py-2 bg-slate-50/50 border-t border-slate-100 flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(suggestion)}
              disabled={isLoading}
              className="text-xs bg-white hover:bg-teal-50 hover:text-teal-600 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-full transition-colors truncate max-w-xs text-left"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      {/* Input Field */}
      <ChatInput
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        onClearChat={handleClearChat}
      />
    </div>
  );
}

