import React from 'react';
import { Conversation } from '../types';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';

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
    <div className="w-80 sidebar">
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          <span>新建对话</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
            最近对话
          </h3>
          
          <div className="space-y-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`group relative p-3 rounded-lg cursor-pointer transition-colors ${
                  currentConversationId === conversation.id
                    ? 'bg-primary-50 border border-primary-200'
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => onSelectConversation(conversation.id)}
              >
                <div className="flex items-start space-x-3">
                  <MessageSquare className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {conversation.title}
                    </p>
                    {conversation.lastMessage && (
                      <p className="text-xs text-gray-600 truncate mt-1">
                        {conversation.lastMessage}
                      </p>
                    )}
                    <p className="text-xs text-gray-500">
                      {formatDate(conversation.updatedAt as Date)}
                    </p>
                  </div>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conversation.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-all"
                  >
                    <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-medium">U</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">用户</p>
            <p className="text-xs text-gray-500">在线</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
