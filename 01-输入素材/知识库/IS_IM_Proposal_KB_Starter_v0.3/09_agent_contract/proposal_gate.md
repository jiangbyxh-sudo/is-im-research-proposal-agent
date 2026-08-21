# 开题报告门禁

## PASS 条件

```text
scope_verified == true
journal_rank_verified == true
paper_source_verified == true
paradigm_coverage_verified == true
len(selected_gap_ids) >= 1
len(selected_innovation_ids) >= 1
proposal_context.schema.json validates
```

## FAIL 行为

- 缺选择：返回候选空白/创新点，不写开题。
- 缺范式：列出缺失知识，现场搜官方资源，等待验证。
- 缺证据：指出哪项判断证据不足，不补写。
- 期刊/论文无法验证：移除记录，重新计算数量。

## 禁止的绕过

不得把用户说“继续”“先写一个看看”解释为选择空白和创新点；必须记录明确的ID或可唯一映射的选项。
