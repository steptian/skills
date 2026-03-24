# BOSS 直聘招聘助手参考文档

## ⏰ 上下文管理（重要！）

### 为什么需要上下文管理

长时间运行会消耗大量 token，导致：
1. **性能下降**：响应变慢
2. **成本增加**：token 消耗累积
3. **意外中断**：超出上下文限制

### 解决方案：10分钟检查点

每工作 **10 分钟**，自动保存进度并提示用户重置。

### 检查点工作流

```
┌────────────────────────────────────────────────────────────────┐
│  开始                                                          │
│    ↓                                                           │
│  记录 start_time                                                │
│    ↓                                                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  处理候选人                                                │  │
│  │    ↓                                                      │  │
│  │  检查: elapsed >= 10分钟?                                  │  │
│  │    ↓ 是                     ↓ 否                          │  │
│  │  保存进度到 session.json    继续处理下一个                  │  │
│  │    ↓                                                      │  │
│  │  显示进度摘要                                              │  │
│  │    ↓                                                      │  │
│  │  提示用户说"继续"                                          │  │
│  │    ↓                                                      │  │
│  │  等待用户响应                                              │  │
│  │    ↓                                                      │  │
│  │  用户说"继续"                                              │  │
│  │    ↓                                                      │  │
│  │  清空上下文                                                │  │
│  │    ↓                                                      │  │
│  │  从 session.json 恢复                                      │  │
│  │    ↓                                                      │  │
│  │  重置 start_time                                           │  │
│  │    ↓                                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│    ↓                                                           │
│  完成                                                          │
└────────────────────────────────────────────────────────────────┘
```

### session.json 格式

```json
{
  "session_id": "2025-03-24-14-30-abc12345",
  "start_time": "2025-03-24T14:30:00+08:00",
  "last_checkpoint": "2025-03-24T14:40:00+08:00",
  "elapsed_minutes": 10,
  "phase": "unread",
  "current_target": "chat/index",
  "processed": [
    {
      "name": "胡美英",
      "position": "验光销售员",
      "status": "replied",
      "processed_at": "2025-03-24T14:32:00+08:00"
    },
    {
      "name": "吴女士",
      "position": "电商事业部HRBP",
      "status": "replied+resume",
      "processed_at": "2025-03-24T14:35:00+08:00"
    }
  ],
  "pending": [
    {"name": "拉拉", "position": "验光销售员"},
    {"name": "罗志鑫", "position": "验光销售员"}
  ],
  "stats": {
    "unread_processed": 2,
    "new_contacts": 0,
    "resumes_requested": 1,
    "errors": 0
  }
}
```

### 恢复流程

用户说"继续"后：

1. **读取 session.json**
2. **恢复状态**
   - phase → 当前阶段
   - processed → 已处理（用于报告）
   - pending → 待处理（从这里继续）
   - stats → 统计数据
3. **重置计时器**：`start_time = now()`
4. **继续处理**：从 pending[0] 开始

### 检查点提示格式

```
⏰ 已工作 10 分钟，建议重置上下文以保持性能。

📊 当前进度：
- 当前阶段：处理未读消息
- 已处理：3 位候选人
- 待处理：2 位候选人
- 简历获取：1 份
- 新增联系：0 人

💾 进度已保存到 session.json

请说"继续"来恢复工作，或说"结束"保存并退出。
```

---

## 页面结构说明

### 1. 聊天列表页面
URL: `https://www.zhipin.com/web/chat/index`

**未读筛选按钮**：
- 位置：列表顶部或筛选栏
- 文本：`全部 未读`（点击后切换）
- CSS选择器参考：
  - `.filter-tab` - 筛选标签
  - `[class*="unread"]` - 包含 unread 的类名
  - 包含"未读"文本的可点击元素

**聊天列表项**：
- `.geek-item-wrap` - 聊天项容器
- `.geek-item` - 聊天项
- `.name` 或 `geek-name` - 候选人姓名
- `.position` - 应聘职位
- `.time` 或 `msg-time` - 消息时间
- `.preview` 或 `last-msg` - 最后消息预览

### 2. 聊天详情页面
URL: 动态生成，点击聊天项后跳转

**候选人信息区域**：
- 候选人姓名、年龄、经验、学历
- 在线简历/附件简历按钮
- 工作经历、教育经历

**聊天消息区域**：
- `.message-list` 或 `.chat-history` - 消息列表
- `.message` 或 `.chat-message` - 单条消息
- `.from-candidate` / `.from-me` - 消息发送方

**操作按钮和消息发送流程**：

```
┌─────────────────────────────────────────────────────────────┐
│  发送消息和求简历的完整流程                                    │
├─────────────────────────────────────────────────────────────┤
│  ① 填写回复内容                                              │
│     - 找到输入框: `.boss-chat-editor-input`                   │
│     - 设置 textContent: "回复内容"                            │
│     - 触发 input + change 事件                                │
│                                                              │
│  ② 真实鼠标点击发送按钮（关键！）                              │
│     - ⚠️ 必须使用 CDP clickAt，JavaScript click() 无效！      │
│     - curl -X POST ".../clickAt?target=ID" -d ".submit-content"│
│                                                              │
│  ③ 验证发送成功                                              │
│     - 检查输入框是否清空                                       │
│     - 检查消息是否带 [送达] 状态                               │
│                                                              │
│  ④ 等待后端处理完成                                           │
│     - 等待 2-3 秒                                             │
│                                                              │
│  ⑤ 点击"求简历"按钮                                          │
│     - 检查 disabled 类                                        │
│     - 点击请求简历                                            │
└─────────────────────────────────────────────────────────────┘
```

**⚠️ 关键发现：发送按钮必须用真实鼠标点击！**

| 方式 | 是否有效 | 说明 |
|------|----------|------|
| JavaScript `btn.click()` | ❌ 无效 | 不会触发真正的发送 |
| web-access `clickAt` | ✅ 有效 | 模拟真实鼠标点击（通过 CDP） |

**正确代码示例（使用 web-access skill）：**
```bash
# 填写内容（通过 web-access /eval）
curl -s -X POST "http://localhost:3456/eval?target=ID" -d "
  const input = document.querySelector('.boss-chat-editor-input');
  input.textContent = '您的回复内容';
  input.dispatchEvent(new Event('input', { bubbles: true }));
"

# 真实鼠标点击发送（关键！使用 web-access /clickAt）
curl -s -X POST "http://localhost:3456/clickAt?target=ID" -d ".submit-content"

# 等待后验证
sleep 3
curl -s -X POST "http://localhost:3456/eval?target=ID" -d "
  const pageText = document.body.innerText;
  return {
    inputCleared: document.querySelector('.boss-chat-editor-input').textContent.length < 5,
    hasMessage: pageText.includes('[送达]')
  };
"
```

**发送成功的标志：**
1. 输入框被清空（textContent 长度 < 5）
2. 消息出现在聊天记录中，显示 `[送达]` 状态
3. 时间戳更新（如 `13:18`）

**CSS选择器参考：**
- `.boss-chat-editor-input` - 消息输入框（contenteditable）
- `.submit-content` - 发送按钮
- `.operate-btn` - 操作按钮容器
- `[class*="resume"]` - 求简历相关按钮

### 3. 职位管理页面
URL: `https://www.zhipin.com/web/chat/job/list`

**职位列表**：
- `.job-item` 或 `.job-card` - 职位卡片
- `.job-status` - 职位状态（招聘中/暂停招聘）
- `.job-title` - 职位名称
- `.job-salary` - 薪资范围
- `.job-detail-link` - 职位详情链接

**筛选器**：
- 状态筛选：开放中 / 暂停招聘
- 职位类型筛选

### 4. 推荐牛人页面
URL: `https://www.zhipin.com/web/chat/recommend`

**筛选器**：
- 经验筛选：1年以下 / 1-3年 / 3-5年 / 5-10年 / 10年以上
- 学历筛选：不限 / 大专 / 本科 / 硕士 / 博士
- 薪资筛选：按范围选择
- 其他条件：性别、年龄等

**候选人卡片**：
- `.recommend-item` 或 `.geek-item` - 候选人卡片
- 候选人基本信息：姓名、经验、学历
- 技能标签：`.tag` 或 `.skill-tag`
- `.contact-btn` - "立即沟通" / "打招呼"按钮

## 数据结构

### 本地职位文件格式 (jobs.md)

```markdown
# BOSS 直聘职位信息

更新时间：2025-03-24 14:30:00

## 职位名称

- **职位ID**: 字符串，从页面提取或生成
- **状态**: "开放中" | "暂停招聘"
- **薪资**: "5-7K" 格式
- **工作地点**: "江苏丹阳" 或 "杭州滨江区"
- **经验要求**: "1-3年" | "3-5年" | "不限"
- **学历要求**: "不限" | "大专" | "本科" | "硕士"
- **发布时间**: ISO 8601 格式或中文日期

### 职位描述
从页面提取的完整 JD

### 任职要求
从页面提取的要求列表

---

（更多职位...）
```

### 历史记录 Schema (history.json)

```json
{
  "sessions": [
    {
      "session_id": "unique-id",
      "timestamp": "ISO-8601格式",
      "summary": {
        "unread_processed": "处理的未读消息数",
        "new_contacts": "新增联系人数量",
        "resumes_requested": "请求简历数量",
        "errors": "错误数量",
        "duration_seconds": "执行耗时(秒)"
      },
      "candidates": [
        {
          "name": "姓名",
          "job_position": "应聘职位",
          "action": "replied|contacted|skipped|error",
          "resume_requested": "布尔值",
          "ai_reply": "AI生成的回复内容",
          "timestamp": "处理时间",
          "error": "错误信息(如有)"
        }
      ]
    }
  ]
}
```

### 候选人信息 Schema

```json
{
  "candidate_id": "候选人ID",
  "name": "姓名",
  "experience": "工作经验(年)",
  "education": "学历",
  "expected_salary": "期望薪资",
  "skills": ["技能1", "技能2"],
  "tags": ["标签1", "标签2"],
  "last_active": "最后活跃时间",
  "message": "发送的消息内容"
}
```

## 操作流程

### 获取职位信息并保存到本地

```javascript
// 1. 导航到职位管理页面
navigate("https://www.zhipin.com/web/chat/job/list");

// 2. 查找所有"开放中"的职位
const jobs = document.querySelectorAll('.job-item');
const openJobs = Array.from(jobs).filter(job =>
  job.textContent.includes('开放中') || job.textContent.includes('招聘中')
);

// 3. 提取每个职位的信息
const jobData = openJobs.map(job => {
  return {
    title: job.querySelector('.job-title')?.textContent,
    salary: job.querySelector('.job-salary')?.textContent,
    location: job.querySelector('.job-location')?.textContent,
    // ... 更多字段
  };
});

// 4. 格式化为 Markdown 并保存到本地
const markdown = formatJobsToMarkdown(jobData);
saveToFile(markdown, "jobs.md");
```

### 处理未读消息（完整流程 - 包含发送验证）

```javascript
// 1. 导航到聊天列表
navigate("https://www.zhipin.com/web/chat/index");

// 2. 点击"未读"筛选按钮
const unreadFilter = document.querySelector('.filter-tab') ||
                     Array.from(document.querySelectorAll('*'))
                       .find(el => el.textContent === '未读');
if (unreadFilter) unreadFilter.click();

// 3. 获取筛选后的未读列表
const unreadItems = document.querySelectorAll('.geek-item-wrap');

// 4. 逐个处理每个未读消息
for (let item of unreadItems) {
  // ===== 进入候选人详情 =====
  item.click();
  await sleep(2000);

  // ===== 读取候选人信息 =====
  const candidateInfo = getCandidateInfo();

  // ===== 从本地读取职位信息 =====
  const jobInfo = readLocalJobsFile("jobs.md");

  // ===== 生成回复 =====
  const reply = generateReply(candidateInfo, jobInfo);

  // ===== 步骤1：填写回复内容 =====
  const inputBox = document.querySelector('.boss-chat-editor-input');
  inputBox.textContent = reply;
  inputBox.dispatchEvent(new Event('input', { bubbles: true }));
  inputBox.dispatchEvent(new Event('change', { bubbles: true }));

  // ===== 步骤2：验证内容已填写 =====
  await sleep(500);  // 等待DOM更新
  const filledContent = inputBox.textContent || inputBox.innerHTML || inputBox.innerText;
  if (!filledContent || filledContent.length < reply.length * 0.5) {
    console.error('❌ 内容填写失败，重试...');
    continue;  // 跳过或重试
  }

  // ===== 步骤3：真实鼠标点击发送按钮（关键！）=====
  // ⚠️ 重要：JavaScript click() 不会真正发送消息！
  // 必须使用 web-access skill 的 clickAt API 来模拟真实鼠标点击
  //
  // 通过 web-access skill 调用（示例）：
  //   curl -s -X POST "http://localhost:3456/clickAt?target=TARGET_ID" -d ".submit-content"
  //
  // 以下是 JavaScript 示例代码，但实际执行时通过 web-access skill 调用
  const sendBtn = document.querySelector('.submit-content');
  if (!sendBtn || sendBtn.disabled || sendBtn.style.display === 'none') {
    console.error('❌ 发送按钮不可用');
    continue;
  }
  // sendBtn.click();  // ❌ 这个不会工作！必须用 web-access 的 clickAt

  // ===== 步骤4：验证消息发送成功（关键！）=====
  await sleep(3000);  // 等待3秒让消息发送

  // 验证方式1：检查输入框是否已清空
  const inputCleared = inputBox.textContent.length < 5;

  // 验证方式2：检查页面是否显示 [送达] 状态
  const pageText = document.body.innerText;
  const hasDelivered = pageText.includes('[送达]');

  // 验证方式3：检查消息是否出现在聊天记录中
  const allMessages = Array.from(document.querySelectorAll('.message, [class*="msg"]'));
  const myMessages = allMessages.filter(el =>
    el.classList.contains('from-me') ||
    el.classList.contains('my-message') ||
    el.textContent.includes(reply.substring(0, 10))  // 匹配消息开头
  );

  // 综合判断发送是否成功
  if (!inputCleared && !hasDelivered && myMessages.length === 0) {
    console.error('❌ 消息发送失败：输入框未清空，无[送达]状态，聊天记录无新消息');
    continue;  // 发送失败，跳过此候选人
  }

  console.log('✅ 消息发送成功', {
    inputCleared,
    hasDelivered,
    messageCount: myMessages.length
  });

  // ===== 步骤5：再次等待确保后端处理完成 =====
  await sleep(2000);

  // ===== 步骤6：点击"求简历"按钮 =====
  const resumeBtn = Array.from(document.querySelectorAll('*'))
    .find(el => el.textContent.trim() === '求简历');

  if (resumeBtn) {
    const isDisabled = resumeBtn.classList.contains('disabled') ||
                       resumeBtn.disabled ||
                       resumeBtn.getAttribute('disabled') === 'true';

    if (!isDisabled) {
      resumeBtn.click();
      console.log('✅ 已请求简历');
    } else {
      console.log('⚠️ 求简历按钮被禁用');
    }
  }

  // ===== 返回列表处理下一个 =====
  backToList();
  await sleep(1000);
}
```

**发送验证流程说明：**

| 步骤 | 操作 | 验证方法 | 失败处理 |
|------|------|----------|----------|
| ① | 填写内容 | 检查 inputBox 内容长度 | 重试或跳过 |
| ② | 点击发送 | 检查按钮是否可用 | 跳过 |
| ③ | 验证发送 | 检查聊天记录中是否有消息 | 跳过 |
| ④ | 等待处理 | 固定等待3秒 | - |
| ⑤ | 求简历 | 检查 disabled 类 | 记录状态 |

**消息发送失败的可能原因：**

1. **输入框内容未正确设置**
   - 解决：使用多种方式设置（textContent + innerText + innerHTML）
   - 触发多个事件（input + change + focus）

2. **发送按钮不可用**
   - 检查：disabled 属性、display 样式
   - 解决：等待按钮可用后再点击

3. **网络延迟**
   - 解决：增加等待时间到 3-5 秒

4. **页面状态异常**
   - 解决：检查 URL 是否正确，重新加载页面

**调试技巧：**

```javascript
// 打印输入框状态
console.log('Input box:', {
  textContent: inputBox.textContent,
  innerHTML: inputBox.innerHTML,
  value: inputBox.value,
  disabled: inputBox.disabled
});

// 打印发送按钮状态
console.log('Send button:', {
  exists: !!sendBtn,
  disabled: sendBtn?.disabled,
  display: sendBtn?.style.display
});

// 打印聊天记录
console.log('Messages:', allMessages.map(m => m.textContent));
```

## 匹配算法

### 职位匹配度计算

```javascript
function calculateMatchScore(candidate, job) {
  let score = 0;

  // 经验匹配 (30分)
  const expMap = {'不限': 0, '1年以下': 0.5, '1-3年': 2, '3-5年': 4, '5-10年': 7.5, '10年以上': 10};
  const candidateExp = parseExperience(candidate.experience);
  const jobExp = parseExperience(job.experience_required);

  if (candidateExp >= jobExp) {
    score += 30;
  } else if (candidateExp >= jobExp * 0.8) {
    score += 20;
  }

  // 学历匹配 (20分)
  const eduMap = {'博士': 4, '硕士': 3, '本科': 2, '大专': 1, '中专': 0.5, '不限': 0};
  if (eduMap[candidate.education] >= eduMap[job.education_required]) {
    score += 20;
  }

  // 薪资匹配 (20分)
  const candidateSalary = parseSalary(candidate.expected_salary); // 取下限
  const jobSalaryMax = parseSalary(job.salary); // 取上限

  if (candidateSalary <= jobSalaryMax) {
    score += 20;
  } else if (candidateSalary <= jobSalaryMax * 1.2) {
    score += 10;
  }

  // 技能匹配 (30分)
  if (job.skills && candidate.skills) {
    const matchedSkills = candidate.skills.filter(s => job.skills.includes(s));
    score += (matchedSkills.length / job.skills.length) * 30;
  }

  return Math.round(score);
}
```

## 消息模板

### 职位邀请模板

```javascript
const inviteTemplates = {
  default: (name, position) =>
    `您好${name}，看到您的背景很符合我们的【${position}】职位要求。如果您感兴趣，我们可以进一步沟通。`,

  followUp: (name) =>
    `您好${name}，之前向您介绍了职位信息，不知您是否有兴趣？我们期待您的回复。`,

  salaryDiscussion: (job) =>
    `关于薪资，我们的范围是${job.salary}，具体可以根据您的经验和能力面议。`
};
```

### 回复分类规则

| 候选人消息关键词 | 回复类型 | 模板来源 |
|----------------|---------|---------|
| "感兴趣"/"想了解" | 表达兴趣 | 发送详细职位信息（从本地 jobs.md）|
| "多少钱"/"薪资" | 询问薪资 | 提供薪资范围（从本地 jobs.md）|
| "哪里"/"地点" | 询问地点 | 提供工作地点（从本地 jobs.md）|
| "可以聊聊" | 开场白 | 根据职位发送简介（从本地 jobs.md）|
| "不感兴趣" | 拒绝 | 礼貌结束对话 |

## 常见问题

### Q: "求简历"按钮不可用？
A: 该按钮需要在双方都回复后才可用。如果按钮有 `disabled` 类，说明候选人还未回复，需要等待。

### Q: 本地职位文件在哪里？
A: `~/.claude/projects/-Users-steptian-Documents-iLike-Python-feilian-skills/memory/boss-recruiter/jobs/jobs.md`

### Q: 如何更新职位信息？
A: 使用触发词"更新职位信息"或"刷新职位"，skill 会自动从网页获取并更新本地文件。

### Q: 点击"未读"后看不到消息？
A: 可能是：
1. 当前确实没有未读消息
2. 页面需要刷新
3. 登录状态失效

### Q: 候选人发送完全相同的消息？
A: 这通常是群发消息，质量不高，可以优先处理那些发送个性化消息的候选人。
