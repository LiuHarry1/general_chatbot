/**
 * 应用常量定义
 */

// UI 常量
export const UI_CONSTANTS = {
  // 延迟时间
  DEBOUNCE_DELAY: 50,
  URL_DETECTION_DELAY: 1000,
  
  // 尺寸
  MAX_TEXTAREA_HEIGHT: 120,
  MIN_TEXTAREA_HEIGHT: 28,
  SIDEBAR_WIDTH: 256, // 16 * 16 = 256px (w-64)
  SIDEBAR_COLLAPSED_WIDTH: 64, // 16 * 4 = 64px (w-16)
  
  // 内容长度限制
  MAX_TITLE_LENGTH: 30,
  MAX_USERNAME_LENGTH: 50,
  
  // 重试次数
  MAX_RETRY_ATTEMPTS: 3,
} as const;

// API 常量
export const API_CONSTANTS = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:3001/api',
  TIMEOUT: 15000,
} as const;

// 本地存储键名
export const STORAGE_KEYS = {
  CURRENT_USER: 'currentUser',
} as const;

// 文件类型
export const FILE_TYPES = {
  ACCEPTED: '.pdf,.txt,.doc,.docx,.md',
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
} as const;

// 问候语配置
export const GREETINGS = {
  NIGHT: '夜深了',
  MORNING: '早上好',
  NOON: '中午好',
  AFTERNOON: '下午好',
  EVENING: '晚上好',
} as const;

// 建议操作
export const SUGGESTED_ACTIONS = {
  MIXED: [
    "综合分析所有内容",
    "对比这些文档和网页的异同",
    "总结所有材料的主要观点",
    "生成综合报告"
  ],
  MULTIPLE_FILES: [
    "对比分析这些文档",
    "总结所有文档的共同点",
    "生成综合分析报告",
    "找出文档间的关联性"
  ],
  SINGLE_FILE: [
    "详细总结这篇文档内容",
    "用通俗易懂的话，说说文档讲了什么",
    "生成脑图",
    "生成播客"
  ],
  URLS: [
    "详细总结这个网页内容",
    "用通俗易懂的话，说说网页讲了什么",
    "参考网页写一篇原创内容",
    "生成播客"
  ]
} as const;

// 反爬虫检测关键词
export const ANTI_CRAWLER_INDICATORS = [
  "安全验证", "验证", "人机验证", "captcha", "robot", "bot",
  "请稍后再试", "访问过于频繁", "系统繁忙", "服务暂时不可用"
] as const;
