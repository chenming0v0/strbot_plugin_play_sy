from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register    
from astrbot.api.event.filter import command, command_group
from astrbot.api import llm_tool
import os
import logging

from .memory_manager import MemoryManager
from .config_manager import ConfigManager

logger = logging.getLogger("astrbot")

@register("ai_memory", "chenming0v0", "一个AI记忆管理插件", "2.0.0")
class Main(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.PLUGIN_NAME = "strbot_plugin_play_sy"
        
        # 使用data目录下的数据文件，而非插件自身目录
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
        # 确保目录存在
        os.makedirs(os.path.join(data_dir, "memories"), exist_ok=True)
        self.data_file = os.path.join(data_dir, "memories", "memory_data.json")
        
        # 初始化配置管理器
        default_config = {
            "max_memories": config.get("max_memories", 100),
            "auto_save_enabled": config.get("auto_save_enabled", True),
            "importance_threshold": config.get("importance_threshold", 3),
            "memory_expire_days": config.get("memory_expire_days", 30),
            "enable_memory_management": config.get("enable_memory_management", True)
        }
        self.config_manager = ConfigManager(default_config)
        
        # 初始化记忆管理器
        self.memory_manager = MemoryManager(self.data_file, self.config_manager.get_config())
        
        logger.info("AI记忆管理插件初始化完成")

    def _get_session_id(self, event: AstrMessageEvent) -> str:
        """获取统一的会话ID"""
        if hasattr(event, 'unified_msg_origin'):
            return event.unified_msg_origin
        return str(event.session_id)

    @command_group("memory")
    def memory(self):
        """记忆管理指令组"""
        pass

    @memory.command("list")
    async def list_memories(self, event: AstrMessageEvent):
        """列出所有记忆"""
        session_id = self._get_session_id(event)
        memories = self.memory_manager.get_memories_sorted(session_id)
        
        if not memories:
            return event.plain_result("当前会话没有保存的记忆。")
        
        memory_text = "📝 已保存的记忆:\n"
        for i, memory in enumerate(memories):
            importance_stars = "⭐" * memory["importance"]
            memory_text += f"{i+1}. {memory['content']}\n"
            memory_text += f"   重要程度: {importance_stars} ({memory['importance']}/5)\n"
            memory_text += f"   时间: {memory['timestamp']}\n\n"
        
        return event.plain_result(memory_text)

    @memory.command("search")
    async def search_memories(self, event: AstrMessageEvent, keyword: str):
        """搜索记忆"""
        session_id = self._get_session_id(event)
        memories = self.memory_manager.search_memories(session_id, keyword)
        
        if not memories:
            return event.plain_result(f"没有找到包含 '{keyword}' 的记忆。")
        
        memory_text = f"🔍 搜索结果 (关键词: {keyword}):\n"
        for i, memory in enumerate(memories):
            importance_stars = "⭐" * memory["importance"]
            memory_text += f"{i+1}. {memory['content']}\n"
            memory_text += f"   重要程度: {importance_stars} ({memory['importance']}/5)\n"
            memory_text += f"   时间: {memory['timestamp']}\n\n"
        
        return event.plain_result(memory_text)

    @memory.command("stats")
    async def memory_stats(self, event: AstrMessageEvent):
        """显示记忆统计信息"""
        session_id = self._get_session_id(event)
        stats = self.memory_manager.get_memory_stats(session_id)
        
        if stats["total"] == 0:
            return event.plain_result("当前会话没有保存的记忆。")
        
        stats_text = "📊 记忆统计信息:\n"
        stats_text += f"总记忆数: {stats['total']}\n"
        stats_text += f"平均重要性: {stats['avg_importance']}/5\n"
        stats_text += "重要性分布:\n"
        
        for importance, count in stats["importance_distribution"].items():
            if count > 0:
                stars = "⭐" * importance
                stats_text += f"  {stars} ({importance}级): {count}条\n"
        
        return event.plain_result(stats_text)

    @memory.command("add")
    async def add_memory(self, event: AstrMessageEvent, content: str, importance: int = 3, tags: str = None):
        """手动添加一条记忆，支持自定义标签"""
        session_id = self._get_session_id(event)
        
        if not content.strip():
            return event.plain_result("❌ 记忆内容不能为空。")
        
        if importance < 1 or importance > 5:
            return event.plain_result("❌ 重要性必须在1-5之间。")
        
        # 处理自定义标签
        custom_tags = None
        if tags:
            custom_tags = [tag.strip() for tag in tags.split(',')]
        
        if self.memory_manager.add_memory(session_id, content.strip(), importance, custom_tags):
            await self.memory_manager.save_memories()
            importance_stars = "⭐" * importance
            tag_info = f"\n标签: {', '.join(custom_tags)}" if custom_tags else ""
            return event.plain_result(f"✅ 已添加记忆: {content}\n重要程度: {importance_stars} ({importance}/5){tag_info}")
        else:
            return event.plain_result("❌ 记忆管理功能已禁用，无法添加记忆。")

    @memory.command("edit")
    async def edit_memory(self, event: AstrMessageEvent, index: int, content: str):
        """编辑指定序号的记忆内容"""
        session_id = self._get_session_id(event)
        index = index - 1  # 用户输入1-based，转换为0-based
        
        if not content.strip():
            return event.plain_result("❌ 记忆内容不能为空。")
        
        memories = self.memory_manager.get_memories(session_id)
        if index < 0 or index >= len(memories):
            return event.plain_result("❌ 无效的记忆序号。")
        
        old_content = memories[index]["content"]
        memories[index]["content"] = content.strip()
        await self.memory_manager.save_memories()
        
        return event.plain_result(f"✅ 已编辑记忆:\n原内容: {old_content}\n新内容: {content}")

    @memory.command("clear")
    async def clear_memories(self, event: AstrMessageEvent):
        """清空当前会话的所有记忆"""
        session_id = self._get_session_id(event)
        if self.memory_manager.clear_memories(session_id):
            await self.memory_manager.save_memories()
            return event.plain_result("✅ 已清空所有记忆。")
        return event.plain_result("当前会话没有保存的记忆。")

    @memory.command("remove")
    async def remove_memory(self, event: AstrMessageEvent, index: int):
        """删除指定序号的记忆"""
        session_id = self._get_session_id(event)
        index = index - 1  # 用户输入1-based，转换为0-based
        
        removed = self.memory_manager.remove_memory(session_id, index)
        if removed:
            await self.memory_manager.save_memories()
            return event.plain_result(f"✅ 已删除记忆: {removed['content']}")
        return event.plain_result("❌ 无效的记忆序号。")

    @memory.command("update")
    async def update_memory_importance(self, event: AstrMessageEvent, index: int, importance: int):
        """更新记忆的重要性"""
        session_id = self._get_session_id(event)
        index = index - 1  # 用户输入1-based，转换为0-based
        
        if importance < 1 or importance > 5:
            return event.plain_result("❌ 重要性必须在1-5之间。")
        
        if self.memory_manager.update_memory_importance(session_id, index, importance):
            await self.memory_manager.save_memories()
            return event.plain_result(f"✅ 已更新记忆重要性为 {importance}。")
        return event.plain_result("❌ 无效的记忆序号。")

    @command("memory_config")
    async def show_config(self, event: AstrMessageEvent):
        """显示当前配置"""
        summary = self.config_manager.get_config_summary()
        return event.plain_result(summary)

    @command("memory_reset_config")
    async def reset_config(self, event: AstrMessageEvent):
        """重置配置为默认值"""
        self.config_manager.reset_to_default()
        # 更新记忆管理器的配置
        self.memory_manager.config = self.config_manager.get_config()
        return event.plain_result("✅ 配置已重置为默认值")

    @command("mem_help")
    async def memory_help(self, event: AstrMessageEvent):
        """显示记忆插件帮助信息"""
        help_text = """🧠 记忆插件使用帮助：

📋 记忆管理指令：

🔍 查看记忆：
   /memory list - 列出所有已保存的记忆
   /memory search <关键词> - 搜索包含关键词的记忆
   /memory stats - 显示记忆统计信息

✏️ 添加/编辑记忆：
   /memory add <内容> [重要性] - 手动添加记忆(重要性默认3，范围1-5)
   示例: /memory add 我喜欢吃苹果 4
   示例: /memory add 明天要开会
   
   /memory edit <序号> <新内容> - 编辑指定序号的记忆内容
   示例: /memory edit 1 我喜欢吃红苹果

🗑️ 删除记忆：
   /memory remove <序号> - 删除指定序号的记忆
   示例: /memory remove 1
   
   /memory clear - 清空当前会话的所有记忆

⚙️ 调整记忆：
   /memory update <序号> <重要性> - 更新记忆的重要性(1-5)
   示例: /memory update 1 5

📊 配置管理：
   /memory_config - 显示当前配置
   /memory_reset_config - 重置配置为默认值

❓ 帮助信息：
   /mem_help - 显示此帮助信息

⚙️ 记忆特性：
   - 每个会话最多保存记忆数量可在管理面板配置
   - 记忆按重要程度(1-5)排序，⭐表示重要性
   - 记忆数量超限时会自动删除最不重要的记忆
   - AI会自动保存它认为重要的信息
   - AI在对话时会参考历史记忆
   - 支持记忆过期自动清理
   - 支持记忆重要性手动调整

💡 使用建议：
   - 使用 /memory add 手动添加重要信息
   - 定期使用 /memory stats 查看记忆使用情况
   - 使用 /memory search 快速找到相关记忆
   - 通过 /memory update 调整记忆重要性
   - 定期清理不重要的记忆
        """
        
        return event.plain_result(help_text)

    @llm_tool(name="save_memory")
    async def save_memory(self, event: AstrMessageEvent, content: str, importance: int = 1, tags: str = None):
        """保存一条记忆
        
        Args:
            content(string): 要保存的记忆内容
            importance(number): 记忆的重要程度，1-5之间
            tags(string): 可选的自定义标签，多个标签用逗号分隔，如"人物:辰林,事件:战斗"
        """
        # 检查自动保存是否启用
        if not self.memory_manager.config.get("auto_save_enabled", True):
            return "自动保存记忆功能已禁用"
        
        # 检查重要性阈值
        threshold = self.memory_manager.config.get("importance_threshold", 3)
        if importance < threshold:
            return f"记忆重要性({importance})低于阈值({threshold})，未保存"
        
        session_id = self._get_session_id(event)
        
        # 处理自定义标签
        custom_tags = None
        if tags:
            custom_tags = [tag.strip() for tag in tags.split(',')]
        
        if self.memory_manager.add_memory(session_id, content, importance, custom_tags):
            await self.memory_manager.save_memories()
            tag_info = f" 标签: {', '.join(custom_tags)}" if custom_tags else ""
            logger.info(f"[save_memory] 保存记忆成功 - 会话: {session_id}, 重要性: {importance}, 内容: {content[:50]}...")
            if custom_tags:
                logger.debug(f"[save_memory] 标签: {', '.join(custom_tags)}")
            return f"✅ 我记住了: {content} (重要性: {importance}/5){tag_info}"
        else:
            logger.warning(f"[save_memory] 记忆保存失败 - 记忆管理功能已禁用")
            return "❌ 记忆管理功能已禁用，无法保存记忆"

    @llm_tool(name="get_memories")
    async def get_memories(self, event: AstrMessageEvent, limit: int = 0) -> str:
        """获取当前会话的所有记忆
        
        Args:
            limit(number): 返回记忆的数量限制，0表示返回所有记忆
        """
        session_id = self._get_session_id(event)
        memories = self.memory_manager.get_memories_sorted(session_id)
        
        # 记录日志
        logger.info(f"[get_memories] 会话ID: {session_id}, 找到 {len(memories)} 条记忆")
        
        if not memories:
            logger.info("[get_memories] 没有找到任何记忆")
            return "我没有任何相关记忆。"
        
        # 如果记忆数量较少，直接返回全部
        if len(memories) <= 10:
            memory_text = f"💭 共有 {len(memories)} 条记忆：\n"
            for i, memory in enumerate(memories):
                importance_stars = "⭐" * memory["importance"]
                # 截断过长的内容，显示前100个字符
                content = memory['content'][:100] + "..." if len(memory['content']) > 100 else memory['content']
                memory_text += f"{i+1}. {content} ({importance_stars})\n"
                # 记录每条记忆到日志
                logger.debug(f"[get_memories] 记忆{i+1}: {memory['content'][:50]}... (重要性:{memory['importance']})")
            logger.info(f"[get_memories] 返回全部 {len(memories)} 条记忆")
            return memory_text
        
        # 记忆较多时，分级显示
        memory_text = f"💭 共有 {len(memories)} 条记忆：\n\n"
        
        # 显示所有5星记忆（不限制数量，全部返回）
        five_star = [m for m in memories if m["importance"] == 5]
        if five_star:
            memory_text += f"【重要记忆 ⭐⭐⭐⭐⭐】({len(five_star)}条)：\n"
            logger.info(f"[get_memories] 找到 {len(five_star)} 条5星记忆，全部返回")
            for i, memory in enumerate(five_star):  # 返回所有5星记忆
                # 完整显示5星记忆内容，不截断
                memory_text += f"{i+1}. {memory['content']}\n"
                # 记录5星记忆到日志
                logger.debug(f"[get_memories] 5星记忆{i+1}: {memory['content'][:100]}...")
            memory_text += "\n"
        
        # 显示部分4星记忆
        four_star = [m for m in memories if m["importance"] == 4]
        if four_star:
            memory_text += f"【次要记忆 ⭐⭐⭐⭐】({len(four_star)}条)：\n"
            for memory in four_star[:5]:
                content = memory['content'][:60] + "..." if len(memory['content']) > 60 else memory['content']
                memory_text += f"• {content}\n"
            if len(four_star) > 5:
                memory_text += f"... 还有 {len(four_star) - 5} 条4星记忆\n"
            memory_text += "\n"
        
        # 统计其他记忆
        other_count = len([m for m in memories if m["importance"] < 4])
        if other_count > 0:
            memory_text += f"【其他记忆】：还有 {other_count} 条3星及以下记忆\n"
        
        if limit > 0 and limit < len(memories):
            memory_text += f"\n(根据限制只显示了部分记忆，使用更大的limit查看更多)"
        
        return memory_text

    @llm_tool(name="search_memories")
    async def search_memories_tool(self, event: AstrMessageEvent, keyword: str, show_all: bool = False) -> str:
        """搜索记忆
        
        Args:
            keyword(string): 搜索关键词，支持多个关键词用空格分隔
            show_all(boolean): 是否显示所有匹配结果，默认False只显示摘要
        """
        session_id = self._get_session_id(event)
        
        # 记录搜索请求
        logger.info(f"[search_memories] 会话ID: {session_id}, 搜索关键词: '{keyword}', show_all: {show_all}")
        
        # 支持多关键词搜索
        keywords = keyword.split()
        all_matches = []
        
        for kw in keywords:
            matches = self.memory_manager.search_memories(session_id, kw)
            logger.debug(f"[search_memories] 关键词 '{kw}' 匹配到 {len(matches)} 条记忆")
            for match in matches:
                # 避免重复添加
                if not any(m['memory_id'] == match.get('memory_id', match['content']) for m in all_matches):
                    all_matches.append(match)
        
        logger.info(f"[search_memories] 总共找到 {len(all_matches)} 条匹配的记忆")
        
        if not all_matches:
            logger.info(f"[search_memories] 没有找到包含 '{keyword}' 的记忆")
            return f"没有找到包含 '{keyword}' 的记忆。"
        
        # 按重要性排序
        all_matches.sort(key=lambda x: x["importance"], reverse=True)
        
        memory_text = f"🔍 搜索 '{keyword}' 找到 {len(all_matches)} 条相关记忆：\n\n"
        
        if show_all or len(all_matches) <= 10:
            # 显示所有结果
            for i, memory in enumerate(all_matches):
                importance_stars = "⭐" * memory["importance"]
                # 高亮匹配的关键词
                content = memory['content']
                for kw in keywords:
                    if kw.lower() in content.lower():
                        # 简单的高亮标记
                        content = content.replace(kw, f"【{kw}】")
                        content = content.replace(kw.lower(), f"【{kw.lower()}】")
                        content = content.replace(kw.upper(), f"【{kw.upper()}】")
                
                # 5星记忆完整显示，其他记忆可以截断
                if memory["importance"] < 5 and len(content) > 150:
                    content = content[:150] + "..."
                
                memory_text += f"{i+1}. {content}\n"
                memory_text += f"   {importance_stars} | {memory['timestamp']}\n\n"
        else:
            # 分组显示
            # 5星记忆 - 全部完整返回，不限制数量
            five_star = [m for m in all_matches if m["importance"] == 5]
            if five_star:
                memory_text += f"【高度相关 ⭐⭐⭐⭐⭐】({len(five_star)}条)：\n"
                logger.info(f"[search_memories] 找到 {len(five_star)} 条5星匹配记忆，全部返回")
                for i, memory in enumerate(five_star):  # 返回所有5星记忆
                    # 5星记忆完整显示内容
                    memory_text += f"{i+1}. {memory['content']}\n"
                    # 记录到日志
                    logger.debug(f"[search_memories] 5星匹配{i+1}: {memory['content'][:100]}...")
                memory_text += "\n"
            
            # 4星记忆
            four_star = [m for m in all_matches if m["importance"] == 4]
            if four_star:
                memory_text += f"【中度相关 ⭐⭐⭐⭐】({len(four_star)}条)：\n"
                for memory in four_star[:5]:
                    content = memory['content'][:80] + "..." if len(memory['content']) > 80 else memory['content']
                    memory_text += f"• {content}\n"
                if len(four_star) > 5:
                    memory_text += f"... 还有 {len(four_star) - 5} 条中度相关记忆\n"
                memory_text += "\n"
            
            # 其他
            other = [m for m in all_matches if m["importance"] < 4]
            if other:
                memory_text += f"【其他相关】：还有 {len(other)} 条相关度较低的记忆\n"
            
            memory_text += "\n💡 提示：使用 show_all=true 参数查看所有详细结果"
        
        return memory_text

    @llm_tool(name="get_memory_stats")
    async def get_memory_stats_tool(self, event: AstrMessageEvent) -> str:
        """获取记忆统计信息"""
        session_id = self._get_session_id(event)
        stats = self.memory_manager.get_memory_stats(session_id)
        
        if stats["total"] == 0:
            return "当前会话没有任何记忆。"
        
        stats_text = f"📊 记忆统计：共 {stats['total']} 条记忆，平均重要性 {stats['avg_importance']}/5"
        
        # 添加重要性分布
        importance_text = []
        for importance, count in stats["importance_distribution"].items():
            if count > 0:
                stars = "⭐" * importance
                importance_text.append(f"{stars}: {count}条")
        
        if importance_text:
            stats_text += f"\n重要性分布: {', '.join(importance_text)}"
        
        return stats_text

    @llm_tool(name="clear_old_memories")
    async def clear_old_memories(self, event: AstrMessageEvent, days: int = 30) -> str:
        """清理指定天数之前的记忆
        
        Args:
            days(number): 清理多少天之前的记忆，默认30天
        """
        session_id = self._get_session_id(event)
        memories = self.memory_manager.get_memories(session_id)
        
        if not memories:
            return "当前会话没有任何记忆。"
        
        import datetime
        current_time = datetime.datetime.now()
        cutoff_time = current_time - datetime.timedelta(days=days)
        
        old_memories = []
        for memory in memories:
            try:
                memory_time = datetime.datetime.strptime(memory["timestamp"], "%Y-%m-%d %H:%M:%S")
                if memory_time < cutoff_time:
                    old_memories.append(memory)
            except:
                continue
        
        if not old_memories:
            return f"没有找到 {days} 天之前的记忆。"
        
        # 从记忆中移除旧的记忆
        memories = [m for m in memories if m not in old_memories]
        self.memory_manager.memories[session_id] = memories
        await self.memory_manager.save_memories()
        
        return f"✅ 已清理 {len(old_memories)} 条 {days} 天之前的记忆。"

    async def on_config_update(self, new_config: dict):
        """配置更新时的回调"""
        # 更新配置管理器
        updated_config = self.config_manager.update_config(new_config)
        
        # 更新记忆管理器的配置
        self.memory_manager.config = updated_config
        
        logger.info(f"记忆插件配置已更新: {updated_config}")

    async def terminate(self):
        """插件卸载时的清理工作"""
        await self.memory_manager.save_memories()
        logger.info("AI记忆管理插件已卸载")
