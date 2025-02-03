from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register    
from astrbot.api.event.filter import command, command_group, event_message_type
from astrbot.core.star.filter.event_message_type import EventMessageType
import json
import os
import datetime
import logging
from typing import List, Dict
from astrbot.api import llm_tool, logger

logger = logging.getLogger("astrbot")

@register("ai_memory", "kjqwdw", "一个AI记忆管理插件", "1.0.0")
class Main(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.PLUGIN_NAME = "strbot_plugin_play_sy"
        
        # 获取插件目录路径
        self.plugin_path = os.path.abspath(os.path.dirname(__file__))
        
        # 从配置中获取最大记忆数
        self.max_memories = config.get("max_memories", 10)
        
        # 初始化记忆存储 - 使用插件目录路径
        data_file = os.path.join(self.plugin_path, "memory_data.json")
        if not os.path.exists(data_file):
            with open(data_file, "w", encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
                
        with open(data_file, "r", encoding='utf-8') as f:
            self.memories = json.load(f)

    @command_group("memory")
    def memory(self):
        """记忆管理指令组"""
        pass

    @memory.command("list")
    async def list_memories(self, event: AstrMessageEvent):
        """列出所有记忆"""
        session_id = event.session_id
        if session_id not in self.memories or not self.memories[session_id]:
            return event.plain_result("当前会话没有保存的记忆。")
            
        memories = self.memories[session_id]
        memory_text = "已保存的记忆:\n"
        for i, memory in enumerate(memories):
            memory_text += f"{i+1}. {memory['content']} (重要程度:{memory['importance']}, 时间:{memory['timestamp']})\n"
        return event.plain_result(memory_text)

    @memory.command("clear")
    async def clear_memories(self, event: AstrMessageEvent):
        """清空当前会话的所有记忆"""
        session_id = event.session_id
        if session_id in self.memories:
            del self.memories[session_id]
            await self._save_memories()
            return event.plain_result("已清空所有记忆。")
        return event.plain_result("当前会话没有保存的记忆。")

    @memory.command("remove")
    async def remove_memory(self, event: AstrMessageEvent, index: int):
        """删除指定序号的记忆"""
        session_id = event.session_id
        if session_id not in self.memories:
            return event.plain_result("当前会话没有保存的记忆。")
            
        memories = self.memories[session_id]
        index = index - 1  # 用户输入1-based，转换为0-based
        if index < 0 or index >= len(memories):
            return event.plain_result("无效的记忆序号。")
            
        removed = memories.pop(index)
        await self._save_memories()
        return event.plain_result(f"已删除记忆: {removed['content']}")

    @command("mem_help")
    async def memory_help(self, event: AstrMessageEvent):
        """显示记忆插件帮助信息"""
        help_text = """记忆插件使用帮助：
        
1. 记忆管理指令：
   /memory list - 列出所有已保存的记忆
   /memory clear - 清空当前会话的所有记忆
   /memory remove <序号> - 删除指定序号的记忆
   /mem_help - 显示此帮助信息

2. 记忆特性：
   - 每个会话最多保存{max_memories}条记忆
   - 记忆按重要程度(1-5)排序
   - 记忆数量超限时会自动删除最不重要的记忆
   - AI会自动保存它认为重要的信息
   - AI在对话时会参考历史记忆
        """.format(max_memories=self.max_memories)
        
        return event.plain_result(help_text)

    async def _save_memories(self):
        """保存记忆到文件"""
        data_file = os.path.join(self.plugin_path, "memory_data.json")
        with open(data_file, "w", encoding='utf-8') as f:
            json.dump(self.memories, f, ensure_ascii=False, indent=2)

    @llm_tool(name="save_memory")
    async def save_memory(self, event: AstrMessageEvent, content: str, importance: int = 1):
        """保存一条记忆
        
        Args:
            content(string): 要保存的记忆内容
            importance(number): 记忆的重要程度，1-5之间
        """
        session_id = event.session_id
        
        if session_id not in self.memories:
            self.memories[session_id] = []
            
        if len(self.memories[session_id]) >= self.max_memories:
            self.memories[session_id].sort(key=lambda x: x["importance"])
            self.memories[session_id].pop(0)
            
        memory = {
            "content": content,
            "importance": min(max(importance, 1), 5),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.memories[session_id].append(memory)
        await self._save_memories()
        return f"我记住了: {content}"

    @llm_tool(name="get_memories")
    async def get_memories(self, event: AstrMessageEvent) -> str:
        """获取当前会话的所有记忆"""
        session_id = event.session_id
        if session_id not in self.memories:
            return "我没有任何相关记忆。"
            
        memories = self.memories[session_id]
        if not memories:
            return "我没有任何相关记忆。"
            
        memory_text = "💭 相关记忆：\n"
        sorted_memories = sorted(memories, key=lambda x: x["importance"], reverse=True)
        for memory in sorted_memories:
            memory_text += f"- {memory['content']}\n"
        return memory_text
