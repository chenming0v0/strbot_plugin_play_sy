import json
import os
import datetime
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("astrbot")

@dataclass
class Memory:
    """记忆数据结构"""
    content: str
    importance: int
    timestamp: str
    session_id: str
    memory_id: str

class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, data_file: str, config: dict):
        self.data_file = data_file
        self.config = config
        self.memories: Dict[str, List[Dict]] = {}
        self._load_memories()
    
    def _load_memories(self):
        """加载记忆数据"""
        if not os.path.exists(self.data_file):
            with open(self.data_file, "w", encoding='utf-8') as f:
                f.write("{}")
        
        try:
            with open(self.data_file, "r", encoding='utf-8') as f:
                self.memories = json.load(f)
        except Exception as e:
            logger.error(f"加载记忆数据失败: {e}")
            self.memories = {}
    
    async def save_memories(self):
        """保存记忆到文件"""
        try:
            # 清理过期记忆
            self._clean_expired_memories()
            
            with open(self.data_file, "w", encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存记忆数据失败: {e}")
    
    def _clean_expired_memories(self):
        """清理过期的记忆"""
        if not self.config.get("memory_expire_days", 0):
            return
        
        expire_days = self.config["memory_expire_days"]
        current_time = datetime.datetime.now()
        
        for session_id in list(self.memories.keys()):
            memories = self.memories[session_id]
            # 过滤掉过期的记忆
            valid_memories = []
            for memory in memories:
                try:
                    memory_time = datetime.datetime.strptime(memory["timestamp"], "%Y-%m-%d %H:%M:%S")
                    if (current_time - memory_time).days < expire_days:
                        valid_memories.append(memory)
                except:
                    # 如果时间格式错误，保留记忆
                    valid_memories.append(memory)
            
            if valid_memories:
                self.memories[session_id] = valid_memories
            else:
                del self.memories[session_id]
    
    def add_memory(self, session_id: str, content: str, importance: int = 1, tags: List[str] = None) -> bool:
        """添加记忆，支持标签"""
        if not self.config.get("enable_memory_management", True):
            logger.warning("[MemoryManager] 记忆管理功能已禁用")
            return False
        
        if session_id not in self.memories:
            self.memories[session_id] = []
            logger.debug(f"[MemoryManager] 为会话 {session_id} 创建新的记忆列表")
        
        max_memories = self.config.get("max_memories", 100)
        current_count = len(self.memories[session_id])
        logger.debug(f"[MemoryManager] 当前会话记忆数: {current_count}/{max_memories}")
        
        # 如果记忆数量超限，智能删除
        if current_count >= max_memories:
            # 按重要性和时间综合排序，删除最不重要且最旧的
            self.memories[session_id].sort(key=lambda x: (x["importance"], x["timestamp"]))
            
            # 保护5星记忆，优先删除3星及以下的
            low_importance = [m for m in self.memories[session_id] if m["importance"] <= 3]
            if low_importance:
                # 删除最旧的低重要性记忆
                removed = low_importance[0]
                self.memories[session_id].remove(removed)
                logger.info(f"[MemoryManager] 删除低重要性记忆: {removed['content'][:50]}... (重要性:{removed['importance']})")
            else:
                # 如果都是高重要性记忆，删除最旧的
                removed = self.memories[session_id].pop(0)
                logger.info(f"[MemoryManager] 删除最旧记忆: {removed['content'][:50]}... (重要性:{removed['importance']})")
        
        # 合并自定义标签和自动提取的标签
        auto_tags = self._extract_tags(content)
        if tags:
            # 用户自定义标签优先，然后添加自动提取的标签（去重）
            all_tags = list(set(tags + auto_tags))
            logger.debug(f"[MemoryManager] 标签合并 - 自定义: {tags}, 自动: {auto_tags}, 最终: {all_tags}")
        else:
            all_tags = auto_tags
            logger.debug(f"[MemoryManager] 自动提取标签: {all_tags}")
        
        memory = {
            "content": content,
            "importance": min(max(importance, 1), 5),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "memory_id": f"{session_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "tags": all_tags
        }
        
        self.memories[session_id].append(memory)
        logger.info(f"[MemoryManager] 成功添加记忆 - ID: {memory['memory_id']}, 重要性: {memory['importance']}, 标签数: {len(all_tags)}")
        return True
    
    def _extract_tags(self, content: str) -> List[str]:
        """智能提取标签 - 基于内容动态生成"""
        tags = []
        content_lower = content.lower()
        
        # 动态提取重要关键词作为标签
        # 1. 提取人名（如果包含特定人名）
        names = ["辰林", "小辰", "辰林鸭", "凌风"]
        for name in names:
            if name in content:
                tags.append(f"人物:{name}")
        
        # 2. 提取地点
        locations = {
            "实验室": ["实验室", "lab"],
            "学校": ["学校", "大学", "校园", "教室", "课堂"],
            "家": ["家里", "家中", "公寓", "卧室", "客厅", "浴室"],
            "户外": ["海边", "游乐园", "摩天轮", "过山车", "海洋馆"]
        }
        for location, keywords in locations.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(f"地点:{location}")
        
        # 3. 提取事件类型
        events = {
            "灵魂交换": ["灵魂交换", "身体交换", "交换身体", "换身"],
            "战斗": ["战斗", "攻击", "袭击", "打斗", "刺客"],
            "实验": ["实验", "研究", "测试", "普罗米修斯", "创世纪"],
            "约会": ["约会", "逛街", "吃饭", "看电影"],
            "游戏": ["游戏", "玩", "高达", "拼装"]
        }
        for event, keywords in events.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(f"事件:{event}")
        
        # 4. 提取情感标签
        emotions = {
            "爱情": ["爱", "喜欢", "亲吻", "拥抱", "永远在一起"],
            "恐惧": ["害怕", "恐惧", "担心", "紧张"],
            "羞耻": ["羞", "害羞", "脸红", "尴尬"],
            "保护": ["保护", "守护", "安全"]
        }
        for emotion, keywords in emotions.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(f"情感:{emotion}")
        
        # 5. 提取物品/道具
        items = {
            "武器": ["虚空之刃", "刀", "剑", "武器"],
            "科技设备": ["矩阵", "仪器", "设备", "相机", "维生舱"],
            "服装": ["裙子", "旗袍", "比基尼", "衣服", "制服"]
        }
        for item_type, keywords in items.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(f"物品:{item_type}")
        
        # 6. 时间标签（如果提到）
        time_keywords = {
            "早晨": ["早晨", "早上", "清晨"],
            "晚上": ["晚上", "夜晚", "深夜"],
            "过去": ["之前", "以前", "曾经"],
            "未来": ["以后", "将来", "未来"]
        }
        for time_tag, keywords in time_keywords.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(f"时间:{time_tag}")
        
        # 7. 提取数字相关（第几次等）
        import re
        numbers = re.findall(r'第[一二三四五六七八九十\d]+[次个]', content)
        for num in numbers:
            tags.append(f"序号:{num}")
        
        # 8. 根据重要性自动标记
        if "重要" in content_lower or "记住" in content_lower or "务必" in content_lower:
            tags.append("标记:重要")
        
        # 如果没有任何标签，不强制添加"其他"，让标签列表可以为空
        # 这样更真实，有些记忆可能就是没有明显的标签
        
        # 去重并返回
        return list(set(tags))
    
    def get_memories(self, session_id: str) -> List[Dict]:
        """获取指定会话的记忆"""
        if not self.config.get("enable_memory_management", True):
            return []
        
        return self.memories.get(session_id, [])
    
    def get_memories_sorted(self, session_id: str) -> List[Dict]:
        """获取按重要性排序的记忆"""
        memories = self.get_memories(session_id)
        return sorted(memories, key=lambda x: x["importance"], reverse=True)
    
    def remove_memory(self, session_id: str, index: int) -> Optional[Dict]:
        """删除指定序号的记忆"""
        if session_id not in self.memories:
            return None
        
        memories = self.memories[session_id]
        if index < 0 or index >= len(memories):
            return None
        
        return memories.pop(index)
    
    def clear_memories(self, session_id: str) -> bool:
        """清空指定会话的所有记忆"""
        if session_id in self.memories:
            del self.memories[session_id]
            return True
        return False
    
    def update_memory_importance(self, session_id: str, index: int, importance: int) -> bool:
        """更新记忆的重要性"""
        if session_id not in self.memories:
            return False
        
        memories = self.memories[session_id]
        if index < 0 or index >= len(memories):
            return False
        
        memories[index]["importance"] = min(max(importance, 1), 5)
        return True
    
    def search_memories(self, session_id: str, keyword: str) -> List[Dict]:
        """搜索记忆，支持多关键词"""
        memories = self.get_memories(session_id)
        if not keyword:
            logger.debug(f"[MemoryManager] 搜索关键词为空，返回所有 {len(memories)} 条记忆")
            return memories
        
        # 支持多关键词搜索
        keywords = keyword.lower().split()
        logger.info(f"[MemoryManager] 搜索记忆 - 会话: {session_id}, 关键词: {keywords}")
        
        results = []
        
        for memory in memories:
            content_lower = memory["content"].lower()
            # 检查是否包含任意一个关键词
            if any(kw in content_lower for kw in keywords):
                # 计算匹配度（匹配的关键词数量）
                match_count = sum(1 for kw in keywords if kw in content_lower)
                memory_copy = memory.copy()
                memory_copy['match_score'] = match_count
                results.append(memory_copy)
                logger.debug(f"[MemoryManager] 匹配记忆: {memory['content'][:50]}... (匹配度:{match_count}, 重要性:{memory['importance']})")
        
        # 按匹配度和重要性排序
        results.sort(key=lambda x: (x.get('match_score', 0), x["importance"]), reverse=True)
        
        # 移除临时的match_score字段
        for result in results:
            result.pop('match_score', None)
        
        logger.info(f"[MemoryManager] 搜索完成 - 找到 {len(results)} 条匹配的记忆")
        
        # 记录5星记忆数量
        five_star_count = len([r for r in results if r["importance"] == 5])
        if five_star_count > 0:
            logger.info(f"[MemoryManager] 其中包含 {five_star_count} 条5星记忆")
        
        return results
    
    def get_memory_stats(self, session_id: str) -> Dict:
        """获取记忆统计信息"""
        memories = self.get_memories(session_id)
        if not memories:
            return {
                "total": 0,
                "avg_importance": 0,
                "importance_distribution": {},
                "tag_distribution": {}
            }
        
        total = len(memories)
        avg_importance = sum(m["importance"] for m in memories) / total
        
        # 重要性分布
        importance_dist = {}
        for i in range(1, 6):
            importance_dist[i] = len([m for m in memories if m["importance"] == i])
        
        # 标签分布
        tag_dist = {}
        for memory in memories:
            for tag in memory.get("tags", ["其他"]):
                tag_dist[tag] = tag_dist.get(tag, 0) + 1
        
        return {
            "total": total,
            "avg_importance": round(avg_importance, 2),
            "importance_distribution": importance_dist,
            "tag_distribution": tag_dist
        }
    
    def search_by_tag(self, session_id: str, tag: str) -> List[Dict]:
        """按标签搜索记忆"""
        memories = self.get_memories(session_id)
        if not tag:
            return memories
        
        # 搜索包含指定标签的记忆
        results = [memory for memory in memories if tag in memory.get("tags", [])]
        
        # 按重要性排序
        results.sort(key=lambda x: x["importance"], reverse=True)
        
        return results
    
    def get_all_tags(self, session_id: str) -> List[str]:
        """获取所有标签"""
        memories = self.get_memories(session_id)
        tags = set()
        
        for memory in memories:
            for tag in memory.get("tags", ["其他"]):
                tags.add(tag)
        
        return sorted(list(tags))