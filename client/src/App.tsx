import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import LoginForm from './components/LoginForm';
import LoadingScreen from './components/LoadingScreen';
import Header from './components/Header';
import NewConversationView from './components/NewConversationView';
import SearchResultsSidebar from './components/SearchResultsSidebar';
import { ChatMessage, Attachment, User } from './types';
import { sendMessageStream } from './services/api';
import { useConversation } from './hooks/useConversation';
import { useAuth } from './hooks/useAuth';
import { useClickOutside } from './hooks/useClickOutside';
import { UI_CONSTANTS } from './constants';
import { truncateText, generateId } from './utils/helpers';

const App: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentAttachments, setCurrentAttachments] = useState<Attachment[]>([]);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [isNewConversation, setIsNewConversation] = useState(true);
  const [searchResultsOpen, setSearchResultsOpen] = useState(false);
  const [currentSearchSources, setCurrentSearchSources] = useState<string[]>([]);
  const [currentSearchResults, setCurrentSearchResults] = useState<any[]>([]);
  
  // 使用认证管理hook
  const { user, isAuthenticated, isLoading: authLoading, login, logout } = useAuth();

  // 用户下拉菜单ref
  const userDropdownRef = useRef<HTMLDivElement>(null);
  
  // 使用对话管理hook
  const {
    conversations,
    setConversations,
    currentConversationId,
    setCurrentConversationId,
    messages,
    setMessages,
    isLoading,
    setIsLoading,
    createNewConversation,
    selectConversation,
    deleteConversation,
    updateConversation,
    resetConversation
  } = useConversation(user?.id);


  const handleSendMessage = async (content: string, attachments?: Attachment[]) => {
    if (!content.trim() && (!attachments || attachments.length === 0)) return;

    // 使用传入的附件或当前持久化的附件
    const messageAttachments = attachments || currentAttachments;

    // 保存添加用户消息前的消息数量，用于判断是否需要更新对话标题
    const messagesBeforeUserMessage = messages;
    
    // 如果是新对话（没有currentConversationId），立即创建对话并显示在侧边栏
    let newConversationId: string = currentConversationId || 'temp';
    if (!currentConversationId || currentConversationId === 'temp') {
      try {
        // 创建新对话
        const newConversation = await createNewConversation();
        if (newConversation) {
          newConversationId = newConversation.id;
          // createNewConversation 已经设置了 currentConversationId 和添加到 conversations 列表
        } else {
          throw new Error('Failed to create conversation');
        }
      } catch (error) {
        console.error('创建新对话失败:', error);
        // 如果创建失败，使用temp ID继续
        newConversationId = 'temp';
      }
    }

    // 创建临时的用户消息用于显示（不保存到数据库）
    const tempUserMessage: ChatMessage = {
      id: generateId(),
      conversationId: newConversationId,
      role: 'user',
      content,
      created_at: new Date(),
      attachments: messageAttachments,
      isTyping: false
    };

    // 创建临时的AI消息用于显示（不保存到数据库）
    const tempBotMessage: ChatMessage = {
      id: generateId(),
      conversationId: newConversationId,
      role: 'assistant',
      content: '',
      created_at: new Date(),
      isTyping: true
    };

    // 临时添加到本地状态用于显示
    setMessages(prev => [...prev, tempUserMessage, tempBotMessage]);
    
    // 立即切换到对话视图，因为用户已经开始对话
    setIsNewConversation(false);

    // 用于累积流式内容和保存metadata
    let accumulatedContent = '';
    let savedMetadata: { intent?: string; sources?: string[]; searchResults?: any[] } = {};
    let isStreamEnded = false; // 标记流式响应是否已结束
    
    try {
      await sendMessageStream(
        {
          message: content,
          conversationId: newConversationId,
          attachments: messageAttachments
        },
        // onChunk - 处理内容块
        (chunk: string) => {
          accumulatedContent += chunk;
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempBotMessage.id 
                ? { ...msg, content: accumulatedContent, isTyping: !isStreamEnded }
                : msg
            )
          );
        },
        // onMetadata - 处理元数据
        (metadata) => {
          savedMetadata = {
            intent: metadata.intent,
            sources: metadata.sources,
            searchResults: metadata.search_results
          };
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempBotMessage.id 
                ? { 
                    ...msg, 
                    intent: metadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
                    sources: metadata.sources,
                    searchResults: metadata.search_results,
                    isTyping: true
                  }
                : msg
            )
          );
        },
        // onError - 处理错误
        (error: string) => {
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempBotMessage.id 
                ? { 
                    ...msg, 
                    content: `错误: ${error}`, 
                    isTyping: false,
                    intent: savedMetadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
                    sources: savedMetadata.sources,
                    searchResults: savedMetadata.searchResults
                  }
                : msg
            )
          );
        },
        // onEnd - 流结束
        () => {
          isStreamEnded = true; // 标记流式响应已结束
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempBotMessage.id 
                ? { 
                    ...msg, 
                    content: accumulatedContent,
                    isTyping: false,
                    intent: savedMetadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
                    sources: savedMetadata.sources,
                    searchResults: savedMetadata.searchResults
                  }
                : msg
            )
          );
        },
        // onImage - 处理图片
        (image: { url: string; filename: string }) => {
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
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempBotMessage.id 
                ? { 
                    ...msg, 
                    content: accumulatedContent,
                    isTyping: true
                  }
                : msg
            )
          );
        },
        // onMessageCreated - 处理消息创建完成
        async (data) => {
          // 更新临时消息的ID为服务器返回的真实ID
          setMessages(prev => 
            prev.map(msg => {
              if (msg.id === tempUserMessage.id) {
                return { ...msg, id: data.user_message_id };
              } else if (msg.id === tempBotMessage.id) {
                return { 
                  ...msg, 
                  id: data.ai_message_id,
                  intent: data.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
                  sources: data.sources,
                  isTyping: false  // 消息创建完成后，强制停止typing状态
                };
              }
              return msg;
            })
          );
          
          // 更新对话标题（如果是第一条消息）
          if (messagesBeforeUserMessage.length === 0 && newConversationId) {
            const conversationTitle = truncateText(content, UI_CONSTANTS.MAX_TITLE_LENGTH);
            try {
              await updateConversation(newConversationId, conversationTitle);
            } catch (error) {
              console.error('更新对话标题失败:', error);
            }
          }
        },
        // userId - 传递用户ID
        user?.id
      );
      
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      setMessages(prev => 
        prev.map(msg => 
          msg.id === tempBotMessage.id 
            ? { 
                ...msg, 
                content: `抱歉，我遇到了一个错误：${errorMessage}。请稍后重试。`, 
                isTyping: false,
                intent: savedMetadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
                sources: savedMetadata.sources,
                searchResults: savedMetadata.searchResults
              }
            : msg
        )
      );
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

  const handleShowSearchResults = (sources: string[], searchResults?: any[]) => {
    setCurrentSearchSources(sources);
    setCurrentSearchResults(searchResults || []);
    setSearchResultsOpen(true);
  };

  const handleCloseSearchResults = () => {
    setSearchResultsOpen(false);
  };

  // 使用点击外部hook
  useClickOutside(userDropdownRef, () => setUserDropdownOpen(false));

  // 监听消息和对话变化，统一管理新对话状态
  useEffect(() => {
    // 使用 setTimeout 来避免快速状态切换导致的闪现
    const timeoutId = setTimeout(() => {
      // 如果有消息，则不是新对话
      if (messages.length > 0) {
        setIsNewConversation(false);
      }
      // 如果没有对话，显示新对话界面
      else if (conversations.length === 0) {
        setIsNewConversation(true);
      }
      // 如果有对话但没有当前对话ID，且没有消息，显示新对话界面
      else if (!currentConversationId && messages.length === 0) {
        setIsNewConversation(true);
      }
    }, UI_CONSTANTS.DEBOUNCE_DELAY);

    return () => clearTimeout(timeoutId);
  }, [conversations, currentConversationId, messages, isNewConversation]);

  // 如果正在加载认证状态，显示加载界面
  if (authLoading) {
    return <LoadingScreen />;
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
        <Header
          sidebarCollapsed={sidebarCollapsed}
          user={user}
          userDropdownOpen={userDropdownOpen}
          onToggleSidebar={() => setSidebarCollapsed(false)}
          onNewConversation={handleNewConversation}
          onToggleUserDropdown={() => setUserDropdownOpen(!userDropdownOpen)}
          onLogout={handleLogout}
          userDropdownRef={userDropdownRef}
        />

        {/* 聊天内容区域 */}
        <main className="flex-1 flex flex-col min-h-0">
          {isNewConversation ? (
            <NewConversationView
              user={user}
              attachments={currentAttachments}
              onSendMessage={handleSendMessage}
              onAttachmentsChange={handleAttachmentsChange}
            />
          ) : (
            // 已有对话：正常布局
            <>
              <ChatArea 
                messages={messages} 
                isLoading={isLoading} 
                onShowSearchResults={handleShowSearchResults}
              />
              <InputArea 
                onSendMessage={handleSendMessage} 
                attachments={currentAttachments}
                onAttachmentsChange={handleAttachmentsChange}
              />
            </>
          )}
        </main>
      </div>

      {/* 搜索结果侧边栏 */}
      <SearchResultsSidebar
        isOpen={searchResultsOpen}
        sources={currentSearchSources}
        searchResults={currentSearchResults}
        onClose={handleCloseSearchResults}
      />
    </div>
  );
};

export default App;

