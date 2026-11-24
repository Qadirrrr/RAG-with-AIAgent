import React, { useState } from 'react';
import { Bot, User, BookOpen, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyText = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-3xl ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start gap-3.5`}>
        {/* Avatar */}
        <div className={`
          w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-xs
          ${isUser 
            ? 'bg-indigo-600 text-white' 
            : 'bg-white border border-slate-200 text-indigo-600 shadow-xs'
          }
        `}>
          {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
        </div>

        {/* Message Bubble */}
        <div className="flex flex-col group">
          <div className={`
            rounded-2xl px-5 py-4 text-sm leading-relaxed
            ${isUser
              ? 'bg-indigo-600 text-white rounded-tr-xs shadow-xs'
              : 'bg-white text-slate-800 border border-slate-200/90 rounded-tl-xs shadow-xs'
            }
          `}>
            {/* Message Text with simple formatting support */}
            <div className="whitespace-pre-wrap font-normal break-words">
              {message.content}
            </div>

            {/* AI Action Bar */}
            {!isUser && (
              <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span className="text-[11px] font-medium text-slate-400">AI Knowledge Agent</span>
                <button
                  onClick={copyText}
                  className="flex items-center space-x-1 hover:text-slate-700 transition-colors p-1 rounded hover:bg-slate-50"
                  title="Copy response"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span className="text-[11px]">{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Sources Section for AI Messages */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-2 text-xs">
              <button
                onClick={() => setSourcesOpen(!sourcesOpen)}
                className="flex items-center space-x-1.5 text-indigo-600 hover:text-indigo-700 font-medium bg-indigo-50/70 hover:bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-100 transition-colors"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Sources ({message.sources.length} document references)</span>
                {sourcesOpen ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
              </button>

              {sourcesOpen && (
                <div className="mt-2 space-y-2 max-w-2xl animate-in fade-in duration-200">
                  {message.sources.map((src, index) => (
                    <div 
                      key={index} 
                      className="bg-white border border-slate-200 rounded-xl p-3 shadow-xs text-slate-600"
                    >
                      <div className="flex items-center justify-between mb-1.5 font-medium text-slate-800">
                        <span className="truncate text-xs font-semibold text-indigo-700">
                          📄 {src.document_name}
                        </span>
                        {src.page && (
                          <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                            Page {src.page}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed italic bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-sans">
                        "{src.snippet}"
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Timestamp */}
          {message.timestamp && (
            <span className={`text-[10px] text-slate-400 mt-1 px-1 ${isUser ? 'text-right' : 'text-left'}`}>
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

