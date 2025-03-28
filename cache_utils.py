import os
import json
import hashlib
import logging
from datetime import datetime, timedelta

class VectorSearchCache:
    """
    向量检索结果缓存工具类，用于缓存相似案例检索结果，减少重复计算
    """
    def __init__(self, cache_dir=".cache", cache_ttl=24):
        """
        初始化缓存工具
        
        Args:
            cache_dir: 缓存目录
            cache_ttl: 缓存有效期（小时）
        """
        self.cache_dir = cache_dir
        self.cache_ttl = timedelta(hours=cache_ttl)
        
        # 确保缓存目录存在
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
                logging.info(f"创建缓存目录: {cache_dir}")
            except Exception as e:
                logging.error(f"创建缓存目录失败: {str(e)}")
    
    def _generate_key(self, query, score_category, k):
        """
        生成缓存键
        
        Args:
            query: 查询文本
            score_category: 评分分类
            k: 检索数量
            
        Returns:
            str: 缓存键
        """
        # 使用查询文本、评分分类和检索数量生成唯一键
        key_str = f"{query}_{score_category}_{k}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def get(self, query, score_category, k):
        """
        获取缓存结果
        
        Args:
            query: 查询文本
            score_category: 评分分类
            k: 检索数量
            
        Returns:
            list or None: 缓存结果，如果缓存不存在或已过期则返回None
        """
        key = self._generate_key(query, score_category, k)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time > self.cache_ttl:
                logging.info(f"缓存已过期: {key}")
                return None
            
            logging.info(f"命中缓存: {key}")
            return cache_data['results']
        except Exception as e:
            logging.warning(f"读取缓存失败: {str(e)}")
            return None
    
    def set(self, query, score_category, k, results):
        """
        设置缓存结果
        
        Args:
            query: 查询文本
            score_category: 评分分类
            k: 检索数量
            results: 检索结果
        """
        key = self._generate_key(query, score_category, k)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        
        try:
            # 将检索结果转换为可序列化的格式
            serializable_results = []
            for doc, score in results:
                doc_dict = {
                    'page_content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': score
                }
                serializable_results.append(doc_dict)
            
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'results': serializable_results
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"缓存已保存: {key}")
        except Exception as e:
            logging.warning(f"保存缓存失败: {str(e)}")
    
    def clear_expired(self):
        """
        清理过期缓存
        """
        try:
            count = 0
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue
                
                cache_file = os.path.join(self.cache_dir, filename)
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    cache_time = datetime.fromisoformat(cache_data['timestamp'])
                    if datetime.now() - cache_time > self.cache_ttl:
                        os.remove(cache_file)
                        count += 1
                except Exception:
                    # 如果文件损坏，直接删除
                    os.remove(cache_file)
                    count += 1
            
            logging.info(f"已清理 {count} 个过期缓存文件")
        except Exception as e:
            logging.error(f"清理过期缓存失败: {str(e)}")