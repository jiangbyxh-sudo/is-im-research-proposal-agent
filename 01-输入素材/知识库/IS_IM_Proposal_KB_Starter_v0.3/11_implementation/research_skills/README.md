# Research Skill Layer

本目录只包装现有 P1–P4 产品逻辑，不重新定义论文相关性、聚类成员、研究空白或开题门禁。

## 组件

- `contracts.py`：统一 Context、Descriptor、Result、缓存键和脱敏；
- `registry.py`：注册、阶段检查、秘密字段阻断、确定性缓存和可选 Trace；
- `adapters.py`：P1–P4 薄适配器；
- `third_party_skills.lock.yaml`：外部项目版本和允许边界，默认不启用。

Phase B 的 P1 Discovery Space 还提供：

- `p1.multi_perspective_search_plan`：现象、理论、机制、情境、方法五视角查询；
- `p1.citation_graph_expansion`：引文前向/后向候选；
- `p1.citation_verification`：稳定标识与规范元数据核验；
- `p1.retrieval_saturation`：重复率与新增 direct 产出的建议性饱和度。

这些技能不输出正式 `papers`。引文候选统一标记为 `P1_REEVALUATION_REQUIRED`。

Phase C 提供：

- `p3.gap_falsification_plan`：生成直接解决、矛盾结果、替代解释和边界条件查询；
- `p3.gap_falsification_evaluation`：只接受P1 direct且绑定摘要/全文span的反证发现。

反证裁决返回降级或收窄建议，不自动改写原始Gap或Claim Store。

Phase D-1 提供：

- `p3.fulltext_evidence_extraction`：通过可选GROBID sidecar把合法PDF转换为句级全文Evidence Matrix；
- GROBID只负责结构化、章节/页码定位和句子切分，不决定论文相关性、研究空白或Claim；
- 未配置、服务不可用、解析为空和解析失败均保留明确状态，不回退为题名级正式证据；
- Provider不复制原PDF、不持久化原始TEI，也不在Skill结果中返回本地文件路径。

运行配置和容器边界见`sidecars/grobid/README.md`。未传入`fulltext_provider`时，Registry不注册该可选Skill。

Phase D-2 提供：

- `p3.question_evidence_retrieval`：只在P1 direct论文的摘要/全文span中做问题相关排序；
- PaperQA2固定为`v2026.08.12`隔离Python 3.12运行时，仅调用`sparse` embedding与`Docs.retrieve_texts`；
- worker不接收API Key，不调用PDF解析、外部论文搜索、LLM、agent、答案生成或元数据服务；
- 返回项只是`EVIDENCE_CANDIDATE_ONLY`，必须重新绑定Claim Store；
- 主进程拒绝任何未知、重复、非allowlist或非正式证据span。

运行边界、依赖冻结和验收记录见`sidecars/paperqa2/`。

## 使用示例

```python
from research_skills.adapters import build_default_registry
from research_skills.contracts import ResearchSkillContext

registry = build_default_registry(p1_provider=paper_provider)
result = registry.run(
    "p1.paper_discovery",
    {
        "selected_direction_id": "topic_ai_enabled_information_systems",
        "research_direction": "AI-enabled information systems",
        "chinese_count": 10,
        "english_count": 20,
    },
    ResearchSkillContext(stage="P1"),
)
```

API Key 必须通过既有进程环境或 provider 构造过程配置，不能放入 Skill payload。若 payload 出现秘密字段，Registry 返回 `SECRET_INPUT_REJECTED`。

`SkillRunStatus` 只表达统一运行层状态；`upstream_status` 和原始上游输出始终保留。例如 `RETRIEVAL_PARTIAL` 只能映射为 `PARTIAL`，不能映射为 `COMPLETE`。
