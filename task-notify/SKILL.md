---
name: task-notify
description: "任务完成提醒（语音播报 + 系统通知）。触发词：'提醒我'、'通知我'、'好了叫我'、'完成了告诉我'、'notify'"
argument-hint: "[自定义消息]"
---

## 任务完成通知

发送 macOS 系统通知并语音播报，提醒用户任务已完成。

## 核心规则

**Title 必须从当前对话上下文中提取**，反映正在执行的具体任务：

1. 回顾本次对话中正在执行的任务
2. 提取任务的核心动作 + 对象，生成简洁标题
3. 如果无法确定上下文，使用默认标题「✅ 任务完成」

## 使用方式

```bash
# title 根据上下文动态生成，message 使用参数或默认值
(say "$message" &) && terminal-notifier -title "$title" -message "$message"
```

### 参数说明

| 参数 | 来源 | 示例 |
|------|------|------|
| `$title` | 从上下文推断 | 「✅ 代码审查完成」「✅ 部署完成」 |
| `$message` | `$ARGUMENTS` 或默认值 | 「所有检查已通过」 |

## Title 提取示例

| 上下文 | 生成的 Title |
|--------|-------------|
| 执行代码审查 | ✅ 代码审查完成 |
| 部署到服务器 | ✅ 部署完成 |
| 运行测试套件 | ✅ 测试完成 |
| 构建 Agent Team | ✅ Agent Team 构建完成 |
| 写文档 | ✅ 文档完成 |
| 调试 Bug | ✅ 调试完成 |
| 数据分析 | ✅ 分析完成 |

## Bash 命令模板

```bash
message="${ARGUMENTS:-长任务已完成}"
title="✅ <从上下文提取的任务名>完成"
(say "$message" &) && terminal-notifier -title "$title" -message "$message"
```

> **依赖**：需要 `terminal-notifier`，通过 `brew install terminal-notifier` 安装
