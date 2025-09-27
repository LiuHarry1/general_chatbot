import React from 'react';
import { ChatMessage, FileAttachment, UrlAttachment } from '../types';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Globe, FileText, MessageCircle, Search } from 'lucide-react';

interface MessageBubbleProps {
  message: ChatMessage;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getIntentIcon = (intent?: string) => {
    switch (intent) {
      case 'web':
        return <Globe className="w-4 h-4" />;
      case 'file':
        return <FileText className="w-4 h-4" />;
      case 'search':
        return <Search className="w-4 h-4" />;
      default:
        return <MessageCircle className="w-4 h-4" />;
    }
  };

  const getIntentColor = (intent?: string) => {
    switch (intent) {
      case 'web':
        return 'intent-web';
      case 'file':
        return 'intent-file';
      case 'search':
        return 'intent-search';
      default:
        return 'intent-normal';
    }
  };

  const getIntentText = (intent?: string) => {
    switch (intent) {
      case 'web':
        return '网页分析';
      case 'file':
        return '文档分析';
      case 'search':
        return '网络搜索';
      default:
        return '对话';
    }
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-3xl ${isUser ? 'order-2' : 'order-1'}`}>
        {!isUser && message.intent && (
          <div className="flex items-center space-x-2 mb-1">
            <div className={`intent-badge ${getIntentColor(message.intent)}`}>
              {getIntentIcon(message.intent)}
              <span className="ml-1">{getIntentText(message.intent)}</span>
            </div>
          </div>
        )}
        
        <div
          className={`chat-message ${
            isUser ? 'user-message' : 'bot-message'
          }`}
        >
          {message.attachments && message.attachments.length > 0 && (
            <div className="mb-2 space-y-1">
              {message.attachments.map((attachment, index) => (
                <div key={index} className="attachment-item">
                  <div className="flex items-center space-x-2">
                    {attachment.type === 'file' ? (
                      <FileText className="w-3 h-3 text-blue-500" />
                    ) : (
                      <Globe className="w-3 h-3 text-green-500" />
                    )}
                    <span className="text-xs font-medium">
                      {attachment.type === 'file' 
                        ? (attachment.data as FileAttachment).name 
                        : (attachment.data as UrlAttachment).url
                      }
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          <div className={isUser ? "text-content" : "markdown-content"}>
            {isUser ? (
              <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
            ) : (
              <ReactMarkdown
                components={{
                  code({ className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || '');
                    const inline = !match;
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={tomorrow as any}
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
            )}
          </div>
          
          {/* Sources */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-200">
              <p className="text-xs text-gray-500 mb-1">参考来源：</p>
              <div className="space-y-1">
                {message.sources.map((source, index) => (
                  <a
                    key={index}
                    href={source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:text-blue-800 truncate block"
                  >
                    {source}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
