import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import { ChatMessage, Conversation, Attachment } from './types';
import { sendMessageStream } from './services/api';
import { useConversation } from './hooks/useConversation';

const App: React.FC = () => {
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [currentAttachments, setCurrentAttachments] = useState<Attachment[]>([]);
  
  // 使用对话管理hook
  const {
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
  } = useConversation();


  const handleSendMessage = async (content: string, attachments?: Attachment[]) => {
    if (!content.trim() && (!attachments || attachments.length === 0)) return;

    // 使用传入的附件或当前持久化的附件
    const messageAttachments = attachments || currentAttachments;

    // 添加用户消息到数据库
    const userMessage = await addMessage({
      role: 'user',
      content,
      attachments: messageAttachments
    });

    // 创建AI消息的初始状态
    const botMessage = await addMessage({
      role: 'assistant',
      content: '',
      intent: undefined,
      sources: [],
      isTyping: true  // 标记为正在输入状态
    });

    // 用于累积流式内容
    let accumulatedContent = '';
    
    try {
      await sendMessageStream(
        {
          message: content,
          conversationId: currentConversationId || '1',
          attachments: messageAttachments,
          user_id: 'default_user' // 用户ID现在由后端处理
        },
        // onChunk - 处理内容块
        (chunk: string) => {
          if (botMessage) {
            accumulatedContent += chunk;
            updateMessage(botMessage.id, { 
              content: accumulatedContent,
              isTyping: true // 保持loading状态，直到流式输出结束
            }, false); // 不保存到数据库，只更新本地状态
          }
        },
        // onMetadata - 处理元数据
        (metadata) => {
          if (botMessage) {
            updateMessage(botMessage.id, {
              intent: metadata.intent as 'normal' | 'web' | 'file' | 'search' | undefined,
              sources: metadata.sources,
              isTyping: true // 保持loading状态，直到流式输出结束
            }, false); // 不保存到数据库，只更新本地状态
          }
        },
        // onError - 处理错误
        (error: string) => {
          if (botMessage) {
            updateMessage(botMessage.id, { 
              content: `错误: ${error}`, 
              isTyping: false 
            }, true); // 错误时保存到数据库
          }
        },
        // onEnd - 流结束
        () => {
          if (botMessage) {
            updateMessage(botMessage.id, { 
              content: accumulatedContent,
              isTyping: false 
            }, true); // 结束时保存到数据库
          }
        }
      );
      
      // 更新对话标题（如果是第一条消息）
      if (messages.length === 0 && currentConversationId) {
        const conversationTitle = content.length > 30 ? content.substring(0, 30) + '...' : content;
        try {
          await updateConversation(currentConversationId, conversationTitle);
        } catch (error) {
          console.error('更新对话标题失败:', error);
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      if (botMessage) {
        updateMessage(botMessage.id, { 
          content: '抱歉，我遇到了一个错误。请稍后重试。', 
          isTyping: false 
        });
      }
    }
  };

  const handleAttachmentsChange = (attachments: Attachment[]) => {
    setCurrentAttachments(attachments);
  };

  const handleNewConversation = async () => {
    await createNewConversation();
    setCurrentAttachments([]); // 新对话时清空附件
  };

  const handleSelectConversation = async (conversationId: string) => {
    await selectConversation(conversationId);
    setCurrentAttachments([]); // 切换对话时清空附件
  };

  const handleDeleteConversation = async (conversationId: string) => {
    await deleteConversation(conversationId);
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
