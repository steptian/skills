# Deploy Pipeline Skill

阿里云云效 Flow 流水线部署工具，用于 Claude Code 自动化触发和管理 CI/CD 流水线。

## 功能特性

- 🚀 **一键部署** - 通过自然语言触发流水线执行
- 📋 **流水线管理** - 列出、选择、保存流水线配置
- 📊 **状态查询** - 查看运行状态和阶段详情
- 🔄 **多流水线支持** - 批量执行多个流水线
- 💾 **配置持久化** - 项目级流水线配置保存

## 安装

### 方式一： 符号链接（推荐）

```bash
# 克隆仓库
git clone https://github.com/your-repo/skills.git
cd skills

# 创建符号链接到个人 skills 目录
ln -sf $(pwd)/deploy-pipeline ~/.claude/skills/deploy-pipeline
```

### 方式二： 直接复制

```bash
mkdir -p ~/.claude/skills
cp -r deploy-pipeline ~/.claude/skills/
```

## 配置

### 1. 创建云效 Token

1. 登录 [云效控制台](https://flow.aliyun.com)
2. 点击右上角头像 → 个人设置 → 个人访问令牌
3. 创建令牌，勾选 **流水线** 的 **读写** 权限
4. 复制生成的 Token

### 2. 保存 Token 配置

```bash
cat > ~/.yunxiaorc << 'EOF'
{
  "token": "pt-your-token-here",
  "domain": "openapi-rdc.aliyuncs.com"
}
EOF

chmod 600 ~/.yunxiaorc
```

| 参数 | 说明 | 示例 |
|------|------|------|
| token | 个人访问令牌 | `pt-xxxx` |
| domain | 服务接入点 | `openapi-rdc.aliyuncs.com`（中心版） |

## 使用方法

### 在 Claude Code 中使用

直接用自然语言触发：

```
"部署上线"
"触发流水线"
"发布到生产"
"查看部署状态"
```

### 命令行使用

```bash
# 查看脚本帮助
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py --help

# 获取流水线列表
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py list

# 运行流水线
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py run 123

# 查看最近运行状态
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py latest 123

# 查看历史运行记录
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py status 123

# 保存流水线到项目配置
python3 ~/.claude/skills/deploy-pipeline/scripts/pipeline_api.py save 123
```

### 选项

| 选项 | 说明 |
|------|------|
| `--json` | JSON 格式输出 |
| `--non-interactive` | 非交互模式 |

## 输出示例

### 触发流水线

```
🚀 正在触发流水线 4781947...
✅ 流水线 4781947 触发成功
   运行 ID: 14
   查看详情: https://flow.aliyun.com/pipelines/4781947/builds/14
```

### 查询状态

```
✅ 流水线 4781947 最新运行状态:

  运行 ID: 13
  状态: SUCCESS
  触发方式: 人工触发
  触发时间: 2026-04-02 16:17:48

  📋 阶段详情:
     ✅ 测试: SUCCESS
     ✅ 构建: SUCCESS
     ✅ 部署: SUCCESS

  🔗 查看详情: https://flow.aliyun.com/pipelines/4781947/builds/13
```

## 项目配置文件

在项目根目录创建 `.pipeline.json` 可保存流水线关联：

```json
{
  "organizationId": "your-org-id",
  "pipelines": [
    {
      "pipelineId": "123",
      "pipelineName": "生产环境部署"
    },
    {
      "pipelineId": "456",
      "pipelineName": "测试环境部署"
    }
  ]
}
```

## 状态说明

| 状态 | 图标 | 说明 |
|------|------|------|
| SUCCESS | ✅ | 运行成功 |
| FAIL | ❌ | 运行失败 |
| RUNNING | 🔄 | 运行中 |
| WAITING | ⏳ | 等待中 |
| CANCELED | ⚪ | 已取消 |

## 目录结构

```
deploy-pipeline/
├── SKILL.md                 # Claude Code Skill 定义
├── README.md                # 使用说明
└── scripts/
    └── pipeline_api.py       # API 调用脚本
```

## 常见问题

### Token 无效

检查 `~/.yunxiaorc` 中的 token 是否正确，确保有流水线读写权限。

### 流水线不存在

运行 `list` 命令重新获取可用流水线列表。

### 网络错误

检查服务域名是否正确：
- 中心版： `openapi-rdc.aliyuncs.com`
- Region 版： 参考[服务接入点](https://help.aliyun.com/zh/yunxiao/developer-reference/service-access-point-domain)

## 相关链接

- [云效 Flow 文档](https://help.aliyun.com/zh/yunxiao)
- [OpenAPI 文档](https://help.aliyun.com/zh/yunxiao/developer-reference/api-list)
- [获取个人访问令牌](https://help.aliyun.com/zh/yunxiao/developer-reference/obtain-personal-access-token)

## License

MIT
