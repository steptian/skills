# BOSS 直聘招聘助手 Skill

这是一个帮助你在 BOSS 直聘平台上自动化招聘流程的 Claude Code skill。

## 功能特性

- ✅ 自动处理未读消息
- 🤖 AI 智能回复候选人
- 📄 自动请求候选人简历
- 🔍 智能筛选推荐候选人
- 📊 生成执行报告
- 📝 历史记录追踪

## 安装方法

```bash
# 符号链接到个人 skills 目录
ln -s $(pwd)/boss-recruiter ~/.claude/skills/boss-recruiter
```

## 使用方法

### 触发词

- "处理招聘"
- "BOSS直聘" / "boss 直聘"
- "找候选人" / "筛选候选人"
- "招聘自动化"
- "处理未读消息"
- "批量联系候选人"

### 使用前准备

1. 在浏览器中登录 BOSS 直聘
2. 保持登录状态（skill 将使用已登录的浏览器会话）

### 执行模式

触发后可以选择：
- **完整模式**：处理未读 + 推荐牛人
- **仅未读**：只处理未读消息
- **仅推荐**：只联系新候选人

## 目录结构

```
boss-recruiter/
├── SKILL.md           # 主指令文件
├── README.md          # 说明文档
├── reference.md       # 参考文档（页面结构、数据结构、算法）
├── template.md        # 报告模板
├── evals/             # 测试用例
│   └── evals.json
└── scripts/           # 辅助脚本
    └── init_history.py
```

## 配置选项

### 历史记录位置

```
~/.claude/projects/-Users-steptian-Documents-iLike-Python-feilian-skills/memory/boss-recruiter/history.json
```

### 候选人数量限制

默认软限制：60 个候选人/天

可在 skill 中调整此参数。

## 开发说明

### 依赖

- `web-access` skill（提供浏览器自动化能力）

### 扩展

要添加新的消息模板或修改筛选逻辑，编辑 `reference.md` 中的相关部分。

## 注意事项

1. 本 skill 仅用于合法的招聘活动
2. 请遵守 BOSS 直聘平台的使用规则
3. 建议定期检查自动回复的质量
4. 重要决策建议人工确认

## 许可

本 skill 仅供个人使用。
