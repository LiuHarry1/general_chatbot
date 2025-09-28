/**
 * 对话管理 Hook
 * 封装对话相关的状态管理和业务逻辑
 */
import { useState, useEffect, useCallback } from 'react';
import { Conversation, ChatMessage } from '../types';
import { ConversationStorage } from '../utils/conversationStorage';

export const useConversation = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // 生成或获取用户ID
  const getUserId = useCallback((): string => {
    let userId = localStorage.getItem('chatbot_user_id');
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('chatbot_user_id', userId);
    }
    return userId;
  }, []);

  // 初始化对话
  useEffect(() => {
    const savedConversations = ConversationStorage.getConversations();
    
    if (savedConversations.length > 0) {
      setConversations(savedConversations);
      setCurrentConversationId(savedConversations[0].id);
      
      const firstConversationMessages = ConversationStorage.getMessages(savedConversations[0].id);
      setMessages(firstConversationMessages);
    } else {
      const defaultConversation: Conversation = {
        id: Date.now().toString(),
        title: 'New Conversation',
        createdAt: new Date(),
        updatedAt: new Date()
      };
      setConversations([defaultConversation]);
      setCurrentConversationId(defaultConversation.id);
      setMessages([]);
      ConversationStorage.saveConversations([defaultConversation]);
    }
  }, []);

  // 保存消息
  useEffect(() => {
    if (currentConversationId && messages.length > 0) {
      ConversationStorage.saveMessages(currentConversationId, messages);
    }
  }, [messages, currentConversationId]);

  // 保存对话
  useEffect(() => {
    if (conversations.length > 0) {
      ConversationStorage.saveConversations(conversations);
    }
  }, [conversations]);

  // 创建新对话
  const createNewConversation = useCallback(() => {
    const newConversation: Conversation = {
      id: Date.now().toString(),
      title: 'New Conversation',
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    setConversations(prev => [newConversation, ...prev]);
    setCurrentConversationId(newConversation.id);
    setMessages([]);
    
    return newConversation;
  }, []);

  // 选择对话
  const selectConversation = useCallback((conversationId: string) => {
    const conversation = conversations.find(c => c.id === conversationId);
    if (conversation) {
      setCurrentConversationId(conversationId);
      const conversationMessages = ConversationStorage.getMessages(conversationId);
      setMessages(conversationMessages);
    }
  }, [conversations]);

  // 删除对话
  const deleteConversation = useCallback((conversationId: string) => {
    setConversations(prev => prev.filter(c => c.id !== conversationId));
    
    if (currentConversationId === conversationId) {
      const remainingConversations = conversations.filter(c => c.id !== conversationId);
      if (remainingConversations.length > 0) {
        selectConversation(remainingConversations[0].id);
      } else {
        createNewConversation();
      }
    }
  }, [conversations, currentConversationId, selectConversation, createNewConversation]);

  // 添加消息
  const addMessage = useCallback((message: ChatMessage) => {
    setMessages(prev => [...prev, message]);
  }, []);

  // 更新消息
  const updateMessage = useCallback((messageId: string, updates: Partial<ChatMessage>) => {
    setMessages(prev => 
      prev.map(msg => 
        msg.id === messageId ? { ...msg, ...updates } : msg
      )
    );
  }, []);

  return {
    conversations,
    currentConversationId,
    messages,
    isLoading,
    setIsLoading,
    getUserId,
    createNewConversation,
    selectConversation,
    deleteConversation,
    addMessage,
    updateMessage
  };
};
