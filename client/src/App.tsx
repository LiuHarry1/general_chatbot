import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import LoginForm from './components/LoginForm';
import { ChatMessage, Conversation, Attachment, User } from './types';
import { sendMessageStream } from './services/api';
import { useConversation } from './hooks/useConversation';
import { useAuth } from './hooks/useAuth';

const App: React.FC = () => {
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [currentAttachments, setCurrentAttachments] = useState<Attachment[]>([]);
  
  // 使用认证管理hook
  const { user, isAuthenticated, isLoading: authLoading, login, logout } = useAuth();
  
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
  } = useConversation(user?.id);


  const handleSendMessage = async (content: string, attachments?: Attachment[]) => {
    if (!content.trim() && (!attachments || attachments.length === 0)) return;

    // 使用传入的附件或当前持久化的附件
    const messageAttachments = attachments || currentAttachments;

    // 保存添加用户消息前的消息数量，用于判断是否需要更新对话标题
    const messagesBeforeUserMessage = messages;

    // 添加用户消息到数据库
    const userMessage = await addMessage({
      role: 'user',
      content,
      attachments: messageAttachments
    });

    if (!userMessage) {
      console.error('添加用户消息失败');
      return;
    }

    // 创建AI消息的初始状态
    const botMessage = await addMessage({
      role: 'assistant',
      content: '',
      intent: undefined,
      sources: [],
      isTyping: true  // 标记为正在输入状态
    });

    if (!botMessage) {
      console.error('创建AI消息失败');
      return;
    }

    // 用于累积流式内容
    let accumulatedContent = '';
    
    try {
      await sendMessageStream(
        {
          message: content,
          conversationId: currentConversationId || '1',
          attachments: messageAttachments
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
              intent: metadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
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
        },
        // onImage - 处理图片
        (image: { url: string; filename: string }) => {
          if (botMessage) {
            // 确保图片URL是完整的URL，使用API服务器的地址
            let fullImageUrl;
            if (image.url.startsWith('http')) {
              fullImageUrl = image.url;
            } else {
              // 使用API服务器的地址而不是前端地址
              const apiBaseUrl = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';
              const apiServerUrl = apiBaseUrl.replace('/api', ''); // 移除/api后缀
              fullImageUrl = `${apiServerUrl}${image.url}`;
            }
            // 将图片添加到消息内容中
            const imageMarkdown = `\n\n![${image.filename}](${fullImageUrl})`;
            accumulatedContent += imageMarkdown;
            updateMessage(botMessage.id, { 
              content: accumulatedContent,
              isTyping: true // 继续loading，等待更多内容
            }, false); // 不保存到数据库，只更新本地状态
          }
        },
        // userId - 传递用户ID
        user?.id
      );
      
      // 更新对话标题（如果是第一条消息）
      // 注意：这里检查的是添加用户消息前的消息数量
      if (messagesBeforeUserMessage.length === 0 && currentConversationId) {
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
    try {
      await createNewConversation();
      setCurrentAttachments([]); // 新对话时清空附件
    } catch (error) {
      console.error('创建新对话失败:', error);
      // 可以显示错误提示给用户
    }
  };

  const handleSelectConversation = async (conversationId: string) => {
    await selectConversation(conversationId);
    setCurrentAttachments([]); // 切换对话时清空附件
  };

  const handleDeleteConversation = async (conversationId: string) => {
    await deleteConversation(conversationId);
  };

  const handleLogin = (userData: User) => {
    login(userData);
    // 登录后重新初始化对话数据
    // useConversation hook 会自动根据新的 userId 重新加载数据
  };

  const handleLogout = () => {
    logout();
  };

  // 如果正在加载认证状态，显示加载界面
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  // 如果未登录，显示登录界面
  if (!isAuthenticated) {
    return <LoginForm onLogin={handleLogin} />;
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-gray-100 overflow-hidden">
      {/* 侧边栏 */}
      {sidebarVisible && (
        <div className="w-64 flex-shrink-0">
          <Sidebar
            conversations={conversations}
            currentConversationId={currentConversationId}
            onNewConversation={handleNewConversation}
            onSelectConversation={handleSelectConversation}
            onDeleteConversation={handleDeleteConversation}
          />
        </div>
      )}
      
      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部导航栏 */}
        <header className="bg-white/80 backdrop-blur-sm px-4 py-2 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarVisible(!sidebarVisible)}
              className="p-2.5 hover:bg-gray-100 rounded-xl transition-all duration-200 hover:scale-105"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
          
          {/* 用户信息和操作 */}
          <div className="flex items-center space-x-4">
            {/* 状态指示器 */}
            <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 rounded-full">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-xs font-medium text-green-700">在线</span>
            </div>
            
            {/* 用户头像和信息 */}
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-700 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-sm font-semibold">
                  {user?.username?.charAt(0).toUpperCase() || 'U'}
                </span>
              </div>
              <div className="hidden sm:block">
                <p className="text-sm font-medium text-gray-900">{user?.username}</p>
                <p className="text-xs text-gray-500">智能助手用户</p>
              </div>
            </div>
            
            {/* 操作按钮 */}
            <div className="flex items-center space-x-2">
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-all duration-200"
              >
                退出
              </button>
            </div>
          </div>
        </header>

        {/* 聊天内容区域 */}
        <main className="flex-1 flex flex-col min-h-0">
          <ChatArea messages={messages} isLoading={isLoading} />
          <InputArea 
            onSendMessage={handleSendMessage} 
            attachments={currentAttachments}
            onAttachmentsChange={handleAttachmentsChange}
          />
        </main>
      </div>
    </div>
  );
};

export default App;
