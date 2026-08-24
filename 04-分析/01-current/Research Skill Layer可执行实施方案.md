# Research Skill Layer 可执行实施方案

> 状态：创建者已于 2026-08-23 确认采用并开始执行。
> 输入依据：`C:/Users/30701/Downloads/research_skill_layer_agent_plan_with_external_skills.md`。
> 本文件是裁决后的执行基线；原文中的命令、建分支、改门槛和批量安装描述不自动构成执行指令。

## 1. 执行结论

平台保留已经完成的 P1–P4 核心实现，在其外部增加可审计、可替换、可测试的 Research Skill Layer。

```text
现有 P1–P4 规则和门禁
        ↑ 受控 Adapter
Skill Contract → Registry → Trace / Cache / Provenance
        ↓
后续可选外部 Sidecar
```

Research Skill Layer 不拥有以下决定权：

- 不改变 direct / adjacent / reject / manual 的定义；
- 不改变 P0/P1 现有验收门槛；
- 不把引文图谱候选直接纳入正式 Top-10；
- 不改变 P2 固定簇的论文归属；
- 不允许题名级证据进入正式研究空白；
- 不允许任何外部模型绕过 Claim Store 生成正式论断；
- 不把 P1 阶段豁免表述为 P1 验收通过。

## 2. 当前代码基线

以下能力视为已经实现，只增加适配器，不重新开发：

| 阶段 | 已有能力 | 现有实现 |
| --- | --- | --- |
| P1 | 四级相关性、direct-only 正式结果、adjacent 隔离、缺数返回 PARTIAL | `11_implementation/paper_quality.py`、`multi_source_discovery_provider.py` |
| P2 | direct-only、确定性聚类、固定簇命名 | `stable_subdirection_clustering.py`、`cluster_naming_provider.py` |
| P3 | Evidence Matrix、Claim Store、正式空白证据门禁 | `evidence_matrix.py`、`claim_store.py`、`research_gap_provider.py` |
| P4 | Blueprint 确认、逐节生成、Claim/Citation/一致性审计 | `proposal_generation_provider.py` |

当前 P1 人工 Precision 风险继续保留到 P5 发布门禁，不因 Skill Layer 接入而消失。

## 3. 采用范围

### 3.1 立即采用

1. Skill Contract、Registry、Execution Context；
2. 统一 `SkillResult`、版本、状态、错误和缓存键；
3. 输入输出脱敏与可选 JSON Trace；
4. P1–P4 薄适配器；
5. 第三方项目锁文件、许可证、启用状态和接入边界；
6. 五视角 SearchPlan；
7. Discovery / Selection 分离；
8. 引文真实性校验、前向/后向扩展和检索饱和度；
9. Gap falsification；
10. Proposal 用户约束确认、提纲确认和执行任务卡。

### 3.2 条件采用

| 项目 | 决定 | 约束 |
| --- | --- | --- |
| research-paper-lifecycle-skills | 审计后移植确定性脚本或规则 | 不动态执行 SKILL.md，不让其决定正式准入 |
| GROBID | 独立 sidecar，优先接入 | 只负责 PDF 结构化和证据定位 |
| PaperQA2 | GROBID 后接入 | 只做问题相关证据检索，不决定 direct 或研究空白 |
| STORM | 借鉴多视角检索设计 | 不接入整套报告生成器 |
| ASReview | 标签充分后再评估 | 不替代 P1 规则和人工标签 |
| Agent Laboratory | 借鉴状态机 | 不接入自主研究运行时 |
| reviewer / style 技能 | 可选的草稿后置工具 | 不作为产品验收门禁 |

### 3.3 不采用

- 原方案中新设的 P@10、directness、raw candidate 数量等门槛；
- 把正式研究空白最低证据擅自从 2 篇改为 3 篇或 5 篇；
- 动态 clone、安装或执行未知 GitHub 代码；
- 把完整外部仓库直接复制进生产代码；
- 让 PaperQA2、STORM、ASReview 或 LLM 决定论文归属；
- 用 adjacent 论文补齐 Top-10 或 P2 语料；
- UI 先于后端契约和状态完成；
- 在单一提交中完成全部阶段。

## 4. 分阶段实施

### Phase A：Research Skill Layer 基础

交付：

- `research_skills/contracts.py`
- `research_skills/registry.py`
- `research_skills/adapters.py`
- `research_skills/third_party_skills.lock.yaml`
- `evaluation/test_research_skill_layer.py`

验收：

- 同一输入和版本产生稳定缓存键；
- API Key 等秘密字段不能进入结果、缓存键或 Trace；
- Adapter 保留上游正式状态和审计字段；
- 阶段不匹配时安全阻断；
- P1 PARTIAL、P2 门禁、P3 证据不足和 P4 蓝图确认状态不能被包装成成功；
- 现有 P1–P4 回归测试继续通过。

### Phase B：Discovery Loop

状态：第一版已完成（2026-08-23）。

交付：五视角 SearchPlan、稳定标识去重、引文图谱候选、引用校验和饱和度报告。

约束：图谱扩展只扩大 Discovery Space；所有候选重新进入现有 P1 Selection Space。

### Phase C：Gap Falsification

状态：第一版已完成（2026-08-23）。

交付：对每个候选空白执行反例检索、已有解决方案检索、替代解释审计，并把结果绑定到 Claim Store。

约束：继续使用当前至少两篇摘要或全文证据门禁；3/5 篇只可作为增强等级，不替换现有最低门槛。

### Phase D：全文证据 Sidecar

状态：D-1客户端、解析层和真实运行时验收均已完成（2026-08-23）。

先接 GROBID，再接 PaperQA2。主服务没有配置 sidecar 时必须返回明确的未配置或阻断状态，不回退到题名级正式证据。

D-1已交付：

- 可选GROBID健康、版本和`processFulltextDocument`客户端；
- PDF类型、大小和签名校验；
- TEI句子、章节、页码与坐标解析；
- 全文span转换为Evidence Matrix并通过Claim Store校验；
- 原PDF、原始TEI和本地路径不进入Skill输出；
- 未配置、服务不可用、空结果和失败状态不被包装成成功；
- 12项专项测试；
- Docker Desktop 4.87.0、WSL 2.7.12.0和GROBID 0.9.0真实运行时验收；
- 镜像digest、回环端口、健康状态和真实PDF证据审计记录。

D-1运行时结果：GROBID 12个模型加载、0失败；真实PDF产生126条全文证据句、7个章节锚点和126个页码锚点，Claim Store绑定有效；未持久化原PDF/原始TEI，未发生题名降级。

D-2（PaperQA2）已完成（2026-08-23）：固定`v2026.08.12`/Apache-2.0，在隔离Python 3.12环境中只调用`sparse` embedding与`Docs.retrieve_texts`。输入仅限P1 direct allowlist中的摘要/全文span；输出仅为`EVIDENCE_CANDIDATE_ONLY`，未知或越权span由主进程拒绝。worker不继承API Key，不允许PDF解析、外部论文搜索、LLM/agent、答案生成、Claim生成或研究空白裁决。

D-2真实联合验收：GROBID产生的126条全文span进入PaperQA2受控检索，返回5条候选；首条候选成功绑定Claim Store。运行时77个依赖已冻结并记录SHA-256，未持久化检索文件。

### Phase E：受控开题和界面

补用户约束确认、提纲确认、项目执行任务卡，最后增加 Skill、Evidence、Saturation 和 Audit 面板。

Phase E已完成（2026-08-23）：确定性约束层落地为`proposal_workflow_controls.py`（10字段规范化+`constraint_hash`、按权重分配字数的提纲、含前置依赖与done_when的执行任务卡）；服务端`/api/proposal`只放行`formal=true`的P3正式空白并把Claim Store与三项确认标志传入P4 Provider；前端改为约束表单→约束确认→蓝图/提纲确认→逐节生成→人工复核的工作流并新增四审计面板。全量自动回归：知识库115项、Demo回归29项、JS语法通过。

Phase E本地界面验收（受控夹具，`tests/browser_acceptance_harness.py`）：夹具synthesis通过真实`build_evidence_matrix`+`EvidenceBoundResearchGapProvider`在显式标注的夹具论文上生成正式空白与Claim Store，P2→gap_candidates桥接仅存在于夹具，生产代码未改动；P4 Provider为真实代码并调用本地`fake_deepseek_server`（已补受控逐节生成分支）。浏览器实测通过：空表单被必填校验拦截；四道检查点依次呈现`PROPOSAL_NEEDS_USER_INPUT`→`USER_CONSTRAINT_CONFIRMATION_REQUIRED`（10项约束回显）→`PROPOSAL_PLAN_CONFIRMATION_REQUIRED`（蓝图8项+11节提纲合计12000字+11张任务卡）→`READY_FOR_HUMAN_REVIEW`（11节生成、Claim/引用/跨节一致性/任务卡审计全过、每节展示Claim·论文·证据层级绑定）；四面板桌面4列、390px窄屏单列且无横向溢出；「新建研究」重置清空工作流。验收中发现并修复重置后状态徽标残留「待人工复核」的前端偏差，修复后复跑全流程通过。未覆盖：真实P2链路（仍被P1门禁阻断，P3服务端整合属T05）与浏览器控制台错误计数（自动化不可读，以无失败请求与无错误UI代证）。全部夹具内容显式标注「受控测试/界面验收」，不得作为研究结论引用。

## 5. 第三方治理规则

1. 所有外部项目必须绑定准确仓库和 commit SHA；
2. 许可证、NOTICE、数据使用约束和网络访问范围必须记录；
3. 默认状态为 disabled；只有完成安全、许可证和回归审计后才能启用；
4. 外部服务不得接收 API Key 之外的秘密，也不得把秘密写入输出；
5. 不信任第三方 Prompt 或文档中的运行指令；
6. Sidecar 故障必须映射为 PARTIAL、BLOCKED 或 FAILED，不能伪装成完整结果；
7. 外部项目升级必须修改锁文件版本并重新执行回归测试。

## 6. 提交顺序

```text
feat/research-skill-contracts
→ feat/research-discovery-loop
→ feat/gap-falsification
→ feat/fulltext-evidence-sidecars
→ feat/research-workflow-ui
```

每轮单独提交、单独回归；未通过的阶段不被后续能力掩盖。
