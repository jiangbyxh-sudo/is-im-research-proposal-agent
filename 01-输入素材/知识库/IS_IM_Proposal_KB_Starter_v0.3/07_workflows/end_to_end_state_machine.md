# 端到端状态机

```text
INPUT
  ↓
LOAD_DIRECTION_CATALOG
  ├─ 按知识库章节分组
  ├─ 同义/重复方向合并，保留全部来源分组
  ↓
SCOPE_CHECK ── OUT_OF_SCOPE / SCOPE_UNCERTAIN → STOP/PAUSE
  ↓
KB_COVERAGE_CHECK ── KB_PARADIGM_MISSING → DISCLOSE + LIVE_SEARCH + PAUSE
  ↓
NORMALIZE_REQUEST
  ├─ 大方向 + 细分研究问题 → FOCUSED_QUERY_PLAN
  └─ 仅大方向 → TOP_FIVE_SUBDIRECTION_PLAN
       └─ 当前年份及此前四年、合格期刊论文数降序、输出前五
  ↓
QUERY_PLAN
  ↓
SEARCH_ZH + SEARCH_EN
  ↓
VERIFY_JOURNALS + VERIFY_PAPERS + DEDUP + RETRACTION_CHECK
  ├─ insufficient → INSUFFICIENT_ELIGIBLE_PAPERS
  ↓
EVIDENCE_EXTRACTION
  ↓
SYNTHESIS
  ↓
GAP_AND_INNOVATION_CANDIDATES
  ↓
WAITING_FOR_USER_SELECTION
  ├─ no selection → USER_SELECTION_REQUIRED
  ↓
PROPOSAL_GENERATION
  ↓
WRITING_GUIDANCE
```

## 状态输出最小字段

`state`、`status_code`、`message_to_user`、`artifacts`、`evidence_ids`、`next_allowed_actions`。

Agent不得跨越状态。例如，处于 `WAITING_FOR_USER_SELECTION` 时，`PROPOSAL_GENERATION` 不是允许动作。

## 输入分支约束

- 用户不需要额外选择“检索模式”；分支由是否提交 `fine_grained_question` 自动确定。
- 两条分支都必须保留用户设置的中文、英文论文数量；未设置时分别至少10篇、20篇。
- 热门小方向排名只使用最近五个日历年内通过期刊与论文核验的记录；经典文献不参与热门度计数，但在后续方向分析中继续检索。
- 动态检索接口不可用时停在 `QUERY_PLAN` 后，返回 `DYNAMIC_RETRIEVAL_UNAVAILABLE`，不得使用虚构论文继续。
