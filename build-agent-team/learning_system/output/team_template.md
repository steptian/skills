# Agent Team 模板: 全栈功能开发模板

> 模板ID: `template_fullstack-project-team_20260215_093839`
> 创建时间: 2026-02-15 09:38:39
> 来源团队: fullstack-project-team

## 基本信息

- **适用场景**: 功能开发
- **建议规模**: 4 人
- **标签**: 全栈, 前后端分离, 测试驱动

## 角色定义

### 角色1: 前端工程师

**职责**: 前端工程师 角色，负责 src/frontend/, src/components/

**文件所有权**:

- `src/frontend/` (排他)
- `src/components/` (排他)

**典型任务**:

- 实现用户登录界面
- 实现用户注册表单

**质量要求**:

- [ ] test_coverage
- [ ] lint_check

### 角色2: 后端工程师

**职责**: 后端工程师 角色，负责 src/backend/, src/api/

**文件所有权**:

- `src/backend/` (排他)
- `src/api/` (排他)

**典型任务**:

- 实现登录API接口
- 实现用户注册API
- 配置JWT认证

**质量要求**:

- [ ] test_coverage
- [ ] security_scan
- [ ] security_review

### 角色3: 数据库工程师

**职责**: 数据库工程师 角色，负责 src/database/, migrations/

**文件所有权**:

- `src/database/` (排他)
- `migrations/` (排他)

**典型任务**:

- 设计用户表结构
- 创建数据库迁移脚本

**质量要求**:

- [ ] schema_review
- [ ] migration_test

### 角色4: 测试工程师

**职责**: 测试工程师 角色，负责 tests/, test-fixtures/

**文件所有权**:

- `tests/` (排他)
- `test-fixtures/` (排他)

**典型任务**:

- 编写登录流程集成测试
- 编写注册流程集成测试

**质量要求**:

- [ ] integration_test

## 文件所有权映射

| 目录 | 负责角色 |
|------|---------|
| `src/frontend/` | 前端工程师 |
| `src/components/` | 前端工程师 |
| `src/backend/` | 后端工程师 |
| `src/api/` | 后端工程师 |
| `src/database/` | 数据库工程师 |
| `migrations/` | 数据库工程师 |
| `tests/` | 测试工程师 |
| `test-fixtures/` | 测试工程师 |

## 共享文件处理模式

- `src/shared/types.ts`
- `src/config.py`

## 成功指标（来源项目）

| 指标 | 数值 |
|------|------|
| total_tasks | 9 |
| completed_tasks | 9 |
| blocked_tasks | 0 |
| completion_rate | 1.00 |
| blocked_ratio | 0.00 |
| average_quality_pass_rate | 0.94 |
| average_task_duration | 0.00 |
| total_duration_seconds | 0.00 |
| total_conflicts | 1 |

## 使用说明

```
/build-agent-team 使用模板 全栈功能开发模板
```
