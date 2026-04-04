---
name: deploy-pipeline
description: "阿里云云效流水线部署工具。触发词：'部署上线'、'触发流水线'、'运行pipeline'、'发布到生产'、'执行部署'、'查看部署状态'. 用于自动化触发云效 Flow 流水线，支持多流水线选择、批量执行、状态查询."
argument-hint: "[流水线名称或ID]"
allowed-tools: Read, Grep, Glob, Bash
---

# 云效流水线部署 Skill

自动化触发阿里云云效 Flow 流水线，支持配置管理、流水线选择、批量执行和状态查询。

## 工作流程

### 1. 检查配置

执行任何操作前，先检查以下配置文件：

- **`~/.yunxiaorc`** - 存放个人访问令牌（必需）
- **`.pipeline.json`** - 存放流水线配置（可选，首次使用会自动创建）

配置文件格式：

**`~/.yunxiaorc`**（放在用户主目录）：
```json
{
  "token": "pt-xxxxxxxx",
  "domain": "openapi-rdc.aliyuncs.com"
}
```

**`.pipeline.json`**（放在项目根目录）：
```json
{
  "organizationId": "6475aec3c3226d3f2e4e0f30",
  "pipelines": [
    {
      "pipelineId": "123",
      "pipelineName": "生产环境部署"
    }
  ]
}
```

### 2. 执行逻辑

1. **检查 Token 配置**：读取 `~/.yunxiaorc`，如果不存在提示用户创建
2. **检查流水线配置**：读取当前项目的 `.pipeline.json`
3. **如果流水线配置不存在**：
   - 调用 API 获取可用流水线列表
   - 展示给用户选择要关联的流水线
   - 保存到 `.pipeline.json`
4. **如果配置已存在**：
   - 询问用户要运行哪些流水线
   - 调用运行流水线 API
   - 自动查询运行状态并返回结果

### 3. 脚本调用

**重要**：使用 skill 目录下的脚本，不要在项目中生成任何代码文件。

脚本路径： `~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py`

```bash
# 获取流水线列表
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py list

# 运行流水线
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py run <pipelineId>

# 查看流水线历史运行记录
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py status <pipelineId>

# 查看最近一次运行状态（推荐）
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py latest <pipelineId>

# 保存流水线到配置
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py save <pipelineId>
```

### 4. 状态说明

| 状态 | 说明 |
|------|------|
| SUCCESS | ✅ 运行成功 |
| FAIL | ❌ 运行失败 |
| RUNNING | 🔄 运行中 |
| WAITING | ⏳ 等待中 |
| CANCELED | ⚪ 已取消 |

## 使用示例

用户说：
- "部署上线" → 展示流水线列表，选择后执行
- "触发流水线" → 展示已配置的流水线供选择
- "运行生产环境部署" → 直接运行匹配名称的流水线
- "查看部署状态" → 查询最近一次运行状态
- "发布到生产" → 执行部署

响应流程：
1. 检查配置文件
2. 展示可用/已配置流水线
3. 确认要执行的流水线
4. 调用 API 执行
5. **自动查询运行状态**
6. 返回执行结果、状态和详情链接

## 输出格式

**触发成功**：
```
🚀 正在触发流水线 123...
✅ 流水线 123 触发成功
   运行 ID: 456
   查看详情: https://flow.aliyun.com/pipelines/123/builds/456
```

**查询状态**：
```
✅ 流水线 123 最新运行状态:
  运行 ID: 456
  状态: SUCCESS
  触发方式: 人工触发
  触发时间: 2024-04-04 12:00:00

  📋 阶段详情:
     ✅ 构建: SUCCESS
     ✅ 部署: SUCCESS

  🔗 查看详情: https://flow.aliyun.com/pipelines/123/builds/456
```

## 注意事项

1. **不要在项目中生成代码文件**，所有脚本都在 skill 目录下
2. Token 需要有流水线读写权限
3. `.yunxiaorc` 文件必须放在用户主目录并设置 600 权限
4. `.pipeline.json` 是唯一允许在项目中创建的配置文件（可选）
5. 如果用户只说"部署"但没有指定流水线，展示所有可用流水线让用户选择
6. **运行流水线后自动查询状态**，让用户知道执行结果

## 错误处理

- Token 无效：提示用户检查 `~/.yunxiaorc` 中的 token
- 流水线不存在：提示用户重新获取流水线列表
- 网络错误：检查服务域名是否正确
- 权限不足：提示用户检查 Token 权限设置
