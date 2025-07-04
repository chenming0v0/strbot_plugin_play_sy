import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("astrbot")

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, default_config: Dict[str, Any]):
        self.default_config = default_config
        self.current_config = default_config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置"""
        # 验证配置
        validated_config = self._validate_config(new_config)
        
        # 更新当前配置
        self.current_config.update(validated_config)
        
        logger.info(f"记忆插件配置已更新: {validated_config}")
        return self.current_config
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置"""
        validated = {}
        
        # 验证最大记忆数
        if "max_memories" in config:
            max_memories = config["max_memories"]
            if isinstance(max_memories, int) and 1 <= max_memories <= 100:
                validated["max_memories"] = max_memories
            else:
                logger.warning(f"无效的max_memories值: {max_memories}，使用默认值")
                validated["max_memories"] = self.default_config["max_memories"]
        
        # 验证自动保存开关
        if "auto_save_enabled" in config:
            auto_save = config["auto_save_enabled"]
            if isinstance(auto_save, bool):
                validated["auto_save_enabled"] = auto_save
            else:
                logger.warning(f"无效的auto_save_enabled值: {auto_save}，使用默认值")
                validated["auto_save_enabled"] = self.default_config["auto_save_enabled"]
        
        # 验证重要性阈值
        if "importance_threshold" in config:
            threshold = config["importance_threshold"]
            if isinstance(threshold, int) and 1 <= threshold <= 5:
                validated["importance_threshold"] = threshold
            else:
                logger.warning(f"无效的importance_threshold值: {threshold}，使用默认值")
                validated["importance_threshold"] = self.default_config["importance_threshold"]
        
        # 验证记忆过期天数
        if "memory_expire_days" in config:
            expire_days = config["memory_expire_days"]
            if isinstance(expire_days, int) and 0 <= expire_days <= 365:
                validated["memory_expire_days"] = expire_days
            else:
                logger.warning(f"无效的memory_expire_days值: {expire_days}，使用默认值")
                validated["memory_expire_days"] = self.default_config["memory_expire_days"]
        
        # 验证记忆管理开关
        if "enable_memory_management" in config:
            enable = config["enable_memory_management"]
            if isinstance(enable, bool):
                validated["enable_memory_management"] = enable
            else:
                logger.warning(f"无效的enable_memory_management值: {enable}，使用默认值")
                validated["enable_memory_management"] = self.default_config["enable_memory_management"]
        
        return validated
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.current_config.copy()
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取指定配置值"""
        return self.current_config.get(key, default)
    
    def reset_to_default(self) -> Dict[str, Any]:
        """重置为默认配置"""
        self.current_config = self.default_config.copy()
        logger.info("记忆插件配置已重置为默认值")
        return self.current_config
    
    def get_config_summary(self) -> str:
        """获取配置摘要"""
        config = self.current_config
        summary = "📋 当前配置：\n"
        summary += f"• 最大记忆数: {config.get('max_memories', 10)}\n"
        summary += f"• 自动保存: {'启用' if config.get('auto_save_enabled', True) else '禁用'}\n"
        summary += f"• 重要性阈值: {config.get('importance_threshold', 3)}/5\n"
        summary += f"• 过期天数: {config.get('memory_expire_days', 30)}天\n"
        summary += f"• 记忆管理: {'启用' if config.get('enable_memory_management', True) else '禁用'}"
        return summary 