/**
 * 顶部导航栏组件
 */
import React from 'react';
import { PanelLeftOpen, Bot } from 'lucide-react';
import { User } from '../types';

interface HeaderProps {
  sidebarCollapsed: boolean;
  user: User | null;
  userDropdownOpen: boolean;
  onToggleSidebar: () => void;
  onNewConversation: () => void;
  onToggleUserDropdown: () => void;
  onLogout: () => void;
  userDropdownRef: React.RefObject<HTMLDivElement>;
}

const Header: React.FC<HeaderProps> = ({
  sidebarCollapsed,
  user,
  userDropdownOpen,
  onToggleSidebar,
  onNewConversation,
  onToggleUserDropdown,
  onLogout,
  userDropdownRef
}) => {
  return (
    <header className="bg-white/80 backdrop-blur-sm px-4 py-2 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        {/* 当侧栏收起时显示展开按钮和新对话按钮 */}
        {sidebarCollapsed && (
          <>
            <button
              onClick={onToggleSidebar}
              className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105 group shadow-sm"
              title="展开侧栏"
            >
              <PanelLeftOpen className="w-4 h-4 text-gray-600 group-hover:text-gray-800 transition-colors" />
            </button>
            
            <button
              onClick={onNewConversation}
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
        <div ref={userDropdownRef} className="relative user-dropdown">
          <button
            onClick={onToggleUserDropdown}
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
                  onClick={onLogout}
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
  );
};

export default Header;
