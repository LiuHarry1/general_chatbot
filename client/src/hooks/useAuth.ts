import { useState, useEffect } from 'react';
import { User } from '../types';
import { safeLocalStorage, safeJsonParse } from '../utils/helpers';
import { STORAGE_KEYS } from '../constants';

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 检查本地存储中是否有用户信息
    const checkAuth = () => {
      const storedUser = safeLocalStorage.getItem(STORAGE_KEYS.CURRENT_USER);
      if (storedUser) {
        const userData = safeJsonParse(storedUser, null) as User | null;
        if (userData) {
          // 将字符串日期转换为Date对象
          userData.loginTime = new Date(userData.loginTime);
          setUser(userData);
        } else {
          // 数据损坏，清除
          safeLocalStorage.removeItem(STORAGE_KEYS.CURRENT_USER);
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = (userData: User) => {
    setUser(userData);
    safeLocalStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify(userData));
  };

  const logout = () => {
    setUser(null);
    safeLocalStorage.removeItem(STORAGE_KEYS.CURRENT_USER);
    // 只清除用户信息，对话数据由后端管理
  };

  const isAuthenticated = !!user;

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout
  };
};
