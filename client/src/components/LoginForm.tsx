import React, { useState } from 'react';
import { User } from '../types';
import { LogIn, User as UserIcon } from 'lucide-react';
import { UI_CONSTANTS } from '../constants';

interface LoginFormProps {
  onLogin: (user: User) => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!username.trim()) {
      setError('请输入用户名');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // 创建用户对象 - 使用基于用户名的固定ID，确保同一用户总是有相同的ID
      const userId = `user_${username.trim().toLowerCase().replace(/[^a-z0-9]/g, '_')}`;
      const user: User = {
        id: userId,
        username: username.trim(),
        loginTime: new Date()
      };

      // 保存到本地存储
      localStorage.setItem('currentUser', JSON.stringify(user));
      
      // 调用登录回调
      onLogin(user);
    } catch (err) {
      setError('登录失败，请重试');
      console.error('登录错误:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
            <LogIn className="w-8 h-8 text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">欢迎使用智能聊天助手</h1>
          <p className="text-gray-600">请输入您的用户名开始使用</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
              用户名
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <UserIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="请输入用户名"
                disabled={isLoading}
                maxLength={UI_CONSTANTS.MAX_USERNAME_LENGTH}
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !username.trim()}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? '登录中...' : '开始使用'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            登录即表示您同意使用我们的服务
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;
