import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import { ChatMessage, Conversation, Attachment } from './types';
import { sendMessage } from './services/api';

const App: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [currentAttachments, setCurrentAttachments] = useState<Attachment[]>([]);

  // Initialize with a default conversation
  useEffect(() => {
    const defaultConversation: Conversation = {
      id: '1',
      title: 'New Conversation',
      createdAt: new Date(),
      updatedAt: new Date()
    };
    setConversations([defaultConversation]);
    setCurrentConversationId('1');
  }, []);

  const handleSendMessage = async (content: string, attachments?: Attachment[]) => {
    if (!content.trim() && (!attachments || attachments.length === 0)) return;

    // 使用传入的附件或当前持久化的附件
    const messageAttachments = attachments || currentAttachments;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
      attachments: messageAttachments
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendMessage({
        message: content,
        conversationId: currentConversationId || '1',
        attachments: messageAttachments
      });

      const botMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
        intent: response.intent,
        sources: response.sources
      };

      setMessages(prev => [...prev, botMessage]);
      
      // 更新对话标题（如果是第一条消息）
      if (messages.length === 0) {
        const conversationTitle = content.length > 30 ? content.substring(0, 30) + '...' : content;
        setConversations(prev => prev.map(conv => 
          conv.id === currentConversationId 
            ? { ...conv, title: conversationTitle, lastMessage: content }
            : conv
        ));
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '抱歉，我遇到了一个错误。请稍后重试。',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAttachmentsChange = (attachments: Attachment[]) => {
    setCurrentAttachments(attachments);
  };

  const handleNewConversation = () => {
    const newConversation: Conversation = {
      id: Date.now().toString(),
      title: 'New Conversation',
      createdAt: new Date(),
      updatedAt: new Date()
    };
    setConversations(prev => [newConversation, ...prev]);
    setCurrentConversationId(newConversation.id);
    setMessages([]);
    setCurrentAttachments([]); // 新对话时清空附件
  };

  const handleSelectConversation = (conversationId: string) => {
    setCurrentConversationId(conversationId);
    // In a real app, you would load messages for this conversation
    setMessages([]);
    setCurrentAttachments([]); // 切换对话时清空附件
  };

  const handleDeleteConversation = (conversationId: string) => {
    setConversations(prev => prev.filter(conv => conv.id !== conversationId));
    if (currentConversationId === conversationId) {
      const remaining = conversations.filter(conv => conv.id !== conversationId);
      if (remaining.length > 0) {
        setCurrentConversationId(remaining[0].id);
        setMessages([]);
      } else {
        handleNewConversation();
      }
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {sidebarVisible && (
        <Sidebar
          conversations={conversations}
          currentConversationId={currentConversationId}
          onNewConversation={handleNewConversation}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
        />
      )}
      
      <div className={`flex-1 flex flex-col chat-container ${!sidebarVisible ? 'mx-auto max-w-6xl' : ''}`}>
        <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setSidebarVisible(!sidebarVisible)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-lg font-semibold text-gray-900">AI 助手</h1>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
              <span className="text-white text-sm font-medium">U</span>
            </div>
          </div>
        </div>

        <ChatArea messages={messages} isLoading={isLoading} />
        <InputArea 
          onSendMessage={handleSendMessage} 
          attachments={currentAttachments}
          onAttachmentsChange={handleAttachmentsChange}
        />
      </div>
    </div>
  );
};

export default App;
