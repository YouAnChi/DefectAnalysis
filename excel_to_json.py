import pandas as pd
import json
from datetime import datetime

def generate_defect_id(index):
    return f"DEF{str(index + 1).zfill(3)}"

def generate_defect_number(index):
    return f"DEFNUM{str(index + 1).zfill(3)}"

def generate_work_order():
    current_date = datetime.now().strftime("%Y%m%d")
    return f"WO{current_date}001"

def excel_to_json(excel_file):
    # 读取Excel文件
    df = pd.read_excel(excel_file)
    
    defects = []
    for index, row in df.iterrows():
        defect = {
            "id": generate_defect_id(index),
            "defect_number": row.get('缺陷编号', generate_defect_number(index)),
            "title": row.get('标题', ''),
            "product_name": row.get('产品名称', ''),
            "work_order": row.get('工单编号', generate_work_order()),
            "occurrence_probability": row.get('发生概率', ''),
            "defect_description": row.get('缺陷描述', ''),
            "score_category": row.get('评分分类', ''),
            "severity_level": row.get('严重等级', ''),
            "defect_type": row.get('缺陷类型', ''),
            "defect_scenario": row.get('缺陷场景', ''),
            "introduction_phase": row.get('缺陷引入阶段', ''),
            "metadata": {
                "source": row.get('问题来源', ''),
                "tags": [],  # 可以根据描述提取关键词
                "created_at": row.get('创建时间', ''),
                "resolution_status": row.get('问题状态', ''),
                "learning_count": row.get('学习次数', 0),
                "like_count": row.get('获赞次数', 0),
                "is_historical": row.get('是否历史缺陷', False),
                "is_common": row.get('是否共性缺陷', False),
                "notes": row.get('备注说明', ''),
                "closure_reason": row.get('问题关闭/挂起原因', ''),
                "attachments": row.get('附件图片', '').split(',') if row.get('附件图片') and pd.notna(row.get('附件图片')) else []
            },
            "similar_cases": [],  # 可以通过相似度计算添加
            "solutions": []  # 可以通过分析描述提取解决方案
        }
        defects.append(defect)
    
    knowledge_base = {
        "defects": defects,
        "metadata": {
            "version": "1.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "total_records": len(defects),
            "schema_version": "1.0.0"
        }
    }
    
    return knowledge_base

def save_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    excel_file = '缺陷1.xlsx'
    output_file = 'defects_knowledge_base.json'
    
    try:
        knowledge_base = excel_to_json(excel_file)
        save_json(knowledge_base, output_file)
        print(f"Successfully converted {excel_file} to {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()