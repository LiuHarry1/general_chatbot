import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '../types';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import { Bot, Sparkles, Search, FileText, Code, Lightbulb, Zap } from 'lucide-react';

interface ChatAreaProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

const ChatArea: React.FC<ChatAreaProps> = ({ messages, isLoading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-5xl mx-auto px-8 pt-2 pb-0">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            {/* 主Logo和欢迎信息 */}
            <div className="mb-8">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-300 to-purple-400 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                <Bot className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                欢迎使用 AI 智能助手
              </h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed">
                我是您的智能对话伙伴，可以帮您解答问题、分析文档、搜索信息，还能协助编程和创意写作。
              </p>
            </div>

            {/* 功能卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl mx-auto mb-6">
              <div className="group bg-white p-4 rounded-2xl border border-gray-200 hover:border-blue-300 hover:shadow-lg transition-all duration-300 cursor-pointer">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center mb-4 mx-auto group-hover:scale-110 transition-transform duration-300">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">智能对话</h3>
                <p className="text-sm text-gray-600 leading-relaxed">与我进行自然对话，我会记住我们的交流历史，提供个性化的回答。</p>
              </div>
              
              <div className="group bg-white p-4 rounded-2xl border border-gray-200 hover:border-green-300 hover:shadow-lg transition-all duration-300 cursor-pointer">
                <div className="w-12 h-12 bg-gradient-to-br from-green-600 to-green-700 rounded-xl flex items-center justify-center mb-4 mx-auto group-hover:scale-110 transition-transform duration-300">
                  <Search className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">网络搜索</h3>
                <p className="text-sm text-gray-600 leading-relaxed">搜索互联网获取最新信息，为您提供实时、准确的数据和资讯。</p>
              </div>
              
              <div className="group bg-white p-4 rounded-2xl border border-gray-200 hover:border-purple-300 hover:shadow-lg transition-all duration-300 cursor-pointer">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-purple-700 rounded-xl flex items-center justify-center mb-4 mx-auto group-hover:scale-110 transition-transform duration-300">
                  <FileText className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">文档分析</h3>
                <p className="text-sm text-gray-600 leading-relaxed">上传PDF、Word等文档，我可以帮您总结、分析和提取关键信息。</p>
              </div>
              
              <div className="group bg-white p-4 rounded-2xl border border-gray-200 hover:border-orange-300 hover:shadow-lg transition-all duration-300 cursor-pointer">
                <div className="w-12 h-12 bg-gradient-to-br from-orange-600 to-orange-700 rounded-xl flex items-center justify-center mb-4 mx-auto group-hover:scale-110 transition-transform duration-300">
                  <Code className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">编程助手</h3>
                <p className="text-sm text-gray-600 leading-relaxed">协助您编写、调试和优化代码，支持多种编程语言和框架。</p>
              </div>
              
              <div className="group bg-white p-4 rounded-2xl border border-gray-200 hover:border-pink-300 hover:shadow-lg transition-all duration-300 cursor-pointer">
                <div className="w-12 h-12 bg-gradient-to-br from-pink-600 to-pink-700 rounded-xl flex items-center justify-center mb-4 mx-auto group-hover:scale-110 transition-transform duration-300">
                  <Lightbulb className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">创意写作</h3>
                <p className="text-sm text-gray-600 leading-relaxed">协助您进行创意写作，包括文章、故事、诗歌等各种文体创作。</p>
              </div>
              
              <div className="group bg-white p-4 rounded-2xl border border-gray-200 hover:border-indigo-300 hover:shadow-lg transition-all duration-300 cursor-pointer">
                <div className="w-12 h-12 bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-xl flex items-center justify-center mb-4 mx-auto group-hover:scale-110 transition-transform duration-300">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">快速响应</h3>
                <p className="text-sm text-gray-600 leading-relaxed">快速理解您的需求，提供准确、有用的回答和建议。</p>
              </div>
            </div>

            {/* 开始对话提示 */}
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-4 max-w-2xl mx-auto">
              <div className="flex items-center justify-center space-x-2 mb-3">
                <Sparkles className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-semibold text-blue-800">开始您的智能对话之旅</span>
              </div>
              <p className="text-sm text-gray-700">
                在下方输入框中输入您的问题或需求，我会立即为您提供帮助。您也可以尝试说"帮我写一篇文章"或"分析这个文档"。
              </p>
            </div>
          </div>
        ) : (
            <div className="space-y-3">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatArea;


