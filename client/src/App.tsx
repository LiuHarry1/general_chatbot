import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import LoginForm from './components/LoginForm';
import { ChatMessage, Conversation, Attachment, User } from './types';
import { sendMessageStream } from './services/api';
import { useConversation } from './hooks/useConversation';
import { useAuth } from './hooks/useAuth';
import { PanelLeftOpen, Bot } from 'lucide-react';

const App: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentAttachments, setCurrentAttachments] = useState<Attachment[]>([]);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [isNewConversation, setIsNewConversation] = useState(true);
  
  // 使用认证管理hook
  const { user, isAuthenticated, isLoading: authLoading, login, logout } = useAuth();

  // 获取动态问候语
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 6) return '夜深了';
    if (hour < 12) return '早上好';
    if (hour < 14) return '中午好';
    if (hour < 18) return '下午好';
    if (hour < 22) return '晚上好';
    return '夜深了';
  };
  
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
    updateConversation,
    resetConversation
  } = useConversation(user?.id);


  const handleSendMessage = async (content: string, attachments?: Attachment[]) => {
    if (!content.trim() && (!attachments || attachments.length === 0)) return;

    // 使用传入的附件或当前持久化的附件
    const messageAttachments = attachments || currentAttachments;

    // 保存添加用户消息前的消息数量，用于判断是否需要更新对话标题
    const messagesBeforeUserMessage = messages;
    
    // 注意：不在这里手动设置 isNewConversation，让 useEffect 统一管理

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
      if (messagesBeforeUserMessage.length === 0 && userMessage?.conversationId) {
        const conversationTitle = content.length > 30 ? content.substring(0, 30) + '...' : content;
        try {
          await updateConversation(userMessage.conversationId, conversationTitle);
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
      // 重置对话状态，不创建空对话
      resetConversation();
      setCurrentAttachments([]); // 新对话时清空附件
      setIsNewConversation(true); // 标记为新对话
    } catch (error) {
      console.error('重置对话状态失败:', error);
      // 可以显示错误提示给用户
    }
  };

  const handleSelectConversation = async (conversationId: string) => {
    await selectConversation(conversationId);
    setCurrentAttachments([]); // 切换对话时清空附件
    // 注意：不在这里手动设置 isNewConversation，让 useEffect 统一管理
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
    setUserDropdownOpen(false);
  };

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest('.user-dropdown')) {
        setUserDropdownOpen(false);
      }
    };

    if (userDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [userDropdownOpen]);

  // 监听消息和对话变化，统一管理新对话状态
  useEffect(() => {
    // 使用 setTimeout 来避免快速状态切换导致的闪现
    const timeoutId = setTimeout(() => {
      // 如果没有对话，显示新对话界面
      if (conversations.length === 0) {
        setIsNewConversation(true);
      }
      // 如果有对话但没有当前对话ID，且没有消息，显示新对话界面
      else if (!currentConversationId && messages.length === 0) {
        setIsNewConversation(true);
      }
      // 如果有消息，则不是新对话
      else if (messages.length > 0) {
        setIsNewConversation(false);
      }
    }, 50); // 50ms 的延迟，足够避免闪现但不会影响用户体验

    return () => clearTimeout(timeoutId);
  }, [conversations, currentConversationId, messages]);

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
      {!sidebarCollapsed && (
        <div className="w-64 flex-shrink-0 transition-all duration-300">
          <Sidebar
            conversations={conversations}
            currentConversationId={currentConversationId}
            onNewConversation={handleNewConversation}
            onSelectConversation={handleSelectConversation}
            onDeleteConversation={handleDeleteConversation}
            isCollapsed={false}
            onToggleCollapse={() => setSidebarCollapsed(true)}
          />
        </div>
      )}
      
      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部导航栏 */}
        <header className="bg-white/80 backdrop-blur-sm px-4 py-2 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* 当侧栏收起时显示展开按钮和新对话按钮 */}
            {sidebarCollapsed && (
              <>
                <button
                  onClick={() => setSidebarCollapsed(false)}
                  className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105 group shadow-sm"
                  title="展开侧栏"
                >
                  <PanelLeftOpen className="w-4 h-4 text-gray-600 group-hover:text-gray-800 transition-colors" />
                </button>
                
                <button
                  onClick={handleNewConversation}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-all duration-200 hover:scale-105 group"
                  title="新对话"
                >
                  <svg className="w-4 h-4 text-blue-600 group-hover:text-blue-800" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                  <span className="text-sm font-medium text-blue-600 group-hover:text-blue-800">新对话</span>
                </button>
              </>
            )}
          </div>
          
          {/* 用户信息和操作 - 始终显示 */}
          <div className="flex items-center space-x-4">
            {/* 状态指示器 */}
            <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 rounded-full">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-xs font-medium text-green-700">在线</span>
            </div>
            
            {/* 用户头像和信息 */}
            <div className="relative user-dropdown">
              <button
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                className="flex items-center space-x-3 hover:bg-gray-50 rounded-lg p-1 transition-colors duration-200"
              >
                <div className="w-10 h-10 bg-gradient-to-br from-blue-300 to-purple-400 rounded-xl flex items-center justify-center shadow-lg">
                  <span className="text-white text-sm font-semibold">
                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                  </span>
                </div>
                <div className="hidden sm:block">
                  <p className="text-sm font-medium text-gray-900">{user?.username}</p>
                </div>
              </button>

              {/* 下拉菜单 */}
              {userDropdownOpen && (
                <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                  <div className="px-4 py-2 border-b border-gray-100">
                    <p className="text-sm font-medium text-gray-900">{user?.username}</p>
                    <p className="text-xs text-gray-500">智能助手用户</p>
                  </div>
                  
                  <div className="py-1">
                    <button className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-200">
                      <svg className="w-4 h-4 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      设置
                    </button>
                    
                    <button className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-200">
                      <svg className="w-4 h-4 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      下载电脑版
                    </button>
                    
                    <button className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-200">
                      <svg className="w-4 h-4 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      下载手机应用
                      <svg className="w-4 h-4 ml-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </div>
                  
                  <div className="border-t border-gray-100 pt-1">
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors duration-200"
                    >
                      <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                      退出登录
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* 聊天内容区域 */}
        <main className="flex-1 flex flex-col min-h-0">
          {isNewConversation ? (
            // 新对话：输入框在中间偏上
            <div className="flex-1 flex flex-col items-center justify-start relative bg-white pt-20">
              <div className="w-full max-w-4xl px-8">
                <div className="text-center mb-8">
                  {/* 图标 */}
                  <div className="w-20 h-20 bg-gradient-to-br from-blue-300 to-purple-400 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                    <Bot className="w-10 h-10 text-white" />
                  </div>
                  {/* 欢迎文字 */}
                  <h2 className="text-3xl font-bold text-gray-900 mb-3">
                    {getGreeting()}, {user?.username || '用户'}
                  </h2>
                </div>
                <InputArea 
                  onSendMessage={handleSendMessage} 
                  attachments={currentAttachments}
                  onAttachmentsChange={handleAttachmentsChange}
                />
              </div>
            </div>
          ) : (
            // 已有对话：正常布局
            <>
              <ChatArea messages={messages} isLoading={isLoading} />
              <InputArea 
                onSendMessage={handleSendMessage} 
                attachments={currentAttachments}
                onAttachmentsChange={handleAttachmentsChange}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;

