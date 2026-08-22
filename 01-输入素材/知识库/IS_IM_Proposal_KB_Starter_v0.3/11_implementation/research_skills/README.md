# Research Skill Layer

本目录只包装现有 P1–P4 产品逻辑，不重新定义论文相关性、聚类成员、研究空白或开题门禁。

## 组件

- `contracts.py`：统一 Context、Descriptor、Result、缓存键和脱敏；
- `registry.py`：注册、阶段检查、秘密字段阻断、确定性缓存和可选 Trace；
- `adapters.py`：P1–P4 薄适配器；
- `third_party_skills.lock.yaml`：外部项目版本和允许边界，默认不启用。

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
