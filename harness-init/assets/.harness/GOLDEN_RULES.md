# 黄金原则

> 这些规则由项目定制，智能体必须遵守。违反规则的代码不应合并。

## 代码规范

| 规则 | 约束 | 自动检查 |
|------|------|----------|
| 文件大小 | 单文件 ≤ 500 行 | ✅ |
| 函数长度 | 单函数 ≤ 50 行 | ✅ |
| 命名 | 禁止单字母变量（循环除外） | ✅ |
| 注释 | 复杂逻辑必须有注释 | ❌ |

## 架构约束

### 分层调用

```
┌─────────────────────────────────────────┐
│  UI Layer                               │
│    ↓ 只能调用 API Layer                  │
├─────────────────────────────────────────┤
│  API Layer (路由、参数校验)              │
│    ↓ 只能调用 Service Layer              │
├─────────────────────────────────────────┤
│  Service Layer (业务逻辑)               │
│    ↓ 只能调用 Repo Layer                 │
├─────────────────────────────────────────┤
│  Repo Layer (数据访问)                  │
│    ↓ 访问 DB/Cache/External             │
└─────────────────────────────────────────┘
```

**禁止**：
- ❌ API 层直接访问数据库
- ❌ 跨层调用（如 UI → Service）

### 边界验证

- 入参必须校验（使用类型 + 验证器）
- 禁止 YOLO 式探测数据（`data["maybe_exists"]`）
- 外部调用必须有超时（默认 30s）

### 错误处理

- 所有异常必须有明确的错误信息
- 禁止空 `except` 块
- 重试机制：指数退避 + 最大重试次数

## 命名约定

### API 路由

```
GET    /api/v1/{resource}       # 列表
GET    /api/v1/{resource}/{id}  # 详情
POST   /api/v1/{resource}       # 创建
PUT    /api/v1/{resource}/{id}  # 更新
DELETE /api/v1/{resource}/{id}  # 删除
```

### 文件命名

```
{entity}_service.py   # Service 层
{entity}_repo.py      # Repo 层
{entity}_api.py       # API 层
```

### 函数命名

```
get_{entity}()        # 查询单个
list_{entities}()     # 查询列表
create_{entity}()     # 创建
update_{entity}()     # 更新
delete_{entity}()     # 删除
```

### 类型命名

```
{Entity}Request       # 请求类型
{Entity}Response      # 响应类型
{Entity}Entity        # 数据库实体
```

## 禁止模式

| 模式 | 问题 | 替代方案 |
|------|------|----------|
| `except: pass` | 吞掉所有异常 | 明确捕获具体异常 |
| `SELECT *` | 查询不必要字段 | 明确指定字段 |
| 硬编码密钥 | 安全风险 | 使用环境变量 |
| `data["key"]` | 可能 KeyError | `data.get("key", default)` |
| 嵌套回调 >3层 | 可读性差 | async/await |
| 魔法数字 | 语义不明 | 提取为常量 |

## 测试规范

- 新功能必须有单元测试
- API 必须有集成测试
- 测试覆盖率目标：80%

## Git 提交规范

```
feat: 添加用户登录功能 (auth模块)
fix: 修复登录页面 token 过期报错
refactor: 重构认证服务
docs: 更新 API 文档
test: 添加登录测试用例
```

---

## 项目自定义规则

> 在此添加项目特定的规则

<!-- 示例：
### 本项目特殊约束

- 所有 API 必须返回 `{ "code": int, "data": any, "message": string }` 格式
- 使用 Redis 做缓存，key 格式：`{module}:{id}:{field}`
-->
