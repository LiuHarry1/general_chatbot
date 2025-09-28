/**
 * 对话持久化工具
 * 使用localStorage保存对话和消息数据
 */
import { Conversation, ChatMessage } from '../types';

const CONVERSATIONS_KEY = 'chatbot_conversations';
const MESSAGES_KEY_PREFIX = 'chatbot_messages_';

export class ConversationStorage {
  /**
   * 保存对话列表
   */
  static saveConversations(conversations: Conversation[]): void {
    try {
      const data = conversations.map(conv => ({
        ...conv,
        createdAt: conv.createdAt.toISOString(),
        updatedAt: conv.updatedAt.toISOString()
      }));
      localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(data));
    } catch (error) {
      console.error('保存对话列表失败:', error);
    }
  }

  /**
   * 获取对话列表
   */
  static getConversations(): Conversation[] {
    try {
      const data = localStorage.getItem(CONVERSATIONS_KEY);
      if (!data) return [];
      
      const conversations = JSON.parse(data);
      return conversations.map((conv: any) => ({
        ...conv,
        createdAt: new Date(conv.createdAt),
        updatedAt: new Date(conv.updatedAt)
      }));
    } catch (error) {
      console.error('获取对话列表失败:', error);
      return [];
    }
  }

  /**
   * 保存单个对话的消息
   */
  static saveMessages(conversationId: string, messages: ChatMessage[]): void {
    try {
      const data = messages.map(msg => ({
        ...msg,
        timestamp: msg.timestamp.toISOString()
      }));
      localStorage.setItem(`${MESSAGES_KEY_PREFIX}${conversationId}`, JSON.stringify(data));
    } catch (error) {
      console.error('保存消息失败:', error);
    }
  }

  /**
   * 获取单个对话的消息
   */
  static getMessages(conversationId: string): ChatMessage[] {
    try {
      const data = localStorage.getItem(`${MESSAGES_KEY_PREFIX}${conversationId}`);
      if (!data) return [];
      
      const messages = JSON.parse(data);
      return messages.map((msg: any) => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      }));
    } catch (error) {
      console.error('获取消息失败:', error);
      return [];
    }
  }

  /**
   * 删除对话及其消息
   */
  static deleteConversation(conversationId: string): void {
    try {
      // 删除消息
      localStorage.removeItem(`${MESSAGES_KEY_PREFIX}${conversationId}`);
      
      // 更新对话列表
      const conversations = this.getConversations();
      const updatedConversations = conversations.filter(conv => conv.id !== conversationId);
      this.saveConversations(updatedConversations);
    } catch (error) {
      console.error('删除对话失败:', error);
    }
  }

  /**
   * 清空所有数据
   */
  static clearAll(): void {
    try {
      // 清空对话列表
      localStorage.removeItem(CONVERSATIONS_KEY);
      
      // 清空所有消息
      const conversations = this.getConversations();
      conversations.forEach(conv => {
        localStorage.removeItem(`${MESSAGES_KEY_PREFIX}${conv.id}`);
      });
    } catch (error) {
      console.error('清空数据失败:', error);
    }
  }

  /**
   * 获取存储使用情况
   */
  static getStorageInfo(): { conversations: number; totalSize: string } {
    try {
      const conversations = this.getConversations();
      let totalSize = 0;
      
      conversations.forEach(conv => {
        const messagesData = localStorage.getItem(`${MESSAGES_KEY_PREFIX}${conv.id}`);
        if (messagesData) {
          totalSize += messagesData.length;
        }
      });
      
      const conversationsData = localStorage.getItem(CONVERSATIONS_KEY);
      if (conversationsData) {
        totalSize += conversationsData.length;
      }
      
      return {
        conversations: conversations.length,
        totalSize: this.formatBytes(totalSize)
      };
    } catch (error) {
      console.error('获取存储信息失败:', error);
      return { conversations: 0, totalSize: '0 B' };
    }
  }

  /**
   * 格式化字节数
   */
  private static formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}
