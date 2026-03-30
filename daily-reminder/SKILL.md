---
name: daily-reminder
description: "日程计划与定时提醒。触发词：'今天要做'、'今日计划'、'今日待办'、'提醒我'、'待办事项'、'加个提醒'、'设置提醒'。支持待办管理、定时提醒、多渠道通知。"
argument-hint: "[--add 任务] [--list] [--done ID] [--config]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash(date *), Bash(say *), Bash(terminal-notifier *)
---

# daily-reminder - 日程计划与定时提醒

> 待办管理 + 定时提醒 + 多渠道通知

## 快速开始

```bash
/daily-reminder              # 查看今日待办
/daily-reminder --add "任务"  # 添加待办
/daily-reminder --done 3     # 标记完成
/daily-reminder --config     # 配置提醒
```

## 存储结构

```
~/.daily-reminder/
├── todos.json           # 待办数据
├── config.json          # 用户配置
└── logs/                # 提醒日志
    └── 2026-03-30.log
```

## 待办数据结构

```json
{
  "id": 1,
  "title": "完成报告",
  "priority": "high",
  "status": "pending",
  "deadline": "2026-03-30T18:00:00",
  "reminder_time": "2026-03-30T17:00:00",
  "created_at": "2026-03-30T09:00:00",
  "completed_at": null
}
```

## 优先级

| 级别 | 符号 | 说明 |
|------|------|------|
| high | 🔴 | 紧急重要 |
| medium | 🟡 | 重要不紧急 |
| low | 🟢 | 可延后 |

## 状态

| 状态 | 符号 | 说明 |
|------|------|------|
| pending | ○ | 待办 |
| in_progress | ◐ | 进行中 |
| done | ● | 已完成 |
| deferred | ↻ | 已延期 |

## 功能开发中...

此 Skill 正在开发中，功能将逐步完善。
