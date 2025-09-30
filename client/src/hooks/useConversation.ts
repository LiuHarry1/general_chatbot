/**
 * 对话管理 Hook
 * 封装对话相关的状态管理和业务逻辑
 */
import { useState, useEffect, useCallback } from 'react';
import { Conversation, ChatMessage } from '../types';
import { DatabaseStorage } from '../utils/databaseStorage';

export const useConversation = (userId?: string) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // 初始化对话
  useEffect(() => {
    const initializeConversations = async () => {
      if (!userId) {
        // 如果没有用户ID，清空数据
        setConversations([]);
        setCurrentConversationId(null);
        setMessages([]);
        setIsLoading(false);
        return;
      }
      
      setIsLoading(true);
      try {
        const savedConversations = await DatabaseStorage.getConversations(userId);
        
        if (savedConversations.length > 0) {
          setConversations(savedConversations);
          setCurrentConversationId(savedConversations[0].id);
          
          const firstConversationMessages = await DatabaseStorage.getMessages(savedConversations[0].id);
          setMessages(firstConversationMessages);
        } else {
          // 创建默认对话
          const defaultConversation = await DatabaseStorage.createConversation('New Conversation', userId);
          setConversations([defaultConversation]);
          setCurrentConversationId(defaultConversation.id);
          setMessages([]);
        }
      } catch (error) {
        console.error('初始化对话失败:', error);
        // 如果数据库操作失败，显示空状态
        setConversations([]);
        setCurrentConversationId(null);
        setMessages([]);
      } finally {
        setIsLoading(false);
      }
    };

    initializeConversations();
  }, [userId]);

  // 创建新对话
  const createNewConversation = useCallback(async () => {
    if (!userId) return;
    
    try {
      const newConversation = await DatabaseStorage.createConversation('New Conversation', userId);
      setConversations(prev => [newConversation, ...prev]);
      setCurrentConversationId(newConversation.id);
      setMessages([]);
      return newConversation;
    } catch (error) {
      console.error('创建对话失败:', error);
      throw error; // 直接抛出错误，让调用者处理
    }
  }, [userId]);

  // 选择对话
  const selectConversation = useCallback(async (conversationId: string) => {
    try {
      setCurrentConversationId(conversationId);
      const conversationMessages = await DatabaseStorage.getMessages(conversationId);
      setMessages(conversationMessages);
    } catch (error) {
      console.error('选择对话失败:', error);
      setMessages([]);
    }
  }, []);

  // 删除对话
  const deleteConversation = useCallback(async (conversationId: string) => {
    try {
      await DatabaseStorage.deleteConversation(conversationId);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      
      if (currentConversationId === conversationId) {
        const remainingConversations = conversations.filter(c => c.id !== conversationId);
        if (remainingConversations.length > 0) {
          await selectConversation(remainingConversations[0].id);
        } else {
          await createNewConversation();
        }
      }
    } catch (error) {
      console.error('删除对话失败:', error);
    }
  }, [conversations, currentConversationId, selectConversation, createNewConversation]);

  // 添加消息
  const addMessage = useCallback(async (message: Omit<ChatMessage, 'id' | 'created_at'>) => {
    if (!currentConversationId || !userId) {
      console.error('没有当前对话ID或用户ID');
      return;
    }

    try {
      const newMessage = await DatabaseStorage.createMessage({
        conversationId: currentConversationId,
        role: message.role,
        content: message.content,
        intent: message.intent,
        sources: message.sources,
        attachments: message.attachments,
        isTyping: message.isTyping
      });
      
      setMessages(prev => [...prev, newMessage]);
      return newMessage;
    } catch (error) {
      console.error('添加消息失败:', error);
      throw error; // 直接抛出错误，让调用者处理
    }
  }, [currentConversationId, userId]);

  // 更新消息
  const updateMessage = useCallback(async (messageId: string, updates: Partial<ChatMessage>, saveToDatabase: boolean = true) => {
    // 先更新本地状态
    setMessages(prev => 
      prev.map(msg => 
        msg.id === messageId ? { ...msg, ...updates } : msg
      )
    );

    // 如果需要保存到数据库
    if (saveToDatabase) {
      try {
        const updatedMessage = await DatabaseStorage.updateMessage(messageId, {
          content: updates.content,
          intent: updates.intent,
          sources: updates.sources,
          attachments: updates.attachments,
          isTyping: updates.isTyping
        });
        
        // 用数据库返回的最新数据更新状态
        setMessages(prev => 
          prev.map(msg => 
            msg.id === messageId ? updatedMessage : msg
          )
        );
        return updatedMessage;
      } catch (error) {
        console.error('更新消息失败:', error);
        // 数据库更新失败时，回滚本地状态
        setMessages(prev => 
          prev.map(msg => 
            msg.id === messageId ? { ...msg, ...updates } : msg
          )
        );
        throw error;
      }
    }
    
    // 返回更新后的消息（即使只是本地更新）
    return null; // 本地更新时返回null，调用者可以使用当前状态
  }, []);

  // 更新对话标题
  const updateConversation = useCallback(async (conversationId: string, title: string) => {
    try {
      const updatedConversation = await DatabaseStorage.updateConversation(conversationId, title);
      
      // 更新本地状态
      setConversations(prev => 
        prev.map(conv => 
          conv.id === conversationId ? updatedConversation : conv
        )
      );
      
      return updatedConversation;
    } catch (error) {
      console.error('更新对话标题失败:', error);
      throw error;
    }
  }, []);

  return {
    conversations,
    currentConversationId,
    messages,
    isLoading,
    setIsLoading,
    createNewConversation,
    selectConversation,
    deleteConversation,
    addMessage,
    updateMessage,
    updateConversation
  };
};
