# 基于RAG的智能缺陷分析系统

## 项目概述
本项目是一个基于检索增强生成（RAG）技术的智能缺陷分析系统，通过Streamlit提供友好的Web界面，结合历史缺陷案例知识库，为新的缺陷问题提供智能化的分析和解决方案。系统利用向量检索技术实现相似案例的精准匹配，并结合大语言模型进行深度分析，提供专业的缺陷原因分析和解决方案建议。

## 系统架构

### 核心组件
1. **LLM模型服务**
   - 使用DeepSeek Reasoner模型
   - 支持流式输出和推理过程可视化
   - 提供专业的缺陷分析能力

2. **向量化引擎**
   - 采用HuggingFace的text2vec-base-chinese模型
   - 支持中文文本的高质量向量化

3. **向量存储**
   - 使用FAISS向量数据库
   - 支持高效的相似度检索

4. **知识库管理**
   - JSON格式存储历史缺陷案例
   - 支持结构化的缺陷信息管理

5. **Web界面**
   - 基于Streamlit构建的交互式界面
   - 提供直观的缺陷分析操作体验
   - 实时展示分析结果和推理过程

## 使用指南

### 启动系统
1. 确保已安装所有依赖包：
   ```bash
   pip install -r requirements.txt
   ```

2. 启动Streamlit应用：
   ```bash
   streamlit run app.py
   ```

3. 在浏览器中访问：http://localhost:8501

### Web界面操作
1. **缺陷描述输入**
   - 在文本输入框中输入需要分析的缺陷描述
   - 描述应尽可能详细，包含关键信息

2. **分析结果查看**
   - 系统会自动检索相似的历史案例
   - 展示分析推理过程
   - 提供详细的原因分析和解决方案

3. **相似案例展示**
   - 显示检索到的相似历史案例
   - 包含案例的详细信息和处理方法

## 配置说明

### 环境依赖
```
langchain_deepseek
langchain
faiss-cpu
torch
transformers
pandas
streamlit
```

### 关键配置
1. **API配置**
   ```python
   llm = ChatDeepSeek(
       model="deepseek-reasoner",
       api_key="your-api-key",
       base_url="https://api.deepseek.com/v1"
   )
   ```

2. **向量模型配置**
   ```python
   embeddings = HuggingFaceEmbeddings(
       model_name='shibing624/text2vec-base-chinese'
   )
   ```

## 数据格式说明

### 知识库格式
```json
{
    "defects": [
        {
            "id": "1",
            "defect_number": "DEF-001",
            "title": "缺陷标题",
            "defect_description": "缺陷详细描述",
            "introduction_phase": "引入阶段",
            "product_name": "产品名称"
        }
    ]
}
```

## 系统特点

1. **智能检索**
   - 基于语义的相似度匹配
   - 支持多维度的缺陷特征分析

2. **深度分析**
   - 结合历史经验的分析推理
   - 专业的解决方案建议

3. **实时反馈**
   - 流式输出分析过程
   - 清晰的推理路径展示

4. **友好界面**
   - 简洁直观的Web操作界面
   - 实时交互和结果展示
   - 支持多种数据可视化方式

## 注意事项

1. 确保知识库文件格式正确
2. 系统提示文件对分析质量有重要影响
3. 输入的缺陷描述应尽可能详细和准确
4. 需要稳定的网络连接以访问API服务
5. Web界面支持主流浏览器访问

## 优化建议

1. 定期更新和维护知识库
2. 根据实际应用场景优化系统提示
3. 适当调整相似案例的返回数量
4. 收集用户反馈改进系统
5. 优化Web界面的用户体验