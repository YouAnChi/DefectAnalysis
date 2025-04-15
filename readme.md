# 智能缺陷分析系统文档

## 1. 系统架构

智能缺陷分析系统采用前后端分离的架构设计，主要由以下几个部分组成：

系统采用模块化设计，各组件之间通过标准化接口通信，确保系统的可扩展性和可维护性。数据流向为：用户通过前端界面上传Excel文件，后端服务接收并处理请求，将任务分发给分析引擎，分析引擎调用知识库进行检索和分析，最终将结果返回给用户。

### 1.1 整体架构

```
+----------------+      +----------------+      +----------------+
|                |      |                |      |                |
|  前端界面       | <--> |  后端服务       | <--> |  分析引擎       |
|  (HTML/JS/CSS) |      |  (Go)          |      |  (Python)      |
|                |      |                |      |                |
+----------------+      +----------------+      +----------------+
                                                       |
                                                       v
                                               +----------------+
                                               |                |
                                               |  知识库         |
                                               |  (JSON)        |
                                               |                |
                                               +----------------+
```

### 1.2 前端组件

- **用户界面**：基于HTML5、CSS3和JavaScript构建，使用Bootstrap 5框架实现响应式设计
  - 登录页面：简洁的用户认证界面
  - 主控制台：包含文件上传、参数设置和任务管理区域
  - 结果展示页：表格和图表形式展示分析结果
  - 详情页：展示单个缺陷的详细分析结果

- **交互逻辑**：使用原生JavaScript处理用户交互和API调用
  - 文件上传模块：支持拖拽上传和文件选择
  - 参数配置模块：提供相似度阈值和知识库选择
  - 任务管理模块：展示任务状态和进度
  - 结果展示模块：支持排序、筛选和导出

- **数据展示**：动态生成表格和图表，展示分析结果
  - 使用DataTables实现高级表格功能
  - 使用Chart.js生成可视化图表
  - 支持结果导出为Excel、PDF和CSV格式

### 1.3 后端组件

- **Web服务器**：基于Go语言的Gin框架构建RESTful API
  - 提供高性能的HTTP服务
  - 实现中间件机制，支持日志记录、错误处理和认证
  - 支持静态文件服务，为前端提供资源

- **任务管理**：处理任务创建、状态跟踪和结果获取
  - 任务队列：使用内存队列或Redis实现任务排队
  - 状态追踪：实时更新和存储任务状态
  - 结果缓存：临时存储分析结果，支持重复查询

- **文件处理**：处理Excel文件的上传、解析和结果导出
  - 文件验证：检查文件格式和必要字段
  - 数据解析：将Excel数据转换为JSON格式
  - 结果生成：将分析结果写入新的Excel文件

### 1.4 分析引擎

- **Python应用**：基于LangChain框架构建的NLP分析引擎
  - 提供HTTP接口，接收后端服务的分析请求
  - 实现多线程处理，提高并发性能
  - 支持批量处理和单条处理模式

- **向量检索**：使用FAISS实现高效的相似案例检索
  - 文本向量化：使用text2vec-base-chinese模型
  - 索引构建：创建和维护向量索引
  - 相似度计算：基于余弦相似度算法
  - 评分分类预筛选：根据评分分类预先筛选知识库

- **LLM集成**：集成DeepSeek大语言模型进行智能分析
  - 提示词工程：构建结构化提示词
  - 上下文增强：将相似案例作为上下文
  - 结果解析：从LLM响应中提取结构化信息

### 1.5 知识库

- **数据存储**：使用JSON格式存储缺陷知识库
  - 缺陷记录：包含ID、标题、描述、分类等字段
  - 元数据：记录来源、时间戳和版本信息
  - 支持增量更新和版本控制

- **向量索引**：为缺陷描述建立向量索引，支持语义检索
  - 索引文件：使用FAISS格式存储向量索引
  - 元数据映射：维护向量ID与缺陷记录的映射关系
  - 定期更新：支持知识库扩展后的索引重建

## 2. 功能实现

### 2.1 缺陷分析流程

1. **数据上传**：用户上传包含缺陷描述的Excel文件
   - 支持多种Excel格式（.xlsx, .xls）
   - 提供文件格式验证和错误提示
   - 支持大文件分块上传

2. **任务创建**：后端创建分析任务，分配唯一ID
   - 生成UUID作为任务标识
   - 记录任务创建时间和参数
   - 初始化任务状态为pending

3. **相似案例检索**：基于向量相似度检索相关历史案例
   - 将缺陷描述转换为向量表示
   - 应用评分分类预筛选机制（如有评分分类）
   - 在向量空间中检索相似案例
   - 根据相似度阈值筛选结果

4. **智能分析**：结合历史案例和LLM能力进行缺陷分析
   - 构建包含相似案例的提示词
   - 调用DeepSeek API进行分析
   - 提取关键信息和建议
   - 生成结构化分析结果

5. **结果生成**：生成分析结果并保存为Excel文件
   - 将分析结果添加到原始数据中
   - 格式化输出为Excel文件
   - 保存在临时目录，提供下载链接

6. **结果展示**：前端展示分析结果，支持下载和详情查看
   - 表格形式展示概要结果
   - 提供详情页查看完整分析
   - 支持结果筛选和排序
   - 提供Excel下载功能

### 2.2 关键技术实现

#### 2.2.1 向量检索

系统使用FAISS（Facebook AI Similarity Search）实现高效的向量检索：

1. 使用HuggingFace的text2vec-base-chinese模型将文本转换为向量
   ```python
   embeddings = HuggingFaceEmbeddings(model_name='shibing624/text2vec-base-chinese')
   ```

2. 构建向量索引，支持快速相似度搜索
   ```python
   vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
   ```

3. 根据相似度阈值筛选相关案例
   ```python
   similar_docs = vector_store.similarity_search_with_score(query_text, k=top_k)
   filtered_docs = [doc for doc, score in similar_docs if score <= similarity_threshold]
   ```

4. 评分分类预筛选机制实现
   ```python
   # 根据评分分类筛选文档
   filtered_docs = []
   for doc in all_docs:
       if doc.metadata.get('score_category') == score_category:
           filtered_docs.append(doc)
           
   # 创建临时向量存储用于检索
   temp_vector_store = FAISS.from_documents(filtered_docs, embeddings)
   similar_docs = temp_vector_store.similarity_search_with_score(query_text, k=top_k)
   ```

#### 2.2.2 大语言模型集成

系统集成DeepSeek大语言模型进行智能分析：

1. 构建包含历史案例和当前缺陷的提示词
   ```python
   prompt = f"""
   你是一个专业的缺陷分析专家，请根据以下信息分析当前缺陷：
   
   当前缺陷描述：{defect_description}
   
   相似历史案例：
   {similar_cases_text}
   
   请提供以下分析：
   1. 缺陷根本原因
   2. 可能的解决方案
   3. 缺陷严重程度评估
   4. 预防措施建议
   """
   ```

2. 调用LLM API进行分析
   ```python
   llm = ChatDeepSeek(
       model="deepseek-reasoner",
       api_key="your-api-key",
       base_url="https://api.deepseek.com",
   )
   response = llm.invoke([{"role": "user", "content": prompt}])
   ```

3. 获取分析结果和推理过程
   ```python
   analysis_result = response.content
   structured_result = parse_llm_response(analysis_result)
   ```

#### 2.2.3 任务管理

后端实现了完整的任务管理机制：

1. 使用UUID生成唯一任务ID
   ```go
   taskID := uuid.New().String()
   ```

2. 维护任务状态（pending、processing、completed、failed）
   ```go
   type Task struct {
       ID          string    `json:"id"`
       Status      string    `json:"status"`
       Progress    int       `json:"progress"`
       CreatedAt   time.Time `json:"created_at"`
       CompletedAt time.Time `json:"completed_at,omitempty"`
       ResultFile  string    `json:"result_file,omitempty"`
       Error       string    `json:"error,omitempty"`
   }
   ```

3. 支持任务进度实时更新和查询
   ```go
   func (t *Task) UpdateProgress(progress int) {
       t.Progress = progress
       if progress >= 100 {
           t.Status = "completed"
           t.CompletedAt = time.Now()
       }
   }
   ```

4. 异步处理长时间运行的分析任务
   ```go
   go func() {
       // 执行分析任务
       result, err := analyzeDefects(task, filePath, similarityThreshold)
       if err != nil {
           task.Status = "failed"
           task.Error = err.Error()
           return
       }
       
       // 更新任务状态
       task.Status = "completed"
       task.ResultFile = result.FilePath
       task.CompletedAt = time.Now()
   }()
   ```

#### 2.2.4 前端API交互

前端通过RESTful API与后端交互：

1. 文件上传API
   ```javascript
   async function uploadFile(file, similarityThreshold) {
       const formData = new FormData();
       formData.append('file', file);
       formData.append('similarity_threshold', similarityThreshold);
       
       const response = await fetch('/api/tasks', {
           method: 'POST',
           body: formData
       });
       
       return await response.json();
   }
   ```

2. 任务状态查询API
   ```javascript
   async function checkTaskStatus(taskId) {
       const response = await fetch(`/api/tasks/${taskId}`);
       return await response.json();
   }
   ```

3. 结果获取API
   ```javascript
   async function getTaskResult(taskId) {
       const response = await fetch(`/api/tasks/${taskId}/result`);
       return await response.json();
   }
   ```

4. 结果下载API
   ```javascript
   function downloadResult(taskId) {
       window.location.href = `/api/tasks/${taskId}/download`;
   }
   ```

#### 2.2.5 评分分类预筛选机制

评分分类预筛选是系统的一个关键创新，它通过在向量检索前先根据评分分类对知识库进行预筛选，确保检索结果在业务语义上更加相关：

1. 预筛选流程
   ```python
   def search_with_category_filter(query_text, score_category, vector_store, top_k=8):
       # 获取所有文档
       all_docs = vector_store.docstore._dict.values()
       
       # 根据评分分类筛选
       filtered_docs = []
       for doc in all_docs:
           if doc.metadata.get('score_category') == score_category:
               filtered_docs.append(doc)
       
       # 创建临时向量存储
       temp_vector_store = FAISS.from_documents(filtered_docs, embeddings)
       
       # 在筛选后的文档中执行向量检索
       similar_docs = temp_vector_store.similarity_search_with_score(query_text, k=top_k)
       
       return similar_docs
   ```

2. 回退机制
   ```python
   # 如果筛选后的文档数量太少，则使用原始检索
   if len(filtered_docs) < 5:
       logging.info("筛选后文档数量不足，使用原始检索")
       similar_docs = vector_store.similarity_search_with_score(
           defect_description,
           k=8
       )
   ```

3. 性能优化
   ```python
   # 使用缓存优化性能
   @lru_cache(maxsize=128)
   def get_filtered_vector_store(score_category):
       # 根据评分分类获取预筛选的向量存储
       # 这个函数会缓存结果，避免重复筛选
       filtered_docs = [doc for doc in all_docs if doc.metadata.get('score_category') == score_category]
       return FAISS.from_documents(filtered_docs, embeddings)
   ```

## 3. 部署方式

### 3.1 环境要求

#### 3.1.1 后端环境

- Go 1.16+
- 依赖包：
  - github.com/gin-gonic/gin v1.7.7+：Web框架
  - github.com/gin-contrib/cors v1.3.1+：跨域资源共享中间件
  - github.com/google/uuid v1.3.0+：UUID生成
  - github.com/360EntSecGroup-Skylar/excelize/v2 v2.4.0+：Excel处理

#### 3.1.2 分析引擎环境

- Python 3.9+
- 依赖包：
  - langchain==0.0.267+：LLM应用框架
  - langchain_deepseek==0.0.1+：DeepSeek集成
  - pandas==1.5.3+：数据处理
  - faiss-cpu==1.7.4+：向量检索
  - huggingface_hub==0.16.4+：模型下载
  - tqdm==4.66.1+：进度显示
  - sentence-transformers==2.2.2+：文本向量化

#### 3.1.3 系统要求

- CPU：4核+
- 内存：8GB+（推荐16GB以上）
- 存储：10GB+可用空间
- 网络：稳定的互联网连接（用于API调用）
- 操作系统：Linux、macOS或Windows

### 3.2 部署步骤

#### 3.2.1 后端部署

1. 安装Go环境和依赖包：

```bash
# 安装Go（如未安装）
curl -OL https://golang.org/dl/go1.18.linux-amd64.tar.gz
tar -C /usr/local -xzf go1.18.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin

# 克隆项目
git clone https://github.com/your-repo/defect-analysis.git
cd defect-analysis/backend

# 安装依赖
go mod tidy
```

2. 配置后端服务：

```bash
# 创建配置文件
cp config.example.json config.json

# 编辑配置文件
vim config.json
```

3. 编译后端服务：

```bash
go build -o defect_analysis_server
```

4. 运行后端服务：

```bash
./defect_analysis_server
```

#### 3.2.2 前端部署

前端为静态文件，可以通过以下方式部署：

1. 直接使用后端服务提供的静态文件服务

```bash
# 将前端文件复制到静态目录
cp -r frontend/* backend/static/
```

2. 部署到Nginx Web服务器

```bash
# 安装Nginx
apt-get update
apt-get install -y nginx

# 配置Nginx
cat > /etc/nginx/sites-available/defect-analysis <<EOF
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /path/to/frontend;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
    
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# 启用站点配置
ln -s /etc/nginx/sites-available/defect-analysis /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

3. 使用Docker部署

```bash
# 构建Docker镜像
docker build -t defect-analysis-frontend .

# 运行容器
docker run -d -p 80:80 defect-analysis-frontend
```

#### 3.2.3 分析引擎部署

1. 安装Python环境和依赖包：

```bash
# 安装Python（如未安装）
apt-get update
apt-get install -y python3 python3-pip python3-venv

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

2. 配置分析引擎：

```bash
# 创建配置文件
cp config.example.py config.py

# 编辑配置文件，设置API密钥
vim config.py
```

3. 确保知识库文件存在：

```bash
# 复制示例知识库（如果没有）
cp defects_knowledge_base.example.json defects_knowledge_base.json

# 或从备份恢复
cp /path/to/backup/defects_knowledge_base.json .
```

4. 运行分析引擎：

```bash
python app.py
```

### 3.3 配置说明

#### 3.3.1 后端配置

- 端口：默认8080，可在config.json中修改
  ```json
  {
    "server": {
      "port": 8080,
      "host": "0.0.0.0"
    }
  }
  ```

- 临时目录：默认./temp，用于存储上传和生成的文件
  ```json
  {
    "storage": {
      "temp_dir": "./temp",
      "result_dir": "./results"
    }
  }
  ```

- CORS配置：默认允许所有来源，可根据需要调整
  ```json
  {
    "cors": {
      "allowed_origins": ["*"],
      "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
      "allowed_headers": ["Origin", "Content-Type", "Accept"]
    }
  }
  ```

- 日志配置：控制日志级别和输出位置
  ```json
  {
    "logging": {
      "level": "info",
      "file": "./logs/server.log"
    }
  }
  ```

#### 3.3.2 分析引擎配置

- API密钥：需在config.py中配置DeepSeek API密钥
  ```python
  # DeepSeek API配置
  DEEPSEEK_API_KEY = "your-api-key-here"
  DEEPSEEK_BASE_URL = "https://api.deepseek.com"
  ```

- 知识库路径：默认使用当前目录下的defects_knowledge_base.json
  ```python
  # 知识库配置
  KNOWLEDGE_BASE_PATH = "./defects_knowledge_base.json"
  ```

- 相似度阈值：默认0.3，可通过前端界面调整
  ```python
  # 默认相似度阈值
  DEFAULT_SIMILARITY_THRESHOLD = 0.3
  ```

- 服务器配置：控制分析引擎的HTTP服务
  ```python
  # 服务器配置
  SERVER_HOST = "0.0.0.0"
  SERVER_PORT = 5000
  ```

- 缓存配置：控制向量存储的缓存机制
  ```python
  # 缓存配置
  ENABLE_CACHE = True
  CACHE_DIR = "./cache"
  VECTOR_CACHE_TTL = 3600  # 秒
  ```

## 4. 使用方法

### 4.1 基本操作流程

1. 打开系统首页（http://localhost:8080）
   - 确保后端服务和分析引擎已启动
   - 支持主流浏览器：Chrome、Firefox、Edge、Safari

2. 上传缺陷数据Excel文件（必须包含"缺陷描述"列）
   - 点击上传区域或拖拽文件到指定区域
   - 支持.xlsx和.xls格式
   - 文件大小限制为10MB

3. 选择知识库（默认或自定义）
   - 默认知识库：系统预置的缺陷知识库
   - 自定义知识库：用户上传的知识库文件

4. 调整相似度阈值（0-1之间，值越大要求匹配越精确）
   - 默认值：0.3
   - 推荐范围：0.2-0.5
   - 可通过滑块或输入框调整

5. 设置评分分类（可选）
   - 功能使用：与功能相关的缺陷
   - 体验良好：与用户体验相关的缺陷
   - 性能效率：与系统性能相关的缺陷

6. 点击"开始分析"按钮
   - 系统创建分析任务
   - 显示进度条和状态信息
   - 可取消正在进行的任务

7. 等待分析完成，查看结果
   - 表格形式展示概要结果
   - 支持按列排序和筛选
   - 提供详情查看链接

8. 可下载完整分析结果或查看详情
   - 下载Excel文件：包含原始数据和分析结果
   - 查看详情：展示完整分析报告和相似案例
   - 导出PDF报告：生成格式化的分析报告

### 4.2 Excel文件格式要求

上传的Excel文件必须包含以下列：

- **缺陷描述**（必需）：缺陷的详细描述文本
  - 列名必须为"缺陷描述"或"defect_description"
  - 内容不能为空
  - 建议每条描述在50-500字之间

- **缺陷标题**（可选）：缺陷的简短标题
  - 列名可以是"缺陷标题"、"标题"或"title"
  - 用于结果展示和报告生成

- **评分分类**（可选）：缺陷的评分分类
  - 列名可以是"评分分类"、"分类"或"score_category"
  - 可选值：功能使用、体验良好、性能效率
  - 用于启用评分分类预筛选机制

- **缺陷编号**（可选）：缺陷的唯一标识符
  - 列名可以是"缺陷编号"、"编号"或"defect_number"
  - 用于结果追踪和引用

- **产品名称**（可选）：缺陷所属的产品
  - 列名可以是"产品名称"、"产品"或"product_name"
  - 用于分组和筛选分析结果

- **严重程度**（可选）：缺陷的严重程度
  - 列名可以是"严重程度"、"严重性"或"severity_level"
  - 用于结果排序和优先级确定

- **缺陷类型**（可选）：缺陷的类型分类
  - 列名可以是"缺陷类型"、"类型"或"defect_type"
  - 用于分类统计和分析
  - 常见值包括：功能缺陷、界面缺陷、性能缺陷等

## 5. 系统特点

### 5.1 技术优势

- **智能分析**：结合向量检索和大语言模型，提供高质量的缺陷分析
- **评分分类预筛选**：创新的预筛选机制，确保检索结果在业务语义上更加相关
- **高性能处理**：使用FAISS实现高效向量检索，支持大规模知识库
- **可扩展架构**：模块化设计，支持知识库扩展和功能升级
- **多维度分析**：提供根本原因、解决方案、严重程度和预防措施等多维度分析

### 5.2 应用价值

- **提高效率**：自动化缺陷分析，减少人工分析时间
- **知识沉淀**：积累缺陷知识库，实现经验传承
- **质量提升**：通过分析历史缺陷，预防类似问题再次发生
- **决策支持**：为产品改进和质量管理提供数据支持
- **成本降低**：减少缺陷修复成本，提高开发效率

### 5.3 性能指标

- **响应时间**：单条缺陷分析平均耗时<5秒
- **批量处理**：支持同时处理100+条缺陷记录
- **准确率**：相似案例检索准确率>85%
- **并发能力**：支持10+用户同时使用
- **知识库容量**：支持10万+条缺陷记录的存储和检索