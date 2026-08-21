# P0 · 完整 Trace 索引

## Trace 覆盖

| 类别 | 数量 | 目录/文件 |
|---|---:|---|
| 61 方向实网覆盖 | 61 | `traces/coverage/FIX-COVERAGE-001.json` … `FIX-COVERAGE-061.json` |
| 固定语料五次稳定性 | 5 | `traces/stability/FIX-STABILITY-001-RUN-1.json` … `RUN-5.json` |
| 挑战题 | 7 | `traces/challenges/CHALLENGE-*.json` |
| 开题生成 | 1 | `traces/proposal/FIX-PROPOSAL-001.json` |
| 合计 | 74 | `traces/` |

## 三条关键完整链路

1. 成功检索：`traces/coverage/FIX-COVERAGE-001.json`
   - 包含方向输入、版本、双语查询计划、每本期刊请求、候选量、过滤、论文输出、耗时和错误。
2. Provider 失败恢复：`traces/challenges/CHALLENGE-CROSSREF-429.json`
   - 记录 429、`Retry-After=2`、两次尝试、动态限流头和恢复结果。
   - 另有终止性超时：`CHALLENGE-PROVIDER-TIMEOUT.json`，结果为 0 且没有伪造论文。
3. 证据不足阻断：`traces/challenges/CHALLENGE-INSUFFICIENT-EVIDENCE.json`
   - 输入仅 4 篇，模型未调用，方向与空白均为空，状态为 `SYNTHESIS_INSUFFICIENT_EVIDENCE`。

## 模型链路

- 五次稳定性 Trace 保存固定语料哈希、模型/Prompt 版本、完整分组和研究空白输出、Token、耗时、错误及已知缺失能力。
- 开题 Trace 保存所选空白/创新、完整报告与指导输出、模型/Prompt/Rubric 版本、Token、耗时及缺失的 claim audit/一致性矩阵。
- 模型提供方价格表未配置，货币成本字段为 `null`；Token 已完整保存，不能把未知成本解释为零成本。
- 密钥仅存在服务进程内存，所有 Trace 和报告均不保存或回显密钥。
