# 技术文档变更自动通知 Agent 操作手册

本文档用于指导任意 AI Agent 按固定流程完成“需求变更归档、负责人识别、文档摘要、企业微信通知”。Agent 必须按本文档逐项操作，不允许覆盖旧需求版本，不允许把手机号、Webhook、API Key 等敏感信息提交到仓库。

## 最终效果

一次需求变更完成后，应达到以下效果：

1. 需求变更被归档到对应迭代目录，例如 `docs/iterations/S1/v1/`。
2. 初始需求、变更说明、结构化元信息、Agent 读取过的上下文文件都可追溯。
3. GitHub Actions 自动分析 `.md` 文档变更，生成 `CHANGELOG.md` 和 `docs/changes.json`。
4. 企业微信群收到 markdown 摘要通知。
5. 企业微信群收到原生 @ 提醒，提醒对象来自 GitHub Secret 中的人员配置。
6. AI 摘要接口超时时，脚本使用本地 diff 兜底摘要，通知链路不能中断。

## GitHub 配置

### Secrets

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions -> Secrets` 配置：

| 名称 | 必填 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 是 | 摘要模型 API Key。 |
| `WECOM_WEBHOOK_URL` | 是 | 企业微信群机器人 Webhook。 |
| `MODULE_OWNERS_JSON` | 是 | 人员与通知对象配置，包含姓名、角色、手机号或企微 UserID。 |

`MODULE_OWNERS_JSON` 示例：

```json
{
  "modules": [
    {
      "module": "默认通知",
      "keywords": ["*"],
      "owners": [
        {"name": "测试负责人", "role": "测试", "mobile": "13800000000"},
        {"name": "前端负责人", "role": "前端", "mobile": "13800000000"},
        {"name": "后端负责人", "role": "后端", "mobile": "13800000000"}
      ]
    }
  ]
}
```

注意：

- 真实手机号只能放在 GitHub Secret 中，不能提交到仓库文件。
- 当前 demo 的通知脚本从 `MODULE_OWNERS_JSON` 读取企微 @ 对象。
- `keywords: ["*"]` 表示每次文档变更都通知这些人。
- 后续如果要按 Excel 精准通知不同需求负责人，需要让 Agent 根据 Excel 姓名和 GitHub 人员主数据生成精确的负责人匹配结果，再交给通知脚本。

### Variables

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions -> Variables` 配置：

| 名称 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- |
| `LLM_PROVIDER` | 是 | `openai-compatible` | 摘要模型供应商；也支持 `anthropic`。 |
| `LLM_MODEL` | 是 | `gpt-5.5` | 摘要模型名称。 |
| `LLM_API_BASE` | 是 | `https://example.com` | OpenAI-compatible 或 Anthropic API Base URL。 |

## 仓库文件职责

| 文件 | 职责 |
| --- | --- |
| `.github/workflows/doc-change-summary.yml` | GitHub Actions 工作流。监听 `main` 分支 `.md` 文档变化。 |
| `scripts/generate_summary.py` | 根据 git diff 生成文档变更摘要，更新 `CHANGELOG.md` 和 `docs/changes.json`。AI 失败时自动使用本地 diff 兜底。 |
| `scripts/send_notification.py` | 读取 `docs/changes.json`，按 `MODULE_OWNERS_JSON` 匹配负责人，发送企业微信 markdown 和原生 @。 |
| `docs/iteration_module_owners_template.xlsx` | 每个迭代负责人 Excel 模板。 |
| `docs/iteration_owner_excel_contract.md` | 迭代负责人 Excel 字段规范。 |
| `docs/iteration_requirement_versioning.md` | 迭代需求版本归档规范。 |
| `docs/iterations/<迭代>/...` | 每个迭代的初始需求和后续变更版本目录。 |
| `CHANGELOG.md` | 自动生成的文档变更日志。 |
| `docs/changes.json` | 自动生成的最新一次变更摘要，供企微通知脚本读取。 |

## 迭代目录规范

每个迭代一个目录，例如：

```text
docs/iterations/
  S1/
    00_initial/
      requirement.md
      iteration_module_owners.xlsx
    v1/
      change.md
      meta.json
      agent_context/
        requirement_before.md
        requirement_after.md
        iteration_module_owners.xlsx
```

规则：

- `00_initial` 只放初始需求，不允许反复覆盖。
- 每次需求变更新增一个版本目录：`v1`、`v2`、`v3`。
- 版本目录只新增，不删除、不覆盖旧版本。
- 如果需求撤回，也新增下一个版本目录记录撤回原因。

## 负责人 Excel 格式

每个迭代的 `iteration_module_owners.xlsx` 使用 4 列：

| 字段 | 说明 |
| --- | --- |
| `模块需求` | 描述模块、页面、接口、字段或业务变化范围。 |
| `前端负责人` | 只写姓名，多个姓名用 `、`、`,`、`，`、`;`、`；` 分隔。 |
| `后端负责人` | 只写姓名，多个姓名用 `、`、`,`、`，`、`;`、`；` 分隔。 |
| `需求优先级` | 推荐 `P0`、`P1`、`P2`、`P3`。 |

示例：

| 模块需求 | 前端负责人 | 后端负责人 | 需求优先级 |
| --- | --- | --- | --- |
| 订单展示：创建人字段由 createId 调整为 createName。 | 晋鹏 | 聂巧宇 | P1 |

## Agent 执行流程

### 1. 创建迭代初始目录

当一个新迭代开始时，Agent 创建：

```text
docs/iterations/S1/00_initial/
```

必须放入：

```text
docs/iterations/S1/00_initial/requirement.md
docs/iterations/S1/00_initial/iteration_module_owners.xlsx
```

`requirement.md` 保存最初需求。  
`iteration_module_owners.xlsx` 保存本迭代模块需求、前端负责人、后端负责人、优先级。

### 2. 创建需求变更版本

当用户提出需求变更时，Agent 先判断当前迭代下最大的版本号，然后创建下一个版本目录。

如果当前只有 `00_initial`，第一次变更创建：

```text
docs/iterations/S1/v1/
```

如果已经有 `v1`，下一次创建：

```text
docs/iterations/S1/v2/
```

### 3. 编写 change.md

每个版本目录必须包含：

```text
docs/iterations/S1/v1/change.md
```

模板：

```markdown
# S1 v1 需求变更

## 变动人

- 姓名：<变动人>
- 角色：<产品/研发/测试/其他>
- 时间：yyyy-MM-dd HH:mm:ss

## 变更说明

- <说明本次改了什么>

## 影响范围

- 影响模块：
- 影响接口：
- 影响页面：

## 需要关注

- 前端：
- 后端：
- 测试：
```

示例：

```markdown
- 订单展示中的创建人字段由 `createId` 调整为 `createName`。
- 字段替换关系：`createId` -> `createName`。
```

### 4. 编写 meta.json

每个版本目录必须包含：

```text
docs/iterations/S1/v1/meta.json
```

模板：

```json
{
  "iteration": "S1",
  "version": "v1",
  "based_on": "00_initial",
  "changed_by": {
    "name": "变动人姓名",
    "role": "产品"
  },
  "changed_at": "yyyy-MM-dd HH:mm:ss",
  "change_summary": "一句话描述本次需求变动",
  "affected_modules": ["订单展示"],
  "affected_fields": [
    {
      "from": "createId",
      "to": "createName"
    }
  ],
  "agent_context_files": [
    "agent_context/requirement_before.md",
    "agent_context/requirement_after.md",
    "agent_context/iteration_module_owners.xlsx"
  ]
}
```

要求：

- `changed_at` 使用 `yyyy-MM-dd HH:mm:ss`。
- `iteration` 必须和目录名一致。
- `version` 必须和版本目录名一致。
- `agent_context_files` 必须列出 Agent 实际读取过的关键文件。

### 5. 保存 agent_context

每个版本目录必须包含：

```text
docs/iterations/S1/v1/agent_context/
```

至少保存：

```text
requirement_before.md
requirement_after.md
iteration_module_owners.xlsx
```

规则：

- Agent 对比过什么，就保存什么。
- `requirement_before.md` 保存变更前需求快照。
- `requirement_after.md` 保存变更后需求快照。
- `iteration_module_owners.xlsx` 保存本次判断负责人时使用的 Excel。
- 不要放无关文件。

### 6. 检查负责人

Agent 根据 `iteration_module_owners.xlsx` 找到命中的 `模块需求`，读取：

- `前端负责人`
- `后端负责人`
- `需求优先级`

然后结合 GitHub Secret `MODULE_OWNERS_JSON` 中的人员配置补齐：

- 角色
- 手机号
- 企微 UserID

当前 demo 中，脚本直接从 `MODULE_OWNERS_JSON` 匹配通知对象；Excel 作为 Agent 判断和审计依据保留在版本目录中。

### 7. 提交并触发通知

Agent 完成文件后提交到 `main` 分支。

工作流触发条件：

- push 到 `main`
- 且变更中包含 `.md` 文件

注意：

- 只改 `.xlsx` 不会触发通知。
- `CHANGELOG.md` 和 `docs/changes.json` 是自动生成文件，不要手工改。

## 自动通知流程

推送后，GitHub Actions 执行：

1. `Generate change summary`
   - 读取 git diff。
   - 调用 LLM 生成摘要。
   - 如果 LLM 超时或失败，使用本地 diff 生成保底摘要。
   - 写入 `CHANGELOG.md` 和 `docs/changes.json`。
2. `Send to WeCom`
   - 读取 `docs/changes.json`。
   - 读取 `MODULE_OWNERS_JSON`。
   - 发送 markdown 摘要。
   - 发送 text 消息，并通过 `mentioned_mobile_list` 或 `mentioned_list` 原生 @。
3. `Commit and push changelog`
   - 自动提交 `CHANGELOG.md` 和 `docs/changes.json`。

## 通知展示规则

如果变更文件路径是：

```text
docs/iterations/S1/v1/change.md
```

通知标题优先展示：

```text
技术文档更新通知 S1 v1
```

普通文档变更则展示全局版本，例如：

```text
技术文档更新通知 v11
```

下方 text 提醒格式：

```text
请相关负责人关注技术文档更新 S1 v1，详情见上方通知。
```

企微蓝色 @ 由机器人 API 的 `mentioned_mobile_list` 或 `mentioned_list` 生成，不要在正文里手写黑色 @ 文案。

## 验收清单

Agent 完成一次变更后，必须确认：

- `docs/iterations/<迭代>/00_initial/` 存在。
- 本次新增了正确的 `vN` 目录。
- `vN/change.md` 存在。
- `vN/meta.json` 是合法 JSON。
- `vN/agent_context/requirement_before.md` 存在。
- `vN/agent_context/requirement_after.md` 存在。
- `vN/agent_context/iteration_module_owners.xlsx` 存在。
- push 后 GitHub Actions 成功。
- `CHANGELOG.md` 生成了新条目。
- 企业微信群收到 markdown 摘要。
- 企业微信群收到原生 @。

## 排障

### 企微没收到

先看 GitHub Actions：

```bash
gh run list --repo <owner>/<repo> --workflow "Doc Change Summary" --limit 3
gh run view <run-id> --repo <owner>/<repo> --log
```

常见原因：

- 本地 commit 没有 push。
- 只改了 `.xlsx`，没有 `.md` 变更，workflow 不触发。
- `Generate change summary` 失败。
- `WECOM_WEBHOOK_URL` 未配置或已失效。
- `MODULE_OWNERS_JSON` 为空或格式错误。

### AI 摘要接口超时

脚本会打印：

```text
AI summary failed, using fallback summary
```

这是可接受状态。通知仍应继续发送。

### 没有 @ 到人

检查：

- `MODULE_OWNERS_JSON` 是否包含 `owners`。
- 每个 owner 是否有 `mobile` 或 `user_id`。
- 手机号是否是企微成员绑定手机号。
- 日志中是否出现：

```text
WeCom mention targets: user_ids=..., mobiles=...
```

### 通知版本不对

检查变更文件路径是否符合：

```text
docs/iterations/<迭代>/<vN>/change.md
```

只有符合该路径时，通知才会优先显示 `S1 v1` 这类需求版本。

## 当前 demo 已验证

已验证案例：

```text
docs/iterations/S1/v1/change.md
```

变更内容：

```text
订单展示创建人字段由 createId 调整为 createName
```

验证结果：

- GitHub Actions 成功。
- `CHANGELOG.md` 生成 `v11` 条目。
- 企业微信 markdown 通知发送成功。
- 企业微信手机号原生 @ 发送成功。
- AI 接口失败时，保底摘要可继续保障通知链路。
