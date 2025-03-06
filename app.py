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
    return ChatDeepSeek(
        model="deepseek-reasoner",
        api_key="sk-0ea9167338bc4daf945bf8a769ade25f",
        base_url="https://api.deepseek.com/v1",
    )

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
@st.cache_resource
def build_vector_store(_knowledge_base):
    defects = _knowledge_base['defects']
    texts = []
    metadatas = []
    
    for defect in defects:
        text = f"标题：{defect['title']}\n"
        text += f"描述：{defect['defect_description']}\n"
        text += f"引入阶段：{defect['introduction_phase']}\n"
        
        metadata = {
            'id': defect['id'],
            'defect_number': defect['defect_number'],
            'product_name': defect['product_name']
        }
        
        texts.append(text)
        metadatas.append(metadata)
    
    vector_store = FAISS.from_texts(texts, init_embeddings(), metadatas=metadatas)
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
    similar_docs = vector_store.similarity_search(
        defect_description,
        k=3
    )
    
    # 构建增强的上下文
    context = "历史相似案例：\n"
    for i, doc in enumerate(similar_docs, 1):
        context += f"案例{i}：\n{doc.page_content}\n\n"
    
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
                analyze_defect(defect_description, vector_store, llm)
        else:
            st.warning("请先输入缺陷描述")

if __name__ == "__main__":
    main()