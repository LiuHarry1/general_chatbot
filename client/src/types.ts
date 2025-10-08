export interface SearchResult {
  title: string;
  url: string;
  content: string;
  score: number;
  published_date?: string;
}

export interface ChatMessage {
  id: string;
  conversationId?: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: Date;
  attachments?: Attachment[];
  intent?: 'normal' | 'web' | 'file' | 'search' | 'code';
  sources?: string[];
  searchResults?: SearchResult[];
  isTyping?: boolean;
  tempStatus?: string;  // 临时状态消息（不保存到数据库）
}

export interface Attachment {
  type: 'file' | 'url';
  data: FileAttachment | UrlAttachment;
  id: string;
}

export interface FileAttachment {
  name: string;
  size: number;
  type: string;
  content?: string;
  url?: string;
}

export interface UrlAttachment {
  url: string;
  title?: string;
  content?: string;
  favicon?: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount?: number;
  lastMessage?: string;
  lastMessageTime?: Date;
}

export interface ApiResponse {
  content: string;
  intent: 'normal' | 'web' | 'file' | 'search' | 'code';
  sources?: string[];
  created_at?: Date;
}

export interface User {
  id: string;
  username: string;
  loginTime: Date;
}

export interface SendMessageRequest {
  message: string;
  conversationId: string;
  attachments?: Attachment[];
  user_id?: string;
}