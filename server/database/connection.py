"""
数据库连接管理
"""
import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "chatbot.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建用户表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建对话表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        user_id TEXT DEFAULT 'default_user',
                        title TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # 创建消息表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                        content TEXT NOT NULL,
                        intent TEXT,
                        sources TEXT,  -- JSON字符串
                        attachments TEXT,  -- JSON字符串
                        is_typing BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                """)
                
                # 创建附件表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attachments (
                        id TEXT PRIMARY KEY,
                        message_id TEXT NOT NULL,
                        type TEXT NOT NULL CHECK (type IN ('file', 'url')),
                        data TEXT NOT NULL,  -- JSON字符串
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (message_id) REFERENCES messages (id)
                    )
                """)
                
                # 创建记忆索引表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memory_index (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        memory_type TEXT NOT NULL CHECK (memory_type IN ('short', 'semantic', 'profile', 'knowledge')),
                        importance_score REAL DEFAULT 0.0,
                        content_preview TEXT,
                        vector_id TEXT,  -- Qdrant中的向量ID
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 0,
                        metadata TEXT,  -- JSON字符串
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # 创建记忆摘要表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memory_summaries (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        summary_text TEXT NOT NULL,
                        original_message_count INTEGER,
                        compressed_ratio REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # 创建用户行为表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_behavior (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        action_data TEXT,  -- JSON字符串
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id)")
                
                # 记忆相关索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_index_user_id ON memory_index (user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_index_type ON memory_index (memory_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_index_importance ON memory_index (importance_score)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_index_accessed ON memory_index (last_accessed)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_summaries_user_id ON memory_summaries (user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_behavior_user_id ON user_behavior (user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_behavior_type ON user_behavior (action_type)")
                
                conn.commit()
                logger.info("数据库初始化完成（包含记忆系统表）")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
        return conn
    
    def execute_query(self, query: str, params: tuple = ()):
        """执行查询并返回结果"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise
    
    def execute_update(self, query: str, params: tuple = ()):
        """执行更新操作并返回影响行数"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"更新执行失败: {e}")
            raise
    
    def execute_insert(self, query: str, params: tuple = ()):
        """执行插入操作并返回插入的ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return str(cursor.lastrowid)
        except Exception as e:
            logger.error(f"插入执行失败: {e}")
            raise
