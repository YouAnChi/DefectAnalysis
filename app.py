import json
import pandas as pd
from langchain_deepseek import ChatDeepSeek
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

# 初始化LLM模型
def init_llm():
    try:
        llm = ChatDeepSeek(
            model="deepseek-reasoner",
            api_key="sk-f2c874ce43b2492a9cb96e74dd282b28",
            base_url="https://api.deepseek.com",
        )
        # 测试API连接
        llm.invoke([{"role": "user", "content": "测试连接"}])
        return llm
    except Exception as e:
        print(f"初始化LLM模型失败: {str(e)}")
        return None

# 初始化向量化模型
def init_embeddings():
    return HuggingFaceEmbeddings(model_name='shibing624/text2vec-base-chinese')

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
def build_vector_store(_knowledge_base):
    defects = _knowledge_base['defects']
    texts = []
    metadatas = []
    
    for defect in defects:
        text = defect['defect_description']
        metadata = {
            'id': defect['id'],
            'defect_number': defect['defect_number'],
            'product_name': defect['product_name'],
            'title': defect['title'],
            'work_order': defect.get('work_order', ''),
            'occurrence_probability': defect.get('occurrence_probability', ''),
            'score_category': defect.get('score_category', ''),
            'severity_level': defect.get('severity_level', ''),
            'defect_type': defect.get('defect_type', ''),
            'defect_scenario': defect.get('defect_scenario', ''),
            'introduction_phase': defect.get('introduction_phase', ''),
            'source': defect['metadata']['source']
        }
        texts.append(text)
        metadatas.append(metadata)
    
    vector_store = FAISS.from_texts(texts, init_embeddings(), metadatas=metadatas)
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
def analyze_defect(defect_description, vector_store, llm):
    similar_docs = vector_store.similarity_search_with_score(
        defect_description,
        k=3
    )
    
    context = "历史相似案例：\n"
    for i, (doc, score) in enumerate(similar_docs, 1):
        similarity = 100 / (1 + score)
        context += f"案例{i}（相似度: {similarity:.2f}%）：\n{doc.page_content}\n"
        if hasattr(doc, 'metadata') and doc.metadata:
            context += "元数据信息:\n"
            for key, value in doc.metadata.items():
                if value and str(value).lower() != 'nan' and key != 'source':
                    context += f"{key}: {value}\n"
            context += "\n"
    
    system_prompt = load_system_prompt('sys.md')
    if system_prompt is None:
        system_prompt = "你是一个专业的缺陷分析专家，请分析给定缺陷的可能原因和解决方案。"
    
    messages = [
        ("system", system_prompt),
        ("human", f"请基于以下历史案例分析当前缺陷：\n\n{context}\n当前缺陷描述：\n{defect_description}")
    ]
    
    reasoning_content = ""
    answer_content = ""
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'additional_kwargs') and 'reasoning_content' in chunk.additional_kwargs:
            reasoning_content += chunk.additional_kwargs['reasoning_content']
        elif chunk.text():
            answer_content += chunk.text()
    
    return reasoning_content, answer_content

def main():
    print("正在初始化系统...")
    
    # 加载知识库
    knowledge_base = load_knowledge_base('defects_knowledge_base.json')
    if knowledge_base is None:
        print("加载知识库失败，程序退出")
        return
    
    # 构建向量存储
    vector_store = build_vector_store(knowledge_base)
    
    # 初始化LLM模型
    llm = init_llm()
    if llm is None:
        print("LLM模型初始化失败，程序退出")
        return
    
    try:
        # 读取Excel文件
        df = pd.read_excel('缺陷1.xlsx')
        if '缺陷描述' not in df.columns:
            print("错误：Excel文件中没有'缺陷描述'列")
            return
        
        # 创建结果DataFrame
        results_df = pd.DataFrame()
        results_df['缺陷描述'] = df['缺陷描述']
        results_df['推理过程'] = ''
        results_df['分析结果'] = ''
        
        # 逐行处理缺陷描述
        total_rows = len(df)
        for index, row in df.iterrows():
            print(f"\n正在处理第 {index + 1}/{total_rows} 条缺陷描述...")
            defect_description = row['缺陷描述']
            if pd.isna(defect_description) or not str(defect_description).strip():
                print(f"跳过第 {index + 1} 行：缺陷描述为空")
                continue
            
            try:
                reasoning, analysis = analyze_defect(str(defect_description), vector_store, llm)
                results_df.at[index, '推理过程'] = reasoning
                results_df.at[index, '分析结果'] = analysis
                print(f"第 {index + 1} 条处理完成")
            except Exception as e:
                print(f"处理第 {index + 1} 条时出错: {str(e)}")
                results_df.at[index, '推理过程'] = f"处理出错: {str(e)}"
                results_df.at[index, '分析结果'] = f"处理出错: {str(e)}"
        
        # 保存结果到新的Excel文件
        output_file = '缺陷分析结果.xlsx'
        results_df.to_excel(output_file, index=False)
        print(f"\n分析完成！结果已保存到 {output_file}")
        
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()