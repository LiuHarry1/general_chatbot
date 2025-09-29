export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachments?: Attachment[];
  intent?: 'normal' | 'web' | 'file' | 'search' | 'code';
  sources?: string[];
  isTyping?: boolean;
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
  timestamp?: string;
}

export interface IntentIndicator {
  type: 'file' | 'web' | 'search' | 'normal';
  label: string;
  icon: string;
  color: string;
}

export interface SendMessageRequest {
  message: string;
  conversationId: string;
  attachments?: Attachment[];
  user_id?: string;
}