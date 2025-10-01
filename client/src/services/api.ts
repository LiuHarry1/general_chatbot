import { SendMessageRequest, ApiResponse, Conversation, ChatMessage } from '../types';
import { API_CONSTANTS } from '../constants';

// API响应的原始数据类型（包含字符串日期）
interface ConversationApiResponse {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  lastMessage?: string;
  lastMessageTime?: string;
  messageCount?: number;
}

interface MessageApiResponse {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: 'normal' | 'web' | 'file' | 'search' | 'code';
  sources?: string[];
  attachments?: any[];
  is_typing: boolean;
  created_at: string;
}


export const sendMessageStream = async (
  request: SendMessageRequest,
  onChunk: (chunk: string) => void,
  onMetadata: (metadata: { intent?: string; sources?: string[]; created_at?: Date }) => void,
  onError: (error: string) => void,
  onEnd: () => void,
  onImage?: (image: { url: string; filename: string }) => void,
  userId?: string
): Promise<void> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...request,
      user_id: userId || 'default_user'
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            switch (data.type) {
              case 'metadata':
                onMetadata({
                  intent: data.intent,
                  sources: data.sources,
                  created_at: data.created_at ? new Date(data.created_at) : undefined
                });
                break;
              case 'content':
                onChunk(data.content);
                break;
              case 'image':
                if (onImage) {
                  onImage({
                    url: data.url,
                    filename: data.filename
                  });
                }
                break;
              case 'end':
                onEnd();
                return;
              case 'error':
                onError(data.error);
                return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};

export const uploadFile = async (file: File): Promise<{ content: string }> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/files/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const analyzeUrl = async (url: string): Promise<{ content: string; title?: string }> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/files/analyze-url`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// 数据库API调用 - 对话管理
export const createConversation = async (title: string, userId: string = 'default_user'): Promise<ConversationApiResponse> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/conversations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title, user_id: userId }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const getConversations = async (userId: string = 'default_user'): Promise<ConversationApiResponse[]> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/conversations?user_id=${userId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const getConversation = async (conversationId: string): Promise<ConversationApiResponse> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/conversations/${conversationId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const updateConversation = async (conversationId: string, title: string): Promise<ConversationApiResponse> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/conversations/${conversationId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title, user_id: 'default_user' }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const deleteConversation = async (conversationId: string): Promise<void> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
};

// 数据库API调用 - 消息管理
export const createMessage = async (message: {
  conversation_id: string;
  role: string;
  content: string;
  intent?: string;
  sources?: string[];
  attachments?: any[];
  is_typing?: boolean;
}): Promise<MessageApiResponse> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(message),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const getMessages = async (conversationId: string): Promise<MessageApiResponse[]> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/messages/conversations/${conversationId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const updateMessage = async (messageId: string, updates: {
  content?: string;
  intent?: string;
  sources?: string[];
  attachments?: any[];
  is_typing?: boolean;
}): Promise<MessageApiResponse> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/messages/${messageId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const deleteMessage = async (messageId: string): Promise<void> => {
  const response = await fetch(`${API_CONSTANTS.BASE_URL}/v1/db/messages/${messageId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
};


