const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const cheerio = require('cheerio');
const mammoth = require('mammoth');
const pdfParse = require('pdf-parse');
const winston = require('winston');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Configure logging
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});

// Create logs directory if it doesn't exist
if (!fs.existsSync('logs')) {
  fs.mkdirSync('logs');
}

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = 'uploads';
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir);
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + '-' + file.originalname);
  }
});

const upload = multer({ 
  storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['.pdf', '.txt', '.doc', '.docx', '.md'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowedTypes.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only PDF, TXT, DOC, DOCX, and MD files are allowed.'));
    }
  }
});

// Utility functions
const extractTextFromFile = async (filePath, fileType) => {
  try {
    const buffer = fs.readFileSync(filePath);
    
    switch (fileType) {
      case '.pdf':
        const pdfData = await pdfParse(buffer);
        return pdfData.text;
      
      case '.docx':
        const docxResult = await mammoth.extractRawText({ buffer });
        return docxResult.value;
      
      case '.txt':
      case '.md':
        return buffer.toString('utf-8');
      
      default:
        throw new Error('Unsupported file type');
    }
  } catch (error) {
    logger.error('Error extracting text from file:', error);
    throw error;
  }
};

const analyzeWebPage = async (url) => {
  try {
    logger.info(`Analyzing web page: ${url}`);
    const response = await axios.get(url, {
      timeout: 10000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    
    const $ = cheerio.load(response.data);
    
    // Remove script and style elements
    $('script, style').remove();
    
    // Extract title
    const title = $('title').text().trim() || 'Untitled';
    
    // Extract main content
    const content = $('body').text()
      .replace(/\s+/g, ' ')
      .trim()
      .substring(0, 4000); // Limit content length
    
    return { title, content };
  } catch (error) {
    logger.error('Error analyzing web page:', error);
    throw new Error('Failed to analyze web page');
  }
};

const searchWithTavily = async (query) => {
  try {
    logger.info(`Searching with Tavily: ${query}`);
    const response = await axios.post('https://api.tavily.com/search', {
      api_key: process.env.TAVILY_API_KEY,
      query,
      search_depth: 'basic',
      include_answer: true,
      include_raw_content: false,
      max_results: 5
    });
    
    return response.data;
  } catch (error) {
    logger.error('Error searching with Tavily:', error);
    throw new Error('Search failed');
  }
};

const callTongyiQwen = async (messages, searchResults = null, fileContent = null, webContent = null, intent = 'normal') => {
  try {
    logger.info(`Calling Tongyi Qwen API with intent: ${intent}`);
    
    let systemPrompt = "你是一个专业的AI助手，可以帮助用户进行对话、分析文档、搜索网络信息等任务。请用中文回答用户的问题。";
    
    // 根据不同的意图调整系统提示
    if (intent === 'file') {
      systemPrompt = "你是一个专业的文档分析助手。用户上传了文档，请基于文档内容回答用户的问题。请用中文回答，并确保回答基于文档的实际内容。";
      if (fileContent) {
        systemPrompt += `\n\n当前分析的文档内容：\n${fileContent.substring(0, 8000)}`; // 限制长度避免token超限
      }
    } else if (intent === 'web') {
      systemPrompt = "你是一个专业的网页内容分析助手。用户提供了网页链接，请基于网页内容回答用户的问题。请用中文回答，并确保回答基于网页的实际内容。";
      if (webContent) {
        systemPrompt += `\n\n当前分析的网页内容：\n${webContent.substring(0, 8000)}`; // 限制长度避免token超限
      }
    } else if (searchResults) {
      systemPrompt = "你是一个专业的搜索助手。用户的问题需要搜索最新信息，请基于搜索结果回答用户的问题。请用中文回答，并引用相关的信息来源。";
      systemPrompt += `\n\n搜索结果：\n${JSON.stringify(searchResults, null, 2)}`;
    }
    
    const response = await axios.post('https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation', {
      model: 'qwen-turbo',
      input: {
        messages: [
          { role: 'system', content: systemPrompt },
          ...messages
        ]
      },
      parameters: {
        temperature: 0.7,
        max_tokens: 3000,
        top_p: 0.8,
        repetition_penalty: 1.1
      }
    }, {
      headers: {
        'Authorization': `Bearer ${process.env.DASHSCOPE_API_KEY}`,
        'Content-Type': 'application/json'
      }
    });
    
    return response.data.output.text;
  } catch (error) {
    logger.error('Error calling Tongyi Qwen:', error);
    if (error.response) {
      logger.error('API Error Response:', error.response.data);
    }
    throw new Error('AI服务暂时不可用，请稍后重试');
  }
};

// Routes
app.post('/api/chat', async (req, res) => {
  try {
    const { message, conversationId, attachments } = req.body;
    logger.info(`Chat request - Conversation: ${conversationId}, Message: ${message.substring(0, 100)}...`);
    
    let intent = 'normal';
    let searchResults = null;
    let fileContent = null;
    let webContent = null;
    
    // Check if there are attachments
    if (attachments && attachments.length > 0) {
      const fileAttachment = attachments.find(att => att.type === 'file');
      const urlAttachment = attachments.find(att => att.type === 'url');
      
      if (fileAttachment) {
        intent = 'file';
        fileContent = fileAttachment.data.content;
        logger.info(`Processing file attachment: ${fileAttachment.data.name}`);
      }
      
      if (urlAttachment) {
        intent = 'web';
        webContent = urlAttachment.data.content;
        logger.info(`Processing URL attachment: ${urlAttachment.data.url}`);
      }
    }
    
    // 检查是否需要搜索 - 支持中英文关键词
    const searchKeywords = [
      'search', 'find', 'look up', 'what is', 'how to', 'where is',
      '搜索', '查找', '寻找', '什么是', '如何', '哪里', '最新', '新闻', '资讯'
    ];
    const needsSearch = searchKeywords.some(keyword => 
      message.toLowerCase().includes(keyword.toLowerCase())
    ) && intent === 'normal';
    
    if (needsSearch) {
      logger.info('Performing web search for query:', message);
      try {
        searchResults = await searchWithTavily(message);
        logger.info(`Search completed, found ${searchResults.results?.length || 0} results`);
      } catch (searchError) {
        logger.warn('Search failed, continuing with normal chat:', searchError.message);
        // 搜索失败时继续正常对话
      }
    }
    
    // Prepare messages for AI
    const messages = [
      { role: 'user', content: message }
    ];
    
    // Call Tongyi Qwen
    const aiResponse = await callTongyiQwen(messages, searchResults, fileContent, webContent, intent);
    
    // 记录响应信息
    logger.info(`AI response generated for intent: ${intent}, response length: ${aiResponse.length}`);
    
    res.json({
      content: aiResponse,
      intent: intent,
      sources: searchResults ? searchResults.results?.map(r => r.url) : [],
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    logger.error('Chat API error:', error);
    res.status(500).json({ 
      error: '处理请求时发生错误',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

app.post('/api/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: '没有上传文件' });
    }
    
    logger.info(`File upload: ${req.file.originalname}, size: ${req.file.size} bytes`);
    
    const filePath = req.file.path;
    const fileType = path.extname(req.file.originalname).toLowerCase();
    
    const content = await extractTextFromFile(filePath, fileType);
    
    // Clean up uploaded file
    fs.unlinkSync(filePath);
    
    logger.info(`File processed successfully, extracted ${content.length} characters`);
    
    res.json({ 
      content,
      filename: req.file.originalname,
      size: req.file.size,
      type: fileType,
      extractedLength: content.length
    });
    
  } catch (error) {
    logger.error('Upload API error:', error);
    res.status(500).json({ 
      error: '文件处理失败',
      message: error.message 
    });
  }
});

app.post('/api/analyze-url', async (req, res) => {
  try {
    const { url } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'URL是必需的' });
    }
    
    // 验证URL格式
    try {
      new URL(url);
    } catch (urlError) {
      return res.status(400).json({ error: '无效的URL格式' });
    }
    
    logger.info(`Analyzing URL: ${url}`);
    const result = await analyzeWebPage(url);
    
    logger.info(`URL analysis completed, extracted ${result.content.length} characters`);
    
    res.json({
      ...result,
      url: url,
      analyzedAt: new Date().toISOString(),
      contentLength: result.content.length
    });
    
  } catch (error) {
    logger.error('URL analysis error:', error);
    res.status(500).json({ 
      error: '网页分析失败',
      message: error.message 
    });
  }
});

// 获取支持的文件类型
app.get('/api/supported-formats', (req, res) => {
  res.json({
    supportedFormats: ['.pdf', '.txt', '.doc', '.docx', '.md'],
    maxFileSize: '10MB',
    description: '支持的文件格式和大小限制'
  });
});

// 获取API状态
app.get('/api/status', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    services: {
      tongyi: 'Available',
      tavily: 'Available',
      fileProcessing: 'Available',
      webAnalysis: 'Available'
    },
    version: '1.0.0'
  });
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Error handling middleware
app.use((error, req, res, next) => {
  logger.error('Unhandled error:', error);
  res.status(500).json({ 
    error: '服务器内部错误',
    message: process.env.NODE_ENV === 'development' ? error.message : '请稍后重试',
    timestamp: new Date().toISOString()
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: '接口不存在',
    message: `无法找到 ${req.method} ${req.originalUrl}`,
    timestamp: new Date().toISOString()
  });
});

app.listen(PORT, () => {
  logger.info(`Server running on port ${PORT}`);
  console.log(`🚀 Server running on http://localhost:${PORT}`);
});
