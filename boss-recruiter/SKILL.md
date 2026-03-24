---
name: boss-recruiter
description: "BOSS直聘自动化招聘助手。触发词：'处理招聘'、'BOSS直聘'、'找候选人'、'招聘自动化'、'boss直聘聊天'、'处理未读消息'、'获取候选人简历'、'筛选候选人'、'批量联系候选人'、'更新职位信息'。用于在BOSS直聘网站自动处理未读消息、智能回复、获取简历，以及在推荐牛人列表中筛选候选人并发送职位邀请。"
user-invocable: true
context: fork
agent: general-purpose
allowed-tools: Skill(web-access)
---

# BOSS 直聘自动化招聘助手

这是一个帮助你在 BOSS 直聘平台上自动化招聘流程的 skill。

## 前置条件

在执行本 skill 之前，请确保：

1. **已登录 BOSS 直聘**：在浏览器中访问 https://www.zhipin.com 并完成登录
2. **启用 Chrome 远程调试**：在 Chrome 地址栏打开 `chrome://inspect/#remote-debugging`，勾选 **"Allow remote debugging for this browser instance"**

### ⚠️ 重要：使用已打开并登录的浏览器 tab

**问题**：BOSS 直聘等部分网站的登录态在不同 tab 之间不共享。新建的 tab 会丢失登录状态，导致无法正常操作。

**解决方案**：本 skill 会自动检测并使用你已经打开并登录的浏览器 tab，而不是创建新 tab。

**准备工作**：
1. 请在 Chrome 中手动打开 https://www.zhipin.com 并完成登录
2. 确保该 tab 保持打开状态
3. 执行本 skill 时，它会自动找到并使用该 tab

本 skill 使用 **web-access skill** 进行浏览器自动化操作，无需安装 Playwright。

## 数据存储位置

### 职位信息
```
~/.claude/projects/-Users-steptian-Documents-iLike-Python-feilian-skills/memory/boss-recruiter/jobs/
└── jobs.md          # 所有开放中的职位详情
```

### 执行历史
```
~/.claude/projects/-Users-steptian-Documents-iLike-Python-feilian-skills/memory/boss-recruiter/
├── history.json     # 执行历史记录
└── session.json     # 当前会话进度（用于断点续传）
```

## ⏰ 上下文管理（重要！）

**问题**：长时间运行会消耗大量上下文（token），导致性能下降甚至无法继续。

**解决方案**：每工作 **10 分钟**，自动保存进度并提示用户重置。

### 工作流程

```
开始 → 记录开始时间 → 处理候选人 → 检查时间 → 超过10分钟？
                                                      ↓ 是
                              保存进度到 session.json → 提示用户 → 用户说"继续" → 清空上下文 → 从进度恢复 → 继续处理
                                                      ↓ 否
                                                继续处理下一个候选人
```

### 进度文件格式 (session.json)

```json
{
  "session_id": "2025-03-24-14-30",
  "start_time": "2025-03-24T14:30:00+08:00",
  "last_checkpoint": "2025-03-24T14:40:00+08:00",
  "elapsed_minutes": 10,
  "phase": "unread",
  "current_target": "chat/index",
  "processed": [
    {"name": "胡美英", "position": "验光销售员", "status": "replied", "time": "14:32"},
    {"name": "吴女士", "position": "电商事业部HRBP", "status": "replied+resume", "time": "14:35"}
  ],
  "pending": [
    {"name": "拉拉", "position": "验光销售员"},
    {"name": "罗志鑫", "position": "验光销售员"}
  ],
  "stats": {
    "unread_processed": 2,
    "new_contacts": 0,
    "resumes_requested": 1
  }
}
```

### 检查点触发条件

每处理完一个候选人后检查：
1. 距离开始时间是否超过 **10 分钟**
2. 如果是，执行检查点流程

### 检查点流程

```
1. 保存当前进度到 session.json
2. 显示进度摘要给用户
3. 提示用户说"继续"来恢复工作
4. 用户说"继续"后：
   a. 读取 session.json 恢复状态
   b. 从 pending 列表继续处理
   c. 更新开始时间（重置10分钟计时器）
```

### 用户提示格式

```
⏰ 已工作 10 分钟，建议重置上下文以保持性能。

📊 当前进度：
- 已处理：2 位候选人
- 待处理：2 位候选人
- 简历获取：1 份

💾 进度已保存。请说"继续"来恢复工作。
```

### 断点续传

如果意外中断，下次启动时：
1. 检查是否存在 session.json
2. 如果存在且有未完成任务，询问用户是否继续
3. 用户确认后从断点恢复

## 核心流程

### 🔍 步骤 0：查找并使用已登录的 BOSS 直聘 tab（必需）

**重要**：在执行任何操作前，必须先找到用户已打开并登录的 BOSS 直聘 tab。

#### 查找已登录 tab 的流程

```bash
# 1. 获取所有已打开的 tab 列表
curl -s http://localhost:3456/targets

# 返回格式：
# [
#   {"targetId": "A1B2C3", "title": "BOSS直聘", "url": "https://www.zhipin.com/web/user/?ka=header-login"},
#   {"targetId": "D4E5F6", "title": "Google", "url": "https://www.google.com"},
#   ...
# ]
```

#### 匹配逻辑

```javascript
// 通过 URL 或 title 匹配 BOSS 直聘 tab
const targets = JSON.parse(shell('curl -s http://localhost:3456/targets'));
const bossTab = targets.find(t =>
  t.url.includes('zhipin.com') || t.title.includes('BOSS') || t.title.includes('直聘')
);

if (bossTab) {
  console.log('✅ 找到已打开的 BOSS 直聘 tab:', bossTab.targetId);
  TARGET_ID = bossTab.targetId;  // 使用该 tab 进行后续操作
} else {
  console.log('❌ 未找到已打开的 BOSS 直聘 tab');
  // 提示用户打开并登录
}
```

#### 如果未找到已登录 tab

```
⚠️ 未找到已打开的 BOSS 直聘 tab。

请按以下步骤操作：
1. 在 Chrome 中打开新标签
2. 访问 https://www.zhipin.com
3. 完成登录
4. 确保页面加载完成
5. 告诉我"准备好了"或"继续"

完成后我将自动检测并使用该 tab。
```

#### 验证登录状态

找到 tab 后，验证是否已登录：

```javascript
// 通过检查页面元素判断登录状态
const isLoggedIn = () => {
  // 检查是否有用户头像或登录按钮消失
  const hasUserAvatar = document.querySelector('.user-nav') !== null;
  const hasLoginBtn = document.querySelector('.btn-login') === null;
  return hasUserAvatar || hasLoginBtn;
};

// 如果未登录，提示用户
if (!isLoggedIn()) {
  return { success: false, reason: '未登录，请在当前 tab 完成登录' };
}
```

#### 后续操作使用找到的 tab

一旦找到并验证登录状态，所有后续操作都使用该 `TARGET_ID`：

```bash
# 导航（使用已打开的 tab）
curl -s "http://localhost:3456/navigate?target=$TARGET_ID&url=https://www.zhipin.com/web/chat/index"

# 执行 JS
curl -s -X POST "http://localhost:3456/eval?target=$TARGET_ID" -d 'document.title'

# 点击
curl -s -X POST "http://localhost:3456/click?target=$TARGET_ID" -d '.filter-tab'
```

### ⏰ 时间管理与上下文重置

**重要**：为避免上下文溢出，每 **10 分钟** 必须执行一次检查点。

```
┌─────────────────────────────────────────────────────────────┐
│  时间管理流程                                                │
├─────────────────────────────────────────────────────────────┤
│  1. 记录开始时间 start_time                                   │
│  2. 每处理完一个候选人后：                                     │
│     elapsed = now() - start_time                             │
│     if elapsed >= 10 minutes:                                │
│        → 保存进度到 session.json                              │
│        → 显示进度摘要                                         │
│        → 提示用户说"继续"                                     │
│        → 等待用户响应                                         │
│        → 清空上下文，从 session.json 恢复                      │
│        → 重置 start_time                                      │
│        → 继续处理                                             │
└─────────────────────────────────────────────────────────────┘
```

**检查点代码示例**：
```javascript
const CHECKPOINT_INTERVAL = 10 * 60 * 1000; // 10分钟（毫秒）

function shouldCheckpoint(startTime) {
  return Date.now() - startTime >= CHECKPOINT_INTERVAL;
}

function saveCheckpoint(data) {
  const session = {
    session_id: generateSessionId(),
    start_time: startTime,
    last_checkpoint: new Date().toISOString(),
    elapsed_minutes: Math.floor((Date.now() - startTime) / 60000),
    phase: currentPhase,
    processed: processedCandidates,
    pending: pendingCandidates,
    stats: statistics
  };
  writeToFile('session.json', JSON.stringify(session, null, 2));
}

function restoreFromCheckpoint() {
  const session = readFile('session.json');
  if (session && session.pending.length > 0) {
    return session;
  }
  return null;
}
```

### 初始化：获取职位信息（首次或更新时）

当触发词包含"更新职位信息"或首次运行时：

1. **访问职位管理页面**
   - **使用已找到的 tab**（`$TARGET_ID`）导航：
     ```bash
     curl -s "http://localhost:3456/navigate?target=$TARGET_ID&url=https://www.zhipin.com/web/chat/job/list"
     ```
   - 查找所有"开放中"状态的职位

2. **提取职位详情**
   - 职位名称、薪资范围
   - 工作地点
   - 经验要求、学历要求
   - 职位描述（JD）
   - 发布时间

3. **保存到本地文件**
   - 写入 `jobs.md`（Markdown 格式）
   - 格式见下方"职位信息格式"

### 第一阶段：处理未读消息（高优先级）

**优化策略**：使用"未读"筛选功能，只处理未读消息

1. **导航到聊天列表并筛选未读**
   - **使用已找到的 tab**（`$TARGET_ID`）导航：
     ```bash
     curl -s "http://localhost:3456/navigate?target=$TARGET_ID&url=https://www.zhipin.com/web/chat/index"
     ```
   - **点击"未读"筛选按钮**（CSS选择器参考）：
     ```bash
     curl -s -X POST "http://localhost:3456/click?target=$TARGET_ID" -d '.filter-tab'
     ```
   - 获取筛选后的未读消息列表

2. **逐个处理未读消息**

   **重要：发送消息的完整验证流程**

   步骤顺序：
   ```
   ① 填写内容 → ② 验证填写 → ③ 真实鼠标点击发送 → ④ 验证发送成功 → ⑤ 等待 → ⑥ 求简历
   ```

   详细步骤（必须严格执行）：
   - 点击未读对话进入详情
   - **读取当前沟通的职位信息**（从页面获取，不是本地文件）
   - 读取候选人信息：姓名、经验、学历、期望职位/期望薪资
   - 读取候选人消息内容
   - **职位匹配检查**：检查沟通职位是否在本地在招职位列表中
   - AI 智能分析并生成回复（基于当前沟通的职位）

   **职位匹配规则**：
   ```
   1. 获取页面上的"沟通职位"名称（候选人正在沟通的职位）
   2. 从本地 jobs.md 读取所有"开放中"的职位列表
   3. 匹配判断：
      - 如果沟通职位 ∈ 本地在招职位列表 → 匹配成功，继续沟通
      - 如果沟通职位 ∉ 本地在招职位列表 → 职位已关闭或不存在，说明情况
   4. 匹配成功后：
      - 从本地 jobs.md 读取该职位的详细信息（地点、薪资、要求）
      - 生成回复时使用该职位的具体信息
   ```

   **示例**：
   ```
   候选人沟通职位：门店运营专员（眼镜行业）
   本地在招职位：[门店运营专员、验光销售员、电商事业部HRBP]
   匹配结果：✅ 匹配成功
   回复策略：使用门店运营专员的详情生成回复
   ```

   **步骤1：填写回复内容**
   ```javascript
   const input = document.querySelector('.boss-chat-editor-input');
   input.textContent = reply;
   input.dispatchEvent(new Event('input', { bubbles: true }));
   input.dispatchEvent(new Event('change', { bubbles: true }));
   ```

   **步骤2：验证内容已填写**
   ```javascript
   // 检查输入框是否包含刚才填写的内容
   const filledContent = input.textContent || input.innerHTML;
   if (filledContent.length < reply.length * 0.5) {
       return { success: false, reason: '内容未填写成功' };
   }
   ```

   **步骤3：真实鼠标点击发送按钮（关键！）**

   ⚠️ **必须使用真实鼠标点击，普通 JavaScript click() 可能无效！**

   本 skill 使用 web-access skill，通过以下方式点击：

   ```bash
   # 使用 web-access 的真实点击
   curl -s -X POST "http://localhost:3456/clickAt?target=TARGET_ID" -d ".submit-content"
   ```

   **步骤4：验证消息发送成功**
   ```javascript
   await sleep(3000);  // 等待3秒

   // 检查1：输入框是否已清空
   const inputCleared = inputBox.textContent.length < 5;

   // 检查2：消息是否出现在聊天记录中，带 [送达] 状态
   const pageText = document.body.innerText;
   const hasMessage = pageText.includes('[送达]') &&
                      pageText.includes('您发送的内容关键词');

   if (!inputCleared || !hasMessage) {
       return { success: false, reason: '消息未发送成功' };
   }
   ```

   **步骤5：再次等待确保后端处理完成**
   ```javascript
   await sleep(2000);  // 再等待2秒
   ```

   **步骤6：点击"求简历"按钮**
   - 检查按钮是否可用（没有 `disabled` 类）
   - 如果可用则点击
   - 如果不可用则说明需要等待候选人回复

   **重要提示：**
   - 使用 web-access skill 的 clickAt API 进行真实鼠标点击
   - 每步都必须验证成功才继续
   - 如果任何一步失败，记录错误并重试（最多3次）
   - 发送成功的标志：输入框清空 + 消息显示 [送达]

   **⏰ 每处理完一个候选人后，检查时间：**
   ```
   if (Date.now() - startTime >= 10 * 60 * 1000) {
       // 触发检查点
       1. 保存进度到 session.json
       2. 显示进度摘要
       3. 提示用户说"继续"
       4. 停止当前处理，等待用户响应
   }
   ```

3. **处理完成条件**
   - 所有未读消息已处理
   - 列表为空或返回列表页

### 🔄 检查点恢复流程

当用户说"继续"后：

```
1. 读取 session.json 获取进度
2. 恢复状态：
   - 当前阶段 (phase)
   - 已处理列表 (processed)
   - 待处理列表 (pending)
   - 统计数据 (stats)
3. 重置开始时间：start_time = Date.now()
4. 继续处理 pending 列表中的候选人
```

**恢复时的输出格式：**
```
📂 从检查点恢复：
- 恢复时间：2025-03-24 14:45
- 当前阶段：处理未读消息
- 已处理：3 位候选人
- 待处理：2 位候选人
- 继续处理...
```

### 第二阶段：推荐牛人（资源允许时）

**优化策略**：使用本地职位信息进行匹配

1. **读取本地职位信息**
   - 从 `jobs.md` 加载所有开放中的职位
   - 选择一个目标职位（优先级：最早发布 / 薪资最高）

2. **访问推荐牛人页面**
   - **使用已找到的 tab**（`$TARGET_ID`）导航：
     ```bash
     curl -s "http://localhost:3456/navigate?target=$TARGET_ID&url=https://www.zhipin.com/web/chat/recommend"
     ```
   - **使用筛选条件**：根据职位要求设置筛选器（如经验、学历）

3. **匹配并联系候选人**
   - 读取候选人信息
   - **与本地职位信息匹配**（不是网页）
   - 计算匹配度（经验、学历、薪资、技能）
   - 匹配度 > 60 则发送邀请
   - 使用职位相关的邀请话术

4. **数量控制**
   - 软限制 60 个候选人/天
   - 记录已联系候选人（避免重复）

## 职位信息格式

`jobs.md` 文件格式：

```markdown
# BOSS 直聘职位信息

更新时间：2025-03-24 14:30:00

## 门店运营专员（眼镜行业）

- **职位ID**: job-123456
- **状态**: 开放中
- **薪资**: 5-7K
- **工作地点**: 江苏丹阳
- **经验要求**: 1-3年
- **学历要求**: 不限
- **发布时间**: 2025-03-20

### 职位描述
负责眼镜门店的日常运营管理，包括销售管理、库存管理、客户服务等。

### 任职要求
1. 有门店或零售行业经验优先
2. 具备良好的沟通能力
3. 能够接受丹阳工作地点

---

## 验光销售员

- **职位ID**: job-789012
- **状态**: 开放中
- **薪资**: 6-10K
- **工作地点**: 杭州滨江区银泰百货
- **经验要求**: 1-3年
- **学历要求**: 中专/中技
- **发布时间**: 2025-03-15

### 职位描述
负责眼镜验光和销售工作，为顾客提供专业的验光服务。

### 任职要求
1. 眼视光相关专业
2. 持有验光师资格证书
3. 有眼镜店或医院验光经验优先

---

（更多职位...）
```

## 使用方法

### 触发方式

通过以下任一方式触发本 skill：

**处理未读消息**：
- "处理招聘"
- "BOSS直聘" / "boss 直聘"
- "处理未读消息"
- "回复候选人"

**推荐牛人**：
- "找候选人" / "筛选候选人"
- "招聘自动化"
- "批量联系候选人"
- "推荐牛人"

**更新职位信息**：
- "更新职位信息"
- "刷新职位"
- "获取职位详情"

### 执行模式

触发后，系统会自动判断：

| 触发词 | 执行内容 |
|--------|----------|
| 包含"更新职位"/"刷新职位" | 仅更新职位信息到本地 |
| 包含"找候选人"/"推荐牛人" | 仅处理推荐牛人（跳过未读）|
| 其他（"处理招聘"等） | 完整模式：先未读后推荐 |

## 智能回复策略

### 回复生成逻辑

⚠️ **重要**：必须基于**当前沟通职位**生成回复，而不是随便选择职位。

系统基于以下信息生成回复：
1. **候选人信息**：从页面读取（姓名、经验、学历、期望职位/期望薪资）
2. **候选人消息**：从页面读取
3. **当前沟通职位**：**从页面读取**（查找"沟通职位："后的职位名称）
4. **职位匹配分析**：检查沟通职位是否在本地在招职位列表中

### 职位匹配检查流程

```javascript
// 1. 从页面获取候选人的"沟通职位"
const currentJob = document.body.innerText.match(/沟通职位[：:]+\s*([^\n]+)/)?.[1];

// 2. 从本地 jobs.md 读取所有开放中的职位
const localJobs = readLocalJobs(); // 从 jobs.md 读取
const availableJobs = localJobs.filter(job => job.status === '开放中').map(job => job.name);

// 3. 检查沟通职位是否在本地职位列表中
const isMatch = availableJobs.some(job => currentJob.includes(job) || job.includes(currentJob));

// 4. 如果匹配，获取该职位的详细信息
const jobDetails = isMatch ? localJobs.find(job => currentJob.includes(job.name) || job.name.includes(currentJob)) : null;
```

**匹配判断逻辑**：
```
IF 沟通职位 在 本地在招职位列表 中:
    → 匹配成功 ✅
    → 使用该职位的详细信息（地点、薪资、要求）生成回复

ELSE:
    → 职位不匹配 ❌
    → 说明该职位已关闭或不存在
    → 询问是否对其他职位感兴趣
```

### 回复类型判断

| 候选人消息/情况 | 回复策略 |
|-----------------|---------|
| 沟通职位在本地职位列表中（匹配成功） | 使用本地该职位的详细信息（地点、薪资、要求）生成回复，邀请进一步沟通 |
| 沟通职位**不在**本地职位列表中（不匹配） | 说明该职位已关闭或不存在，列出当前在招职位，询问是否感兴趣 |
| 询问职位详情 | 从本地读取该职位的 JD，介绍详细信息 |
| 询问薪资 | 从本地读取该职位的薪资范围 |
| 询问地点 | 从本地读取该职位的工作地点，询问是否可接受 |
| 已发送简历/表达兴趣 | 确认收到，介绍该职位详情，询问进一步问题 |
| 确认面试 | 提供可选时间段，要求确认 |
| 拒绝/不考虑 | 礼貌回复，标记为不合适 |

### 回复模板示例

⚠️ **注意**：模板中的 `{职位}`、`{地点}`、`{薪资}`、`{要求}` 必须从**本地 jobs.md** 中对应职位的信息读取。

**情况1：沟通职位在本地职位列表中（匹配成功）**

```
您好{候选人姓名}，感谢您的关注！

这个{职位}岗位在{工作地点}，薪资范围{薪资}。

{职位简介：1-2句话描述职位内容}

请问您对{具体问题}还有什么想了解的吗？
```

**示例（门店运营专员）**：
```
您好刘先生，感谢您的关注！

这个门店运营专员岗位在江苏丹阳，薪资范围8-11K。

主要负责眼镜门店的日常运营管理，包括销售管理、库存管理、客户服务等。有门店或零售行业经验优先。

请问您对江苏丹阳这个工作地点可以接受吗？
```

**情况2：沟通职位不在本地职位列表中（不匹配）**

```
您好{候选人姓名}，

抱歉，您沟通的{沟通职位}职位目前已经关闭了/不在我们的招聘计划中。

我们目前在招的职位有：
{列出2-3个主要职位}

请问您对其中哪个职位感兴趣吗？
```

**情况3：候选人已发送简历（匹配成功）**

```
{候选人姓名}您好，收到您的简历了！

我这边沟通的{职位}岗位在{地点}，薪资{薪资}。

请问：
1. 您对{地点}这个工作地点可以接受吗？
2. {根据候选人背景提1个相关问题}

方便的话我们进一步沟通一下？
```

## 页面操作参考

### 未读筛选按钮

聊天列表页面的"未读"筛选按钮：
- 文本：`全部 未读`
- 选择器：`.filter-tab` 或包含"未读"文本的可点击元素
- 操作：点击后只显示未读消息

### 读取当前沟通职位并进行匹配（重要！）

在对话详情页面，按以下步骤处理：

**步骤1：从页面读取候选人的"沟通职位"**
```javascript
const pageText = document.body.innerText;
const jobMatch = pageText.match(/沟通职位[：:]+\s*([^\n]+)/);
const currentJob = jobMatch ? jobMatch[1].trim() : '';
// 示例结果：currentJob = "门店运营专员（眼镜行业）"
```

**步骤2：从本地 jobs.md 读取所有开放中的职位**
```javascript
// 读取本地职位文件
const localJobs = [
  { name: '门店运营专员（眼镜行业）', location: '江苏丹阳', salary: '8-11K', status: '开放中' },
  { name: '验光销售员', location: '杭州滨江区', salary: '6-10K', status: '开放中' },
  { name: '电商事业部HRBP', location: '镇江', salary: '10-15K', status: '开放中' }
];
```

**步骤3：检查沟通职位是否在本地职位列表中**
```javascript
// 检查是否匹配
const matchedJob = localJobs.find(job =>
  currentJob.includes(job.name) || job.name.includes(currentJob)
);

if (matchedJob && matchedJob.status === '开放中') {
  // 匹配成功 ✅
  console.log('匹配成功，使用职位详情：', matchedJob);
} else {
  // 不匹配 ❌
  console.log('职位不匹配或已关闭');
}
```

**示例输出**：
```
候选人沟通职位：门店运营专员（眼镜行业）
本地职位列表：[门店运营专员、验光销售员、电商事业部HRBP]
匹配结果：✅ 匹配成功
职位详情：江苏丹阳，8-11K
```

### 职位管理页面

- URL: `https://www.zhipin.com/web/chat/job/list`
- 导航命令：`curl -s "http://localhost:3456/navigate?target=$TARGET_ID&url=https://www.zhipin.com/web/chat/job/list"`
- "开放中"状态标识
- 职位详情链接通常在职位卡片上

### 推荐牛人页面

- URL: `https://www.zhipin.com/web/chat/recommend`
- 导航命令：`curl -s "http://localhost:3456/navigate?target=$TARGET_ID&url=https://www.zhipin.com/web/chat/recommend"`
- 筛选器通常在页面顶部或侧边
- 候选人卡片显示基本信息

## 错误处理

- **登录失效**：提示用户重新登录，等待确认后继续
- **沟通职位不在本地职位列表中**：
  - 说明该职位已关闭或不存在
  - 列出当前在招职位供参考
  - 记录到处理日志，供人工后续跟进
- **无法获取沟通职位**：
  - 记录错误
  - 跳过该候选人
  - 继续处理下一个
- **本地职位文件不存在**：自动触发"更新职位信息"流程（用于推荐牛人阶段）
- **页面元素找不到**：跳过当前候选人，记录错误，继续下一个
- **消息发送失败**：记录失败，等待用户指示
- **达到频率限制**：暂停 30 秒后继续

## 注意事项

1. **频率控制**：避免过快操作，消息间隔至少 3-5 秒
2. **人工审核**：重要消息建议人工审核后再发送
3. **礼貌沟通**：所有自动消息保持礼貌和专业
4. **合规性**：遵守 BOSS 直聘平台规则
5. **职位更新**：建议每周更新一次职位信息

## 开始执行

当你准备好时，使用触发词即可开始：
- **处理招聘** - 完整流程（未读 + 推荐）
- **更新职位信息** - 仅更新职位到本地
- **找候选人** - 仅处理推荐牛人

---

*本 skill 使用 web-access skill 进行浏览器自动化操作。*
*职位信息存储在本地，提高响应速度并减少网页读取。*
