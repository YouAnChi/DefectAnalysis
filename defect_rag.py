import json
import pandas as pd
from langchain_deepseek import ChatDeepSeek
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter

# 初始化LLM模型
llm = ChatDeepSeek(
    model="deepseek-reasoner",
    api_key="sk-0ea9167338bc4daf945bf8a769ade25f",
    base_url="https://api.deepseek.com/v1",
)

# 初始化向量化模型
embeddings = HuggingFaceEmbeddings(model_name='shibing624/text2vec-base-chinese')

# 加载知识库
def load_knowledge_base(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
            return knowledge_base
    except Exception as e:
        print(f"读取知识库文件失败: {e}")
        return None

# 构建向量存储
def build_vector_store(knowledge_base):
    defects = knowledge_base['defects']
    texts = []
    metadatas = []
    
    for defect in defects:
        # 将缺陷信息组合成文本
        text = f"标题：{defect['title']}\n"
        text += f"描述：{defect['defect_description']}\n"
        text += f"引入阶段：{defect['introduction_phase']}\n"
        
        # 保存元数据
        metadata = {
            'id': defect['id'],
            'defect_number': defect['defect_number'],
            'product_name': defect['product_name']
        }
        
        texts.append(text)
        metadatas.append(metadata)
    
    # 创建向量存储
    vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    return vector_store

# 读取系统提示文件
def load_system_prompt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"读取系统提示文件失败: {e}")
        return None

# 分析缺陷
def analyze_defect(defect_description, vector_store):
    # 检索相似案例
    similar_docs = vector_store.similarity_search(
        defect_description,
        k=3  # 获取前3个最相似的案例
    )
    
    # 构建增强的上下文
    context = "历史相似案例：\n"
    for i, doc in enumerate(similar_docs, 1):
        context += f"案例{i}：\n{doc.page_content}\n\n"
    
    # 加载系统提示
    system_prompt = load_system_prompt('sys.md')
    if system_prompt is None:
        print("无法加载系统提示，使用默认提示")
        system_prompt = "你是一个专业的缺陷分析专家，请分析给定缺陷的可能原因和解决方案。"
    
    # 构建消息
    messages = [
        ("system", system_prompt),
        ("human", f"请基于以下历史案例分析当前缺陷：\n\n{context}\n当前缺陷描述：\n{defect_description}")
    ]
    
    reasoning_content = ""
    answer_content = ""
    is_answering = False
    
    print("\n" + "=" * 20 + "分析过程" + "=" * 20 + "\n")
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'additional_kwargs') and 'reasoning_content' in chunk.additional_kwargs:
            reasoning_content += chunk.additional_kwargs['reasoning_content']
            print(chunk.additional_kwargs['reasoning_content'], end='', flush=True)
        elif chunk.text():
            if not is_answering:
                print("\n" + "=" * 20 + "分析结果" + "=" * 20 + "\n")
                is_answering = True
            answer_content += chunk.text()
            print(chunk.text(), end='', flush=True)
    
    return reasoning_content, answer_content

def main():
    # 加载知识库
    knowledge_base = load_knowledge_base('defects_knowledge_base.json')
    if knowledge_base is None:
        print("加载知识库失败，程序退出")
        return
    
    # 构建向量存储
    vector_store = build_vector_store(knowledge_base)
    print("知识库向量化完成，开始分析...")
    
    # 从终端获取用户输入的缺陷描述
    print("\n请输入缺陷描述：")
    defect_description = input().strip()
    if defect_description:
        reasoning, analysis = analyze_defect(defect_description, vector_store)
        print(f"推理过程：\n{reasoning}")
        print(f"分析结果：\n{analysis}")

if __name__ == "__main__":
    main()