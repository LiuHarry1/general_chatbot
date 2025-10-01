/**
 * 数据库存储服务
 * 使用后端数据库API保存对话和消息数据
 */
import { Conversation, ChatMessage } from '../types';
import {
  createConversation,
  getConversations,
  updateConversation,
  deleteConversation,
  createMessage,
  getMessages,
  updateMessage
} from '../services/api';

export class DatabaseStorage {
  /**
   * 获取用户ID
   */
  private static getUserId(): string {
    const storedUser = localStorage.getItem('currentUser');
    if (storedUser) {
      try {
        const userData = JSON.parse(storedUser);
        return userData.id;
      } catch (error) {
        console.error('解析用户数据失败:', error);
      }
    }
    return 'default_user';
  }

  /**
   * 解析日期字符串
   */
  private static parseDate(dateString: string | undefined): Date {
    // 处理undefined或null值
    if (!dateString) {
      // 静默处理，不输出警告，因为这是正常情况
      return new Date(); // 返回当前时间作为fallback
    }
    
    try {
      // 尝试解析ISO格式日期
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        console.warn('Invalid date string:', dateString);
        return new Date(); // 返回当前时间作为fallback
      }
      return date;
    } catch (error) {
      console.error('Date parsing error:', error);
      return new Date(); // 返回当前时间作为fallback
    }
  }

  /**
   * 获取对话列表
   */
  static async getConversations(userId?: string): Promise<Conversation[]> {
    try {
      const currentUserId = userId || this.getUserId();
      const conversations = await getConversations(currentUserId);
      
      // 转换日期格式和字段名
      return conversations.map((conv): Conversation => ({
        id: conv.id,
        title: conv.title,
        createdAt: this.parseDate(conv.createdAt),
        updatedAt: this.parseDate(conv.updatedAt),
        messageCount: conv.messageCount || 0,
        lastMessage: conv.lastMessage,
        lastMessageTime: conv.lastMessageTime ? this.parseDate(conv.lastMessageTime) : undefined
      }));
    } catch (error) {
      console.error('获取对话列表失败:', error);
      return [];
    }
  }

  /**
   * 创建新对话
   */
  static async createConversation(title: string = 'New Conversation', userId?: string): Promise<Conversation> {
    try {
      const currentUserId = userId || this.getUserId();
      const conversation = await createConversation(title, currentUserId);
      
      return {
        id: conversation.id,
        title: conversation.title,
        createdAt: this.parseDate(conversation.createdAt),
        updatedAt: this.parseDate(conversation.updatedAt),
        messageCount: conversation.messageCount || 0,
        lastMessage: conversation.lastMessage,
        lastMessageTime: conversation.lastMessageTime ? this.parseDate(conversation.lastMessageTime) : undefined
      };
    } catch (error) {
      console.error('创建对话失败:', error);
      throw error;
    }
  }


  /**
   * 更新对话标题
   */
  static async updateConversation(conversationId: string, title: string): Promise<Conversation> {
    try {
      const conversation = await updateConversation(conversationId, title);
      
      return {
        id: conversation.id,
        title: conversation.title,
        createdAt: this.parseDate(conversation.createdAt),
        updatedAt: this.parseDate(conversation.updatedAt),
        messageCount: conversation.messageCount || 0,
        lastMessage: conversation.lastMessage,
        lastMessageTime: conversation.lastMessageTime ? this.parseDate(conversation.lastMessageTime) : undefined
      };
    } catch (error) {
      console.error('更新对话失败:', error);
      throw error;
    }
  }

  /**
   * 删除对话
   */
  static async deleteConversation(conversationId: string): Promise<void> {
    try {
      await deleteConversation(conversationId);
    } catch (error) {
      console.error('删除对话失败:', error);
      throw error;
    }
  }

  /**
   * 获取对话的所有消息
   */
  static async getMessages(conversationId: string): Promise<ChatMessage[]> {
    try {
      const messages = await getMessages(conversationId);
      
      // 转换日期格式和字段名
      return messages.map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        created_at: this.parseDate(msg.created_at),
        attachments: msg.attachments,
        intent: msg.intent,
        sources: msg.sources,
        isTyping: false // 历史消息不应该显示为正在输入状态
      }));
    } catch (error) {
      console.error('获取消息失败:', error);
      return [];
    }
  }

  /**
   * 创建新消息
   */
  static async createMessage(message: {
    conversationId: string;
    role: 'user' | 'assistant';
    content: string;
    intent?: string;
    sources?: string[];
    attachments?: any[];
    isTyping?: boolean;
  }): Promise<ChatMessage> {
    try {
      const newMessage = await createMessage({
        conversation_id: message.conversationId,
        role: message.role,
        content: message.content,
        intent: message.intent,
        sources: message.sources,
        attachments: message.attachments,
        is_typing: message.isTyping
      });

      return {
        id: newMessage.id,
        conversationId: message.conversationId,
        role: newMessage.role,
        content: newMessage.content,
        created_at: this.parseDate(newMessage.created_at),
        attachments: newMessage.attachments,
        intent: newMessage.intent,
        sources: newMessage.sources,
        isTyping: newMessage.is_typing
      } as ChatMessage;
    } catch (error) {
      console.error('创建消息失败:', error);
      throw error;
    }
  }

  /**
   * 更新消息
   */
  static async updateMessage(messageId: string, updates: {
    content?: string;
    intent?: string;
    sources?: string[];
    attachments?: any[];
    isTyping?: boolean;
  }): Promise<ChatMessage> {
    try {
      // 映射字段名以匹配API期望的格式
      const apiUpdates = {
        content: updates.content,
        intent: updates.intent,
        sources: updates.sources,
        attachments: updates.attachments,
        is_typing: updates.isTyping
      };
      
      const message = await updateMessage(messageId, apiUpdates);
      
      return {
        id: message.id,
        role: message.role,
        content: message.content,
        created_at: this.parseDate(message.created_at),
        attachments: message.attachments,
        intent: message.intent,
        sources: message.sources,
        isTyping: message.is_typing
      };
    } catch (error) {
      console.error('更新消息失败:', error);
      throw error;
    }
  }

}
