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
    
    def add_memory(self, session_id: str, content: str, importance: int = 1) -> bool:
        """添加记忆"""
        if not self.config.get("enable_memory_management", True):
            return False
        
        if session_id not in self.memories:
            self.memories[session_id] = []
        
        max_memories = self.config.get("max_memories", 10)
        
        # 如果记忆数量超限，删除最不重要的
        if len(self.memories[session_id]) >= max_memories:
            self.memories[session_id].sort(key=lambda x: x["importance"])
            self.memories[session_id].pop(0)
        
        memory = {
            "content": content,
            "importance": min(max(importance, 1), 5),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "memory_id": f"{session_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        self.memories[session_id].append(memory)
        return True
    
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
        """搜索记忆"""
        memories = self.get_memories(session_id)
        if not keyword:
            return memories
        
        return [memory for memory in memories if keyword.lower() in memory["content"].lower()]
    
    def get_memory_stats(self, session_id: str) -> Dict:
        """获取记忆统计信息"""
        memories = self.get_memories(session_id)
        if not memories:
            return {
                "total": 0,
                "avg_importance": 0,
                "importance_distribution": {}
            }
        
        total = len(memories)
        avg_importance = sum(m["importance"] for m in memories) / total
        
        # 重要性分布
        importance_dist = {}
        for i in range(1, 6):
            importance_dist[i] = len([m for m in memories if m["importance"] == i])
        
        return {
            "total": total,
            "avg_importance": round(avg_importance, 2),
            "importance_distribution": importance_dist
        } 