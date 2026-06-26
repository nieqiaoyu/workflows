# 迭代需求文档版本归档规范

需求文档不能被覆盖式替换。每个迭代建立一个独立目录，保存最初需求和每一次后续变动；每次变动都必须有版本号、变动人、变更说明，以及 agent 当时实际读取过的文件快照。

## 目录结构

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
    v2/
      change.md
      meta.json
      agent_context/
        requirement_before.md
        requirement_after.md
        iteration_module_owners.xlsx
  S2/
    00_initial/
      requirement.md
      iteration_module_owners.xlsx
```

## 目录含义

| 路径 | 说明 |
| --- | --- |
| `docs/iterations/S1/` | 一个迭代一个目录，目录名按团队迭代名称填写，例如 `S1`、`S2`、`2026-Q3-S1`。 |
| `00_initial/` | 本迭代最初需求。只保存初始版本，不在这里反复覆盖。 |
| `00_initial/requirement.md` | 本迭代最初需求正文。也可以放 Word/PDF/Excel，但建议同时保留一份 markdown 摘要。 |
| `00_initial/iteration_module_owners.xlsx` | 本迭代需求负责人表，使用 `模块需求 / 前端负责人 / 后端负责人 / 需求优先级` 格式。 |
| `v1/`、`v2/` | 每一次需求变动一个版本目录，按自然数递增。 |
| `vN/change.md` | 本次需求变动说明，给人看。 |
| `vN/meta.json` | 本次变动的结构化元信息，给脚本和 agent 读。 |
| `vN/agent_context/` | agent 生成摘要或判断负责人时实际读取过的文件快照。 |

## change.md 模板

```markdown
# S1 v1 需求变更

## 变动人

- 姓名：张三
- 角色：产品
- 时间：2026-06-26 10:00:00

## 变更说明

- 说明本次需求改了什么。
- 说明为什么改。

## 影响范围

- 影响模块：
- 影响接口：
- 影响页面：

## 需要关注

- 前端：
- 后端：
- 测试：
```

## meta.json 模板

```json
{
  "iteration": "S1",
  "version": "v1",
  "based_on": "00_initial",
  "changed_by": {
    "name": "张三",
    "role": "产品"
  },
  "changed_at": "2026-06-26 10:00:00",
  "change_summary": "一句话描述本次需求变动",
  "agent_context_files": [
    "agent_context/requirement_before.md",
    "agent_context/requirement_after.md",
    "agent_context/iteration_module_owners.xlsx"
  ]
}
```

## agent_context 规则

- agent 读过哪些文件，就把这些文件复制或导出到 `agent_context/`。
- 如果 agent 对比了变更前后需求，至少保留：
  - `requirement_before.md`
  - `requirement_after.md`
- 如果 agent 用负责人表判断通知对象，必须保留：
  - `iteration_module_owners.xlsx`
- 文件名尽量稳定，避免用 `最终版`、`最新版` 这类名称。
- 不要把无关文件放进 `agent_context/`，否则后续追溯会变乱。

## 版本规则

- `00_initial` 是初始需求，不算变动版本。
- 第一次需求变动用 `v1`，第二次用 `v2`，依次递增。
- 版本目录只新增，不覆盖、不删除旧版本。
- 如果某次变动撤回，也新建下一个版本目录记录撤回原因，例如 `v3` 写明“撤回 v2 的某项需求”。
- 通知里的版本号应优先使用需求版本，例如 `S1 v2`，而不是只用全局自增号。

## 自动化读取建议

脚本或 agent 应优先读取当前迭代目录中数字最大的 `vN` 目录；如果没有任何 `vN`，则读取 `00_initial`。

一次通知建议包含：

- 迭代：`S1`
- 需求版本：`v2`
- 变动人：来自 `meta.json.changed_by`
- 变更摘要：来自 `change.md` 或 `meta.json.change_summary`
- 负责人：由 `iteration_module_owners.xlsx` 和 GitHub 人员配置共同决定
- agent 依据：列出 `agent_context_files`
