import React, { useState, useRef, useCallback } from 'react';
import { Attachment, FileAttachment, UrlAttachment } from '../types';
import { Paperclip, Link, X, Send, FileText, Globe } from 'lucide-react';
import { uploadFile, analyzeUrl } from '../services/api';

interface InputAreaProps {
  onSendMessage: (content: string, attachments?: Attachment[]) => void;
  attachments?: Attachment[];
  onAttachmentsChange?: (attachments: Attachment[]) => void;
}

const InputArea: React.FC<InputAreaProps> = ({ onSendMessage, attachments = [], onAttachmentsChange }) => {
  const [input, setInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() && attachments.length === 0) return;

    onSendMessage(input, attachments.length > 0 ? attachments : undefined);
    setInput('');
    // 不再自动清空附件，保持持久化
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      const fileArray = Array.from(files);
      const newAttachments: Attachment[] = [];
      
      for (const file of fileArray) {
        const response = await uploadFile(file);
        const newAttachment: Attachment = {
          type: 'file',
          id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
          data: {
            name: file.name,
            size: file.size,
            type: file.type,
            content: response.content
          }
        };
        newAttachments.push(newAttachment);
      }
      
      // 一次性更新所有新附件
      const updatedAttachments = [...attachments, ...newAttachments];
      onAttachmentsChange?.(updatedAttachments);
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('文件上传失败，请重试。');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUrlAnalysis = async (url?: string) => {
    const targetUrl = url || prompt('请输入要分析的网页链接：');
    if (!targetUrl) return;

    setIsUploading(true);
    try {
      const response = await analyzeUrl(targetUrl);
      const newAttachment: Attachment = {
        type: 'url',
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        data: {
          url: targetUrl,
          title: response.title,
          content: response.content
        }
      };
      const updatedAttachments = [...attachments, newAttachment];
      onAttachmentsChange?.(updatedAttachments);
    } catch (error) {
      console.error('Error analyzing URL:', error);
      alert('网页分析失败，请重试。');
    } finally {
      setIsUploading(false);
    }
  };

  const removeAttachment = (index: number) => {
    const updatedAttachments = attachments.filter((_, i) => i !== index);
    onAttachmentsChange?.(updatedAttachments);
  };

  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, []);

  React.useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  const getSuggestedActions = (attachments: Attachment[]) => {
    const hasFiles = attachments.some(att => att.type === 'file');
    const hasUrls = attachments.some(att => att.type === 'url');
    const fileCount = attachments.filter(att => att.type === 'file').length;
    
    if (hasFiles && hasUrls) {
      // 混合类型：文件和网页
      return [
        "综合分析所有内容",
        "对比这些文档和网页的异同",
        "总结所有材料的主要观点",
        "生成综合报告"
      ];
    } else if (hasFiles) {
      // 只有文件
      if (fileCount > 1) {
        return [
          "对比分析这些文档",
          "总结所有文档的共同点",
          "生成综合分析报告",
          "找出文档间的关联性"
        ];
      } else {
        return [
          "详细总结这篇文档内容",
          "用通俗易懂的话，说说文档讲了什么",
          "生成脑图",
          "生成播客"
        ];
      }
    } else if (hasUrls) {
      // 只有网页
      return [
        "详细总结这个网页内容",
        "用通俗易懂的话，说说网页讲了什么",
        "参考网页写一篇原创内容",
        "生成播客"
      ];
    }
    
    return [];
  };

  const handleSuggestedAction = (action: string) => {
    setInput(action);
  };

  // 检测输入中的链接
  const detectAndProcessLinks = (text: string) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const urls = text.match(urlRegex);
    
    if (urls && urls.length > 0) {
      // 自动处理第一个链接
      const url = urls[0];
      if (!attachments.some(att => att.type === 'url' && (att.data as UrlAttachment).url === url)) {
        handleUrlAnalysis(url);
      }
    }
  };

  // 监听输入变化，检测链接
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);
    
    // 检测链接（延迟检测，避免频繁处理）
    if (value.includes('http')) {
      setTimeout(() => {
        detectAndProcessLinks(value);
      }, 1000);
    }
  };

  return (
    <div className="input-area bg-white px-4 pt-0 pb-2">
      {/* 上部分：附件显示区域 */}
      {attachments.length > 0 && (
        <div className="mb-2 space-y-2">
          {/* 附件列表 */}
          <div className="space-y-2">
            {attachments.map((attachment, index) => (
              <div key={index} className="bg-gray-50 rounded-xl border border-gray-200 p-4 shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    {attachment.type === 'file' ? (
                      <div className="w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center">
                        <FileText className="w-5 h-5 text-red-500" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center">
                        <Globe className="w-5 h-5 text-green-500" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {attachment.type === 'file' 
                          ? (attachment.data as FileAttachment).name 
                          : (attachment.data as UrlAttachment).url
                        }
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {attachment.type === 'file' 
                          ? `PDF · ${Math.round(((attachment.data as FileAttachment)?.size || 0) / 1024 / 1024 * 10) / 10}MB · 约${Math.round(((attachment.data as FileAttachment)?.content?.length || 0) / 1000)}千字`
                          : '链接'
                        }
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => removeAttachment(index)}
                    className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <X className="w-4 h-4 text-gray-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* 建议操作按钮 - 只在有附件时显示一次 */}
          <div className="grid grid-cols-2 gap-2">
            {getSuggestedActions(attachments).map((action, actionIndex) => (
              <button
                key={actionIndex}
                onClick={() => handleSuggestedAction(action)}
                className="bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 flex items-center justify-between group transition-colors"
              >
                <span className="truncate">{action}</span>
                <svg className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors flex-shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 中间部分：输入区域 */}
      <div className="input-container -mt-3">
               <form onSubmit={handleSubmit} className="flex items-end bg-white rounded-2xl border border-gray-200/60 p-3 space-x-4 shadow-lg hover:shadow-xl transition-all duration-300">
          {/* 左侧功能按钮组 */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="p-3 hover:bg-blue-50 rounded-xl transition-all duration-200 hover:scale-105 group"
              title="上传文件（支持多选）"
            >
              <Paperclip className="w-5 h-5 text-gray-600 group-hover:text-blue-600 transition-colors" />
            </button>
            
            <button
              type="button"
              onClick={() => handleUrlAnalysis()}
              disabled={isUploading}
              className="p-3 hover:bg-green-50 rounded-xl transition-all duration-200 hover:scale-105 group"
              title="分析网页"
            >
              <Link className="w-5 h-5 text-gray-600 group-hover:text-green-600 transition-colors" />
            </button>

            <button
              type="button"
              className="p-3 hover:bg-purple-50 rounded-xl transition-all duration-200 hover:scale-105 group"
              title="深度思考"
            >
              <svg className="w-5 h-5 text-gray-600 group-hover:text-purple-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </button>
          </div>

          {/* 输入框 */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder={attachments.length > 0 ? "总结一下这个文件" : "输入消息，或使用 / 选择功能..."}
                     className="w-full px-3 py-3 bg-transparent border-none outline-none resize-none text-gray-900 placeholder-gray-500 text-base leading-relaxed"
              rows={1}
              style={{ minHeight: '28px', maxHeight: '120px' }}
            />
          </div>

          {/* 右侧功能按钮组 */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              className="p-3 hover:bg-orange-50 rounded-xl transition-all duration-200 hover:scale-105 group"
              title="剪切"
            >
              <svg className="w-5 h-5 text-gray-600 group-hover:text-orange-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>

            <button
              type="button"
              className="p-3 hover:bg-pink-50 rounded-xl transition-all duration-200 hover:scale-105 group"
              title="语音输入"
            >
              <svg className="w-5 h-5 text-gray-600 group-hover:text-pink-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </button>

            <button
              type="submit"
              disabled={(!input.trim() && attachments.length === 0) || isUploading}
              className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:from-gray-300 disabled:to-gray-400 rounded-2xl flex items-center justify-center transition-all duration-300 hover:scale-105 shadow-lg hover:shadow-xl group"
            >
              {isUploading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-5 h-5 text-white group-hover:translate-x-0.5 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
        </form>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.txt,.doc,.docx,.md"
        onChange={handleFileUpload}
        className="hidden"
      />
    </div>
  );
};

export default InputArea;
