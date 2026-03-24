# BOSS 直聘招聘助手执行报告

**执行时间**: {{timestamp}}
**执行时长**: {{duration}} 分钟
**执行模式**: {{mode}}

---

## 📊 执行摘要

| 指标 | 数量 |
|------|------|
| 处理未读消息 | {{unread_processed}} 条 |
| 新增联系人 | {{new_contacts}} 人 |
| 请求简历 | {{resumes_requested}} 次 |
| 跳过/错误 | {{errors}} 次 |
| 匹配候选人 | {{matched_candidates}} 人 |

---

## 📋 处理详情

### 已处理未读消息

{{#each unread_list}}
- **{{name}}** ({{position}})
  - 时间: {{timestamp}}
  - 回复: {{ai_reply}}
  - 简历: {{#if resume_requested}}✅ 已请求{{else}}❌ 未请求{{/if}}
{{/each}}

{{#unless unread_list}}
*无未读消息*
{{/unless}}

---

### 新联系候选人

{{#each new_contacts_list}}
- **{{name}}** (匹配度: {{match_score}}%)
  - 职位: {{target_position}}
  - 经验: {{experience}} | 学历: {{education}}
  - 标签: {{tags}}
  - 时间: {{timestamp}}
{{/each}}

{{#unless new_contacts_list}}
*未联系新候选人*
{{/unless}}

---

### 处理失败/跳过

{{#each errors_list}}
- **{{name}}** ({{reason}})
  - 详情: {{detail}}
{{/each}}

{{#unless errors_list}}
*无错误*
{{/unless}}

---

## 📈 历史统计

| 指标 | 累计值 |
|------|--------|
| 总会话数 | {{total_sessions}} |
| 总处理候选人 | {{total_candidates}} |
| 总请求简历 | {{total_resumes}} |
| 总新增联系 | {{total_contacts}} |

---

## 💡 建议

{{suggestions}}

---

*报告由 BOSS 直聘招聘助手自动生成*
