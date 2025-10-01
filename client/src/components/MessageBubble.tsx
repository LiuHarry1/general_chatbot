import React, { useState } from 'react';
import { ChatMessage } from '../types';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { ThumbsUp, ThumbsDown, Copy, Check } from 'lucide-react';

interface MessageBubbleProps {
  message: ChatMessage;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleLike = () => {
    setLiked(!liked);
    if (disliked) setDisliked(false);
  };

  const handleDislike = () => {
    setDisliked(!disliked);
    if (liked) setLiked(false);
  };


  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`${isUser ? 'max-w-xs' : 'max-w-4xl'}`}>
        {/* 用户消息样式 */}
        {isUser ? (
          <div className="bg-gray-100 text-gray-900 rounded-2xl rounded-br-md px-4 py-3">
            <p className="whitespace-pre-wrap leading-relaxed text-base">{message.content}</p>
          </div>
        ) : (
          /* AI消息样式 */
          <div className="flex justify-start group">
            <div className="flex-1">
              
              {/* 消息内容 */}
              <div className="bg-white rounded-2xl rounded-tl-md">
                <div className="p-4">
                  <div className="prose prose-gray max-w-none">
                    {message.content ? (
                      <>
                        <ReactMarkdown
                          components={{
                            code({ className, children, ...props }: any) {
                              const match = /language-(\w+)/.exec(className || '');
                              const inline = !match;
                              return !inline && match ? (
                                <SyntaxHighlighter
                                  style={oneLight as any}
                                  language={match[1]}
                                  PreTag="div"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                              ) : (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              );
                            },
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                        {message.isTyping && (
                          <div className="inline-flex items-center mt-3">
                            <span className="inline-typing-indicator">
                              <span className="typing-dot" style={{ animationDelay: '0ms' }}></span>
                              <span className="typing-dot" style={{ animationDelay: '150ms' }}></span>
                              <span className="typing-dot" style={{ animationDelay: '300ms' }}></span>
                            </span>
                          </div>
                        )}
                      </>
                    ) : (
                      message.isTyping ? (
                        <div className="inline-flex items-center">
                          <span className="inline-typing-indicator">
                            <span className="typing-dot" style={{ animationDelay: '0ms' }}></span>
                            <span className="typing-dot" style={{ animationDelay: '150ms' }}></span>
                            <span className="typing-dot" style={{ animationDelay: '300ms' }}></span>
                          </span>
                        </div>
                      ) : (
                        <p className="text-gray-500 italic">消息内容为空</p>
                      )
                    )}
                  </div>
                  
                  {/* 参考来源 */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-4 pt-4">
                      <p className="text-xs text-gray-500 mb-2 font-medium">参考来源：</p>
                      <div className="space-y-1">
                        {message.sources.map((source, index) => (
                          <a
                            key={index}
                            href={source}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 hover:text-blue-800 truncate block hover:underline"
                          >
                            {source}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* 操作按钮 - 与文字内容对齐 */}
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-start mt-4">
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={handleLike}
                        className={`p-2 rounded-lg transition-all duration-200 hover:bg-gray-100 ${
                          liked ? 'text-blue-600' : 'text-gray-500 hover:text-blue-600'
                        }`}
                        title="点赞"
                      >
                        <ThumbsUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleDislike}
                        className={`p-2 rounded-lg transition-all duration-200 hover:bg-gray-100 ${
                          disliked ? 'text-red-600' : 'text-gray-500 hover:text-red-600'
                        }`}
                        title="点踩"
                      >
                        <ThumbsDown className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleCopy}
                        className={`p-2 rounded-lg transition-all duration-200 hover:bg-gray-100 ${
                          copied ? 'text-green-600' : 'text-gray-500 hover:text-green-600'
                        }`}
                        title={copied ? '已复制' : '复制'}
                      >
                        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
