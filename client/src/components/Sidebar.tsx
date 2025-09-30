import React from 'react';
import { Conversation } from '../types';
import { Plus, MessageSquare, Trash2, Sparkles, Bot, Star, Clock, MoreHorizontal } from 'lucide-react';

interface SidebarProps {
  conversations: Conversation[];
  currentConversationId: string | null;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  currentConversationId,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation
}) => {
  const formatDate = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="w-full sidebar bg-white/95 backdrop-blur-sm border-r border-gray-200/60 flex flex-col h-full shadow-xl">
      {/* Logo和标题区域 */}
      <div className="p-6 border-b border-gray-200/60">
        <div className="flex items-center space-x-4 mb-6">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-purple-700 rounded-2xl flex items-center justify-center shadow-lg">
            <Bot className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">AI助手</h1>
            <p className="text-sm text-gray-500">智能对话伙伴</p>
          </div>
        </div>
        
               {/* 新对话按钮 */}
               <button
                 onClick={onNewConversation}
                 className="w-full flex items-center space-x-3 px-3 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200 group"
               >
                 <svg className="w-4 h-4 text-gray-600 group-hover:text-gray-800" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                 </svg>
                 <span className="text-sm font-medium">开始新对话</span>
               </button>
      </div>

      {/* 快速功能区域 */}
      <div className="p-6 border-b border-gray-200/60">
        <h3 className="text-sm font-semibold text-gray-500 mb-4">
          快速功能
        </h3>
        <div className="space-y-1">
          <button className="w-full flex items-center space-x-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200 group">
            <MessageSquare className="w-4 h-4 text-gray-600 group-hover:text-gray-800" />
            <span>文档分析</span>
          </button>
          <button className="w-full flex items-center space-x-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200 group">
            <Sparkles className="w-4 h-4 text-gray-600 group-hover:text-gray-800" />
            <span>创意写作</span>
          </button>
          <button className="w-full flex items-center space-x-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200 group">
            <Bot className="w-4 h-4 text-gray-600 group-hover:text-gray-800" />
            <span>代码助手</span>
          </button>
          <button className="w-full flex items-center space-x-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200 group">
            <MoreHorizontal className="w-4 h-4 text-gray-600 group-hover:text-gray-800" />
            <span>更多</span>
          </button>
        </div>
      </div>

      {/* 对话历史区域 */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-semibold text-gray-700 flex items-center space-x-3">
              <div className="w-1 h-4 bg-gradient-to-b from-blue-500 to-purple-600 rounded-full"></div>
              <Clock className="w-4 h-4" />
              <span>对话历史</span>
            </h3>
            <span className="text-xs font-semibold text-white bg-gradient-to-r from-blue-500 to-purple-600 px-3 py-1.5 rounded-full shadow-sm">
              {conversations.length}
            </span>
          </div>
          
          <div className="space-y-1">
            {conversations.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500 mb-2">还没有对话记录</p>
                <p className="text-xs text-gray-400">点击上方按钮开始新对话</p>
              </div>
            ) : (
              conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`group relative p-3 rounded-xl cursor-pointer transition-all duration-200 ${
                    currentConversationId === conversation.id
                      ? 'bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 shadow-sm'
                      : 'hover:bg-gray-50 hover:shadow-sm'
                  }`}
                  onClick={() => onSelectConversation(conversation.id)}
                >
                  <div className="flex items-start space-x-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      currentConversationId === conversation.id
                        ? 'bg-gradient-to-br from-blue-500 to-purple-600'
                        : 'bg-gray-100 group-hover:bg-gray-200'
                    }`}>
                      <MessageSquare className={`w-4 h-4 ${
                        currentConversationId === conversation.id
                          ? 'text-white'
                          : 'text-gray-500'
                      }`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {conversation.title}
                        </p>
                        {(conversation.messageCount || 0) > 0 && (
                          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                            {conversation.messageCount}
                          </span>
                        )}
                      </div>
                      {conversation.lastMessage && (
                        <p className="text-xs text-gray-600 truncate mt-1">
                          {conversation.lastMessage}
                        </p>
                      )}
                      <div className="flex items-center space-x-2 mt-1">
                        <Clock className="w-3 h-3 text-gray-400" />
                        <p className="text-xs text-gray-500">
                          {formatDate(conversation.updatedAt as Date)}
                        </p>
                      </div>
                    </div>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conversation.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-100 rounded-lg transition-all duration-200"
                    >
                      <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 用户信息区域 */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-blue-600 rounded-xl flex items-center justify-center">
            <Star className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">智能助手</p>
            <p className="text-xs text-gray-500 flex items-center space-x-1">
              <div className="w-2 h-2 bg-green-400 rounded-full"></div>
              <span>随时为您服务</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
