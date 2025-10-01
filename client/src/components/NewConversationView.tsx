/**
 * 新对话视图组件
 */
import React from 'react';
import { Bot } from 'lucide-react';
import { Attachment, User } from '../types';
import InputArea from './InputArea';
import { getGreeting } from '../utils/helpers';

interface NewConversationViewProps {
  user: User | null;
  attachments: Attachment[];
  onSendMessage: (content: string, attachments?: Attachment[]) => void;
  onAttachmentsChange: (attachments: Attachment[]) => void;
}

const NewConversationView: React.FC<NewConversationViewProps> = ({
  user,
  attachments,
  onSendMessage,
  onAttachmentsChange
}) => {
  return (
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
          onSendMessage={onSendMessage} 
          attachments={attachments}
          onAttachmentsChange={onAttachmentsChange}
        />
      </div>
    </div>
  );
};

export default NewConversationView;
