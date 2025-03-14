import streamlit as st
import json
from langchain_deepseek import ChatDeepSeek
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

# 设置页面标题
st.set_page_config(page_title="智能缺陷分析系统", layout="wide")

# 初始化LLM模型
@st.cache_resource
def init_llm():
    try:
        llm = ChatDeepSeek(
            model="deepseek-reasoner",
            api_key="sk-f2c874ce43b2492a94354354ghygh",
            base_url="https://api.deepseek.com",
        )
        # 测试API连接
        llm.invoke([{"role": "user", "content": "测试连接"}])
        return llm
    except Exception as e:
        st.error(f"初始化LLM模型失败: {str(e)}")
        return None

# 初始化向量化模型
@st.cache_resource
def init_embeddings():
    return HuggingFaceEmbeddings(model_name='shibing624/text2vec-base-chinese')

# 加载知识库
@st.cache_data
def load_knowledge_base(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
            return knowledge_base
    except Exception as e:
        st.error(f"读取知识库文件失败: {e}")
        return None

# 构建向量存储
# @st.cache_resource 装饰器用于缓存函数的返回值，避免重复计算
# 当输入参数相同时，直接返回缓存的结果，提高性能
@st.cache_resource
def build_vector_store(_knowledge_base):
    # 从知识库中获取缺陷列表
    defects = _knowledge_base['defects']
    # 初始化两个列表：texts用于存储文本内容，metadatas用于存储元数据
    texts = []
    metadatas = []
    
    # 遍历每个缺陷记录，构建文本内容和元数据
    for defect in defects:
        # 只使用缺陷描述字段作为向量化和相似度计算的依据
        text = defect['defect_description']
        
        # 构建元数据字典，用于存储辅助信息
        # 这些信息不参与向量化和相似度计算，但可用于检索和显示
        metadata = {
            'id': defect['id'],  # 缺陷的唯一标识符
            'defect_number': defect['defect_number'],  # 缺陷的业务编号
            'product_name': defect['product_name'],  # 关联的产品名称
            'title': defect['title'],  # 缺陷标题
            'work_order': defect.get('work_order', ''),  # 工单号
            'occurrence_probability': defect.get('occurrence_probability', ''),  # 发生概率
            'score_category': defect.get('score_category', ''),  # 评分类别
            'severity_level': defect.get('severity_level', ''),  # 严重程度
            'defect_type': defect.get('defect_type', ''),  # 缺陷类型
            'defect_scenario': defect.get('defect_scenario', ''),  # 缺陷场景
            'introduction_phase': defect.get('introduction_phase', ''),  # 引入阶段
            'source': defect['metadata']['source']  # 数据来源，用于后续筛选
        }
        
        # 将处理好的文本和元数据添加到对应的列表中
        texts.append(text)
        metadatas.append(metadata)
    
    # 使用FAISS创建向量存储
    # texts: 文本内容列表，将被转换为向量
    # init_embeddings(): 初始化文本向量化模型
    # metadatas: 元数据列表，与文本一一对应
    vector_store = FAISS.from_texts(texts, init_embeddings(), metadatas=metadatas)
    # 返回构建好的向量存储，供后续相似度检索使用
    return vector_store

# 读取系统提示文件
@st.cache_data
def load_system_prompt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        st.error(f"读取系统提示文件失败: {e}")
        return None

# 分析缺陷
def analyze_defect(defect_description, vector_store, llm):
    # 检索相似案例
    similar_docs = vector_store.similarity_search_with_score(
        defect_description,
        k=3
    )
    
    # 构建增强的上下文
    context = "历史相似案例：\n"
    
    # 创建相似度得分展示区域
    st.markdown("### 相似案例向量相似度")
    for i, (doc, score) in enumerate(similar_docs, 1):
        # 计算相似度百分比（FAISS返回的是L2距离，需要转换为相似度）
        similarity = 100 / (1 + score)  # 使用倒数转换，确保相似度在0-100之间
        
        # 显示相似度信息
        st.write(f"**案例 {i} 相似度: {similarity:.2f}%**")
        st.write(f"内容: {doc.page_content}")
        
        # 显示元数据信息
        if hasattr(doc, 'metadata') and doc.metadata:
            st.write("**元数据信息:**")
            metadata_info = ""
            for key, value in doc.metadata.items():
                if value and str(value).lower() != 'nan' and key != 'source':
                    metadata_info += f"- {key}: {value}\n"
            st.write(metadata_info)
        st.write("---")
        
        # 添加到上下文，包含更多元数据信息
        context += f"案例{i}：\n{doc.page_content}\n"
        if hasattr(doc, 'metadata') and doc.metadata:
            context += "元数据信息:\n"
            for key, value in doc.metadata.items():
                if value and str(value).lower() != 'nan' and key != 'source':
                    context += f"{key}: {value}\n"
            context += "\n"
    
    # 加载系统提示
    system_prompt = load_system_prompt('sys.md')
    if system_prompt is None:
        st.warning("无法加载系统提示，使用默认提示")
        system_prompt = "你是一个专业的缺陷分析专家，请分析给定缺陷的可能原因和解决方案。"
    
    # 构建消息
    messages = [
        ("system", system_prompt),
        ("human", f"请基于以下历史案例分析当前缺陷：\n\n{context}\n当前缺陷描述：\n{defect_description}")
    ]
    
    reasoning_content = ""
    answer_content = ""
    is_answering = False
    
    # 创建两个空的占位符用于显示推理过程和分析结果
    reasoning_placeholder = st.empty()
    analysis_placeholder = st.empty()
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'additional_kwargs') and 'reasoning_content' in chunk.additional_kwargs:
            reasoning_content += chunk.additional_kwargs['reasoning_content']
            reasoning_placeholder.markdown(f"**推理过程：**\n{reasoning_content}")
        elif chunk.text():
            if not is_answering:
                is_answering = True
            answer_content += chunk.text()
            analysis_placeholder.markdown(f"**分析结果：**\n{answer_content}")
    
    return reasoning_content, answer_content

def main():
    st.title("智能缺陷分析系统")
    
    # 添加系统说明
    st.markdown("""
    ### 系统说明
    1. 本系统基于历史缺陷知识库，使用AI技术对新的缺陷进行智能分析
    2. 请在下方输入框中详细描述缺陷情况
    3. 系统将自动检索相似案例并给出分析结果
    """)
    
    # 加载知识库
    knowledge_base = load_knowledge_base('defects_knowledge_base.json')
    if knowledge_base is None:
        st.error("加载知识库失败，请检查文件是否存在")
        return
    
    # 构建向量存储
    vector_store = build_vector_store(knowledge_base)
    
    # 创建文本输入区域
    defect_description = st.text_area(
        "请输入缺陷描述：",
        height=150,
        placeholder="在此输入缺陷的详细描述..."
    )
    
    # 添加分析按钮
    if st.button("开始分析", type="primary"):
        if defect_description.strip():
            with st.spinner("正在分析中...请稍候"):
                llm = init_llm()
                if llm is None:
                    st.error("LLM模型初始化失败，请检查API配置或稍后重试")
                    return
                analyze_defect(defect_description, vector_store, llm)
        else:
            st.warning("请先输入缺陷描述")

if __name__ == "__main__":
    main()