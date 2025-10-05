import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputArea from './components/InputArea';
import LoginForm from './components/LoginForm';
import LoadingScreen from './components/LoadingScreen';
import Header from './components/Header';
import NewConversationView from './components/NewConversationView';
import SearchResultsSidebar from './components/SearchResultsSidebar';
import { ChatMessage, Conversation, Attachment, User } from './types';
import { sendMessageStream } from './services/api';
import { useConversation } from './hooks/useConversation';
import { useAuth } from './hooks/useAuth';
import { useClickOutside } from './hooks/useClickOutside';
import { UI_CONSTANTS } from './constants';
import { truncateText } from './utils/helpers';

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

    // 用于累积流式内容和保存metadata
    let accumulatedContent = '';
    let savedMetadata: { intent?: string; sources?: string[]; searchResults?: any[] } = {};
    
    try {
      await sendMessageStream(
        {
          message: content,
          conversationId: userMessage.conversationId || currentConversationId || '1',
          attachments: messageAttachments
        },
        // onChunk - 处理内容块
        (chunk: string) => {
          if (botMessage) {
            accumulatedContent += chunk;
            updateMessage(botMessage.id, { 
              content: accumulatedContent,
              isTyping: true, // 保持loading状态，直到流式输出结束
              // 保留已保存的metadata
              intent: savedMetadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
              sources: savedMetadata.sources,
              searchResults: savedMetadata.searchResults
            }, false); // 不保存到数据库，只更新本地状态
          }
        },
        // onMetadata - 处理元数据
        (metadata) => {
          if (botMessage) {
            // 保存metadata到本地变量
            savedMetadata = {
              intent: metadata.intent,
              sources: metadata.sources,
              searchResults: metadata.search_results
            };
            updateMessage(botMessage.id, {
              intent: metadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
              sources: metadata.sources,
              searchResults: metadata.search_results,
              isTyping: true // 保持loading状态，直到流式输出结束
            }, false); // 不保存到数据库，只更新本地状态
          }
        },
        // onError - 处理错误
        (error: string) => {
          if (botMessage) {
            updateMessage(botMessage.id, { 
              content: `错误: ${error}`, 
              isTyping: false,
              // 使用保存的metadata
              intent: savedMetadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
              sources: savedMetadata.sources,
              searchResults: savedMetadata.searchResults
            }, true); // 错误时保存到数据库
          }
        },
        // onEnd - 流结束
        () => {
          if (botMessage) {
            updateMessage(botMessage.id, { 
              content: accumulatedContent,
              isTyping: false,
              // 使用保存的metadata
              intent: savedMetadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
              sources: savedMetadata.sources,
              searchResults: savedMetadata.searchResults
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
        const conversationTitle = truncateText(content, UI_CONSTANTS.MAX_TITLE_LENGTH);
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
          isTyping: false,
          // 使用保存的metadata
          intent: savedMetadata.intent as 'normal' | 'web' | 'file' | 'search' | 'code' | undefined,
          sources: savedMetadata.sources,
          searchResults: savedMetadata.searchResults
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
    }, UI_CONSTANTS.DEBOUNCE_DELAY);

    return () => clearTimeout(timeoutId);
  }, [conversations, currentConversationId, messages]);

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

