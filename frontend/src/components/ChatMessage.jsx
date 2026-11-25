import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, User, Copy, Check } from 'lucide-react';

const markdownComponents = {
  p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1.5 last:mb-0">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1.5 last:mb-0">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
  em: ({ children }) => <em className="not-italic">{children}</em>,
  h1: ({ children }) => <h3 className="text-base font-semibold text-slate-900 mb-2 mt-1">{children}</h3>,
  h2: ({ children }) => <h3 className="text-base font-semibold text-slate-900 mb-2 mt-1">{children}</h3>,
  h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-900 mb-2 mt-1">{children}</h3>,
  a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer" className="text-teal-700 underline underline-offset-2">{children}</a>,
  code: ({ children }) => <code className="bg-slate-100 rounded px-1 py-0.5 text-[13px]">{children}</code>,
  pre: ({ children }) => <pre className="bg-slate-100 rounded-xl p-3 text-[13px] overflow-x-auto mb-3 last:mb-0">{children}</pre>,
  blockquote: ({ children }) => <blockquote className="border-l-2 border-teal-600 pl-3 mb-3 last:mb-0 text-slate-600">{children}</blockquote>,
  hr: () => <hr className="border-slate-200 my-3" />,
};

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
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
            ? 'bg-teal-700 text-white'
            : 'bg-white border border-slate-200 text-teal-600 shadow-xs'
          }
        `}>
          {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
        </div>

        {/* Message Bubble */}
        <div className="flex flex-col group">
          <div className={`
            rounded-2xl px-5 py-4 text-sm leading-relaxed
            ${isUser
              ? 'bg-teal-700 text-white rounded-tr-xs shadow-xs'
              : 'bg-white text-slate-800 border border-slate-200/90 rounded-tl-xs shadow-xs'
            }
          `}>
            {/* Message Text: assistant messages render as clean formatted markdown, user messages as plain text */}
            {isUser ? (
              <div className="whitespace-pre-wrap font-normal break-words">
                {message.content}
              </div>
            ) : (
              <div className="font-normal break-words [&>*:first-child]:mt-0">
                <ReactMarkdown components={markdownComponents}>{message.content || ''}</ReactMarkdown>
              </div>
            )}

            {/* Action Bar */}
            {!isUser && (
              <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span className="text-[11px] font-medium text-slate-400">Assistant</span>
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
