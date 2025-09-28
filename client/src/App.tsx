import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import { ChatMessage, Conversation, Attachment } from './types';
import { sendMessageStream } from './services/api';
import { ConversationStorage } from './utils/conversationStorage';

const App: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [currentAttachments, setCurrentAttachments] = useState<Attachment[]>([]);
  
  // 生成或获取用户ID
  const getUserId = (): string => {
    let userId = localStorage.getItem('chatbot_user_id');
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('chatbot_user_id', userId);
    }
    return userId;
  };

  // Initialize conversations from localStorage
  useEffect(() => {
    const savedConversations = ConversationStorage.getConversations();
    
    if (savedConversations.length > 0) {
      // 加载保存的对话
      setConversations(savedConversations);
      setCurrentConversationId(savedConversations[0].id);
      
      // 加载第一个对话的消息
      const firstConversationMessages = ConversationStorage.getMessages(savedConversations[0].id);
      setMessages(firstConversationMessages);
    } else {
      // 创建默认对话
      const defaultConversation: Conversation = {
        id: Date.now().toString(),
        title: 'New Conversation',
        createdAt: new Date(),
        updatedAt: new Date()
      };
      setConversations([defaultConversation]);
      setCurrentConversationId(defaultConversation.id);
      setMessages([]);
      
      // 保存默认对话
      ConversationStorage.saveConversations([defaultConversation]);
    }
  }, []);

  // Save messages to localStorage when messages change
  useEffect(() => {
    if (currentConversationId && messages.length > 0) {
      ConversationStorage.saveMessages(currentConversationId, messages);
    }
  }, [messages, currentConversationId]);

  // Save conversations to localStorage when conversations change
  useEffect(() => {
    if (conversations.length > 0) {
      ConversationStorage.saveConversations(conversations);
    }
  }, [conversations]);

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

    // 创建AI消息的初始状态
    const botMessageId = (Date.now() + 1).toString();
    const botMessage: ChatMessage = {
      id: botMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      intent: undefined,
      sources: [],
      isTyping: true  // 标记为正在输入状态
    };

    setMessages(prev => [...prev, botMessage]);

    try {
      await sendMessageStream(
        {
          message: content,
          conversationId: currentConversationId || '1',
          attachments: messageAttachments,
          user_id: getUserId()
        },
        // onChunk - 处理内容块
        (chunk: string) => {
          setMessages(prev => prev.map(msg => 
            msg.id === botMessageId 
              ? { ...msg, content: msg.content + chunk, isTyping: false }
              : msg
          ));
        },
        // onMetadata - 处理元数据
        (metadata) => {
          setMessages(prev => prev.map(msg => 
            msg.id === botMessageId 
              ? { 
                  ...msg, 
                  intent: metadata.intent as 'normal' | 'web' | 'file' | 'search' | undefined,
                  sources: metadata.sources,
                  timestamp: metadata.timestamp ? new Date(metadata.timestamp) : msg.timestamp,
                  isTyping: false
                }
              : msg
          ));
        },
        // onError - 处理错误
        (error: string) => {
          setMessages(prev => prev.map(msg => 
            msg.id === botMessageId 
              ? { ...msg, content: `错误: ${error}`, isTyping: false }
              : msg
          ));
        },
        // onEnd - 流结束
        () => {
          setMessages(prev => prev.map(msg => 
            msg.id === botMessageId 
              ? { ...msg, isTyping: false }
              : msg
          ));
        }
      );
      
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
      setMessages(prev => prev.map(msg => 
        msg.id === botMessageId 
          ? { ...msg, content: '抱歉，我遇到了一个错误。请稍后重试。', isTyping: false }
          : msg
      ));
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
    const updatedConversations = [newConversation, ...conversations];
    setConversations(updatedConversations);
    setCurrentConversationId(newConversation.id);
    setMessages([]);
    setCurrentAttachments([]); // 新对话时清空附件
    
    // 保存新对话到localStorage
    ConversationStorage.saveConversations(updatedConversations);
  };

  const handleSelectConversation = (conversationId: string) => {
    setCurrentConversationId(conversationId);
    // 加载对应对话的消息
    const conversationMessages = ConversationStorage.getMessages(conversationId);
    setMessages(conversationMessages);
    setCurrentAttachments([]); // 切换对话时清空附件
  };

  const handleDeleteConversation = (conversationId: string) => {
    // 从localStorage删除对话及其消息
    ConversationStorage.deleteConversation(conversationId);
    
    setConversations(prev => prev.filter(conv => conv.id !== conversationId));
    if (currentConversationId === conversationId) {
      const remaining = conversations.filter(conv => conv.id !== conversationId);
      if (remaining.length > 0) {
        setCurrentConversationId(remaining[0].id);
        const messages = ConversationStorage.getMessages(remaining[0].id);
        setMessages(messages);
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
