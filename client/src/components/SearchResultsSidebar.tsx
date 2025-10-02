import React from 'react';
import { X, ExternalLink, Globe } from 'lucide-react';
import { SearchResult } from '../types';

interface SearchResultsSidebarProps {
  isOpen: boolean;
  sources: string[];
  searchResults?: SearchResult[];
  onClose: () => void;
}

const SearchResultsSidebar: React.FC<SearchResultsSidebarProps> = ({ 
  isOpen, 
  sources, 
  searchResults = [],
  onClose 
}) => {
  if (!isOpen) return null;

  const extractDomain = (url: string) => {
    try {
      const domain = new URL(url).hostname;
      return domain.replace('www.', '');
    } catch {
      return url;
    }
  };

  const extractTitle = (url: string) => {
    try {
      const urlObj = new URL(url);
      const path = urlObj.pathname;
      if (path === '/' || path === '') {
        return urlObj.hostname.replace('www.', '');
      }
      // 简单的标题提取逻辑
      const segments = path.split('/').filter(Boolean);
      const lastSegment = segments[segments.length - 1];
      return lastSegment.replace(/[-_]/g, ' ').replace(/\.(html|htm|php|asp|aspx)$/i, '');
    } catch {
      return url;
    }
  };

  return (
    <>
      {/* 背景遮罩 */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />
      
      {/* 侧边栏 */}
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">Search results</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* 搜索结果列表 */}
        <div 
          className="flex-1 overflow-y-auto p-4" 
          style={{ 
            maxHeight: 'calc(100vh - 80px)',
            scrollbarWidth: 'thin',
            scrollbarColor: '#d1d5db #f3f4f6'
          }}
        >
          <div className="space-y-3">
            {searchResults.length > 0 ? (
              searchResults.map((result, index) => (
                <div
                  key={index}
                  className="group border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all duration-200"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-1">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                        <ExternalLink className="w-4 h-4 text-blue-600" />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-gray-900 mb-2 line-clamp-2">
                        {result.title || extractTitle(result.url)}
                      </h3>
                      <p className="text-xs text-gray-600 mb-2 line-clamp-3 leading-relaxed">
                        {result.content}
                      </p>
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-gray-500">
                          {extractDomain(result.url)}
                        </p>
                        {result.published_date && (
                          <p className="text-xs text-gray-400">
                            {result.published_date}
                          </p>
                        )}
                      </div>
                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:text-blue-800 hover:underline break-all mt-2 block"
                      >
                        {result.url}
                      </a>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              // 降级显示：如果没有完整搜索结果，显示URL列表
              sources.map((source, index) => (
                <div
                  key={index}
                  className="group border border-gray-200 rounded-lg p-3 hover:border-blue-300 hover:shadow-sm transition-all duration-200"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-1">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                        <ExternalLink className="w-4 h-4 text-blue-600" />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-gray-900 mb-1 line-clamp-2 capitalize">
                        {extractTitle(source)}
                      </h3>
                      <p className="text-xs text-gray-500 mb-2">
                        {extractDomain(source)}
                      </p>
                      <a
                        href={source}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:text-blue-800 hover:underline break-all"
                      >
                        {source}
                      </a>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          
          {sources.length === 0 && searchResults.length === 0 && (
            <div className="text-center py-8">
              <Globe className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No search results available</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default SearchResultsSidebar;
