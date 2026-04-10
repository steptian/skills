# Harness 迭代模式设计规范

## 背景问题

当前 harness 模式适合：
- **新项目**：从 requirements.md 生成完整功能清单
- **接手项目**：从现有代码库分析生成功能清单

但在**迭代场景**下存在痛点：
- 需求增量式进来，不是完整清单
- 上下文断裂：每次新需求都要重新理解项目状态
- 缺乏项目记忆：设计决策、改动历史难以追溯

## 核心诉求

1. **轻量输入**：灵活格式的需求文档，不需要严格结构
2. **快速融入**：新需求/Bug 能快速加入现有 harness 流程
3. **项目记忆**：系统对项目有精准的理解和记忆

## 解决方案架构

```
┌─────────────────────────────────────────────────────────────┐
│                    迭代需求处理流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   需求文档 ──► dev.sh add ──► 智能解析 ──► 关联判断        │
│       │            │              │              │          │
│       │            ▼              ▼              ▼          │
│       │      简单：单命令    添加到         去重确认        │
│       │      复杂：交互式   features.json                    │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │                  外部记忆系统                        │  │
│   │  ┌─────────────┐ ┌─────────────┐ ┌───────────────┐  │  │
│   │  │ 代码结构/职责 │ │ 接口/数据流 │ │ 设计决策/原因  │  │  │
│   │  └─────────────┘ └─────────────┘ └───────────────┘  │  │
│   │  ┌─────────────────────────────────────────────────┐│  │
│   │  │              迭代历史/背景                       ││  │
│   │  └─────────────────────────────────────────────────┘│  │
│   │                                                     │  │
│   │  更新：混合模式（简单自动，复杂手动）                  │  │
│   │  使用：对话中自动引用                                 │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 一、命令设计

### 1.1 新增命令：`dev.sh add`

```bash
# 基础用法
.harness/dev.sh add <需求文档路径>

# 示例
.harness/dev.sh add iteration/bugfix-login.md
.harness/dev.sh add iteration/feature-export.md
```

### 1.2 命令行为

根据需求复杂度自动选择模式：

| 复杂度 | 判断条件 | 行为 |
|--------|----------|------|
| 简单 | 单一功能点，描述 < 100 字 | 单命令完成，自动添加 |
| 中等 | 多个功能点，有关联关系 | 展示解析结果，确认后添加 |
| 复杂 | 涉及多个模块，需要澄清 | 交互式引导，逐步确认 |

### 1.3 解析流程

```
输入文档
    │
    ▼
┌─────────────────┐
│ 1. 解析需求内容  │  提取：标题、描述、步骤、验收标准
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 关联已有功能  │  分析是否与现有 Feature 相关
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 去重检测     │  检查是否有相似需求
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
  无重复    有相似
    │         │
    ▼         ▼
 自动添加   展示相似项
            确认合并/新建
         │
         ▼
┌─────────────────┐
│ 4. 优先级判断   │  根据类型、紧急程度自动判断
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 写入 JSON    │  通过 feature_cli.py 添加
└─────────────────┘
```

---

## 二、外部记忆系统设计

### 2.1 存储方案

**推荐方案：Knowledge Graph + Markdown 备份**

```
.harness/
├── memory/
│   ├── project.json        # 项目元信息（技术栈、架构）
│   ├── decisions.md        # 设计决策及原因
│   ├── structure.md        # 代码结构和职责
│   ├── interfaces.md       # 关键接口和数据流
│   └── history/            # 迭代历史
│       ├── 2026-03-01-支付功能上线.md
│       └── 2026-03-10-登录优化.md
```

### 2.2 记忆内容

#### 2.2.1 项目元信息 (project.json)

```json
{
  "name": "项目名称",
  "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"],
  "architecture": {
    "backend": "FastAPI REST API",
    "frontend": "React SPA",
    "database": "PostgreSQL",
    "cache": "Redis"
  },
  "key_directories": {
    "src/api": "API 路由和端点",
    "src/models": "数据模型",
    "src/services": "业务逻辑",
    "frontend/src/components": "React 组件"
  }
}
```

#### 2.2.2 设计决策 (decisions.md)

```markdown
# 设计决策记录

## 2026-03-01 认证方案选择

**背景**: 需要实现用户认证功能

**选项**:
1. Session-based 认证
2. JWT 认证

**决策**: 选择 JWT

**原因**:
- 前后端分离架构，JWT 更适合
- 支持跨域
- 无需服务端存储 session

**影响**:
- token 存储在 Redis，支持主动失效
- 前端需要处理 token 刷新逻辑
```

#### 2.2.3 代码结构 (structure.md)

```markdown
# 代码结构说明

## 后端结构

```
src/
├── api/              # API 路由
│   ├── auth.py       # 认证相关 API
│   └── users.py      # 用户管理 API
├── models/           # 数据模型
│   └── user.py       # 用户模型
├── services/         # 业务逻辑
│   └── auth.py       # 认证服务
└── utils/            # 工具函数
```

## 关键模块职责

| 模块 | 职责 | 关键文件 |
|------|------|----------|
| 认证 | 登录/登出/token 管理 | src/services/auth.py |
| 用户 | 用户 CRUD | src/api/users.py |
```

#### 2.2.4 接口文档 (interfaces.md)

```markdown
# 关键接口说明

## 认证接口

### POST /api/auth/login
- **用途**: 用户登录
- **请求**: `{ "email": string, "password": string }`
- **响应**: `{ "token": string, "user": User }`
- **错误**: 401 邮箱或密码错误

### POST /api/auth/logout
- **用途**: 用户登出（使 token 失效）
- **请求**: Header `Authorization: Bearer <token>`
- **响应**: `{ "success": true }`
```

### 2.3 记忆更新机制

#### 自动更新场景

| 触发事件 | 更新内容 |
|----------|----------|
| 完成 Feature | 迭代历史、接口文档 |
| 新增 API 端点 | 接口文档 |
| 新增目录/模块 | 代码结构 |
| Bug 修复 | 迭代历史 |

#### 手动更新命令

```bash
# 记录设计决策
.harness/dev.sh remember decision "为什么选择 Redis 做 cache" "因为需要支持分布式部署"

# 更新代码结构
.harness/dev.sh remember structure "新增支付模块" "src/services/payment.py"

# 记录接口变更
.harness/dev.sh remember interface "新增支付 API" "POST /api/payment/create"
```

### 2.4 记忆使用方式

#### 对话中自动引用

当用户提问或开发时，系统自动从记忆中检索相关信息：

```
用户: 帮我优化登录体验

系统自动注入上下文:
- [记忆] 当前认证方案: JWT，存储在 Redis
- [记忆] 登录 API: POST /api/auth/login
- [记忆] 相关 Feature: F001 用户认证（已完成）
- [记忆] 上次改动: 2026-03-10 调整了 token 过期时间
```

---

## 三、需求/Bug 统一处理

### 3.1 统一作为 Feature

所有需求（包括 Bug）统一作为 Feature 管理：

```json
{
  "id": "F010",
  "type": "bugfix",  // feature | bugfix | enhancement
  "priority": "high",
  "description": "修复登录页面 token 过期未处理的报错",
  "related_feature": "F001",  // 关联的已有功能
  "severity": "high",  // 仅 bugfix: low | medium | high | critical
  "status": "pending",
  ...
}
```

### 3.2 优先级自动判断

```python
def calculate_priority(feature):
    score = 0

    # 类型权重
    type_weights = {
        "bugfix": 30,
        "feature": 20,
        "enhancement": 10
    }
    score += type_weights.get(feature.type, 10)

    # 严重程度（仅 bugfix）
    severity_weights = {
        "critical": 50,
        "high": 30,
        "medium": 15,
        "low": 5
    }
    if feature.type == "bugfix":
        score += severity_weights.get(feature.severity, 10)

    # 手动标注的优先级
    priority_weights = {
        "high": 20,
        "medium": 10,
        "low": 0
    }
    score += priority_weights.get(feature.priority, 0)

    return score
```

---

## 四、完整工作流

### 4.1 新需求进来

```bash
# 1. 整理需求文档（灵活格式）
cat > iteration/feature-export.md << 'EOF'
# 数据导出功能

用户需要导出自己的数据为 CSV 格式。

要求：
- 支持导出用户列表
- 支持导出订单记录
- 大文件需要异步处理

紧急程度：中等
EOF

# 2. 添加到 harness
.harness/dev.sh add iteration/feature-export.md

# 系统输出：
# ✓ 解析需求：数据导出功能
# ✓ 类型判断：feature
# ✓ 优先级：medium（得分：30）
# ✓ 关联：无
# ✓ 去重：无相似需求
# ✓ 已添加为 F010

# 3. 继续开发
.harness/dev.sh run
```

### 4.2 Bug 修复

```bash
# 1. 记录 Bug
cat > iteration/bugfix-login.md << 'EOF'
# Bug: 登录页面报错

现象：用户登录后，如果 token 过期，页面没有正确处理，显示空白。

复现步骤：
1. 登录系统
2. 等待 token 过期（或手动清除）
3. 刷新页面

期望：应该跳转到登录页并提示「会话已过期」

严重程度：高
EOF

# 2. 添加到 harness
.harness/dev.sh add iteration/bugfix-login.md

# 系统输出：
# ✓ 解析需求：登录页面 token 过期处理
# ✓ 类型判断：bugfix
# ✓ 严重程度：high
# ✓ 优先级：high（得分：80）
# ✓ 关联：F001 用户认证
# ✓ 去重：无相似需求
# ✓ 已添加为 F011

# 3. 开发时自动注入上下文
.harness/dev.sh run
# [自动注入] F001 认证方案使用 JWT，存储在 Redis
# [自动注入] 登录 API: POST /api/auth/login
# [自动注入] 相关代码: src/services/auth.py, frontend/src/pages/Login.tsx
```

### 4.3 持续迭代

```bash
# 查看当前状态
.harness/dev.sh status

# 输出：
# 项目：XX系统
# 待处理：3 个（2 bugfix, 1 feature）
# 进行中：1 个
# 已完成：10 个
#
# 优先级队列：
# 1. F011 [bugfix] 登录页面报错 (优先级: 80)
# 2. F010 [feature] 数据导出 (优先级: 30)
# 3. F009 [enhancement] 优化加载速度 (优先级: 20)

# 继续开发
.harness/dev.sh run
```

---

## 五、实现计划

### Phase 1: 基础命令 ✅ 已完成

- [x] 实现 `dev.sh add` 命令
- [x] 需求文档解析逻辑
- [x] 去重检测
- [x] 关联判断

### Phase 2: 记忆系统 ✅ 已完成

- [x] 创建 memory/ 目录结构
- [x] 实现记忆存储和查询
- [x] 自动更新逻辑
- [x] 手动更新命令 (`dev.sh remember`, `dev.sh memory`)

### Phase 3: 智能注入 ✅ 已完成

- [x] 会话开始时注入相关记忆
- [x] 对话中自动引用记忆（通过 memory export）
- [x] 优先级自动计算

### Phase 4: 优化迭代

- [ ] 交互式引导流程
- [ ] 记忆质量检查
- [ ] 性能优化

---

## 六、配置扩展

### config.json 新增字段

```json
{
  "max_sessions": 10,
  "stale_hours": 24,
  "auto_commit": true,

  "iteration": {
    "enabled": true,
    "docs_path": "iteration/",
    "auto_priority": true,
    "memory_enabled": true,
    "memory_path": ".harness/memory/"
  }
}
```

---

## 七、注意事项

1. **向后兼容**：现有的 `plan`、`migrate`、`run` 流程不受影响
2. **渐进式采用**：可以选择性使用迭代模式，不影响已有项目
3. **记忆维护**：定期检查记忆准确性，及时更新过期信息
4. **文档格式**：支持灵活格式，但建议包含基本的描述和验收标准
