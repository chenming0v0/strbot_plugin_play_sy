# AstrBot 记忆插件

一个为 AstrBot 提供记忆功能的插件，让 AI 能够记住对话中的重要信息。

## 功能特性

- 每个会话单独保存记忆
- 记忆按重要程度（1-5）排序
- 自动管理记忆容量，超出时会删除最不重要的记忆
- AI 可以在对话时自动添加和使用历史记忆
- 支持手动管理记忆（删除、查看、清空）
- 本插件功能简陋，仅供娱乐，建议使用隔壁的长期记忆插件

## 使用方法

### 安装
1. 将插件文件夹放入 `data/plugins/` 目录
2. 重启 AstrBot

### 配置

在AstrBot管理面板的插件管理中可以配置以下参数：

#### 基本配置
- **max_memories**
  - 每个会话最大记忆数量
  - 默认值: 10

- **auto_save_enabled** 
  - 是否启用AI自动保存记忆
  - 默认值: true

- **importance_threshold**
  - AI自动保存的重要性阈值
  - 默认值: 3

#### 高级配置
- **memory_expire_days**
  - 记忆过期天数，0表示永不过期
  - 默认值: 30

- **enable_memory_management**
  - 是否启用记忆管理功能
  - 默认值: true

### 命令列表

#### 查看记忆
- `/memory list` - 列出当前会话的所有记忆
- `/memory search <关键词>` - 搜索包含关键词的记忆
- `/memory stats` - 显示记忆统计信息

#### 添加/编辑记忆
- `/memory add <内容> [重要性]` - 手动添加记忆(重要性默认3，范围1-5)
- `/memory edit <序号> <新内容>` - 编辑指定序号的记忆内容

#### 删除记忆
- `/memory remove <序号>` - 删除指定序号的记忆
- `/memory clear` - 清空当前会话的所有记忆

#### 调整记忆
- `/memory update <序号> <重要性>` - 更新记忆的重要性(1-5)

#### 配置管理
- `/memory_config` - 显示当前配置
- `/memory_reset_config` - 重置配置为默认值

#### 帮助信息
- `/mem_help` - 显示详细帮助信息
  
### 使用演示

![演示](image/示例.png)
![后台](image/后台调用.png)
  
## 作者

- 作者：kjqwdw
- 版本：v1.0.0

## 支持

如需帮助，请参考 [AstrBot插件开发文档](https://astrbot.soulter.top/center/docs/%E5%BC%80%E5%8F%91/%E6%8F%92%E4%BB%B6%E5%BC%80%E5%8F%91/)
