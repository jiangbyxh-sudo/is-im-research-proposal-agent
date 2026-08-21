# 动态论文检索配置

## 当前实现

- 主发现源：Crossref REST API；
- 期刊门禁：本地 `journal_registry.json`；英文默认UTD24/FMS 2025 A/B，中文默认FMS T1/T2、CSSCI 2025–2026来源刊或北大核心2023；
- 查询顺序：研究方向 → 来源分组 → 期刊池 → 带ISSN的合格期刊 → Crossref期刊端点；
- 时间窗口：当前年份及此前四个日历年；
- 输出证据：DOI、规范期刊名、期刊等级、查询时间、查询式、返回数、排除原因；
- 质量控制：DOI/题名去重，排除撤稿、更正与低相关记录，不足时保留中英文独立缺口。
- 中文检索：默认启用Crossref期刊端点；补充期刊已进入资格库，但只有ISSN且Crossref精确匹配成功的期刊会发起查询，不伪造元数据补数。
- 五方向/空白综合：DeepSeek仅接收已通过期刊白名单与Crossref核验的论文元数据；模型输出再由代码校验证据ID、DOI、方向数量和论文计数。

运行时注册表由 `build_journal_registry.py` 生成。目前包含179本版本化期刊记录（英文68、中文111）；91本有ISSN，默认资格池中Crossref可直接检索41本英文期刊和3本中文期刊。新增中文名单扩大了资格与路由覆盖，但Crossref中文元数据覆盖仍是独立限制。

## 环境变量

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `PROPOSAL_DYNAMIC_PROVIDER` | `crossref` | 设为 `disabled` 可关闭动态检索 |
| `PROPOSAL_CROSSREF_MAILTO` | 空 | Crossref联系邮箱；建议生产环境配置，不写入项目 |
| `PROPOSAL_RETRIEVAL_TIMEOUT` | `18` | 单次HTTP请求超时秒数 |
| `PROPOSAL_ENABLE_CHINESE_RETRIEVAL` | `1` | 启用通过本地资格门禁且Crossref可检索的中文期刊 |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek调用凭据；仅从进程环境读取，严禁写入项目、日志或截图 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI兼容接口根地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | 证据综合模型 |
| `DEEPSEEK_TIMEOUT` | `90` | 单次综合请求超时秒数 |

示例：

```powershell
$env:PROPOSAL_CROSSREF_MAILTO = "your-address@example.edu"
python .\server.py
```

安全注入DeepSeek密钥（不会保存到文件）：

```powershell
$proposalSecureKey = Read-Host "DeepSeek API Key" -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new("", $proposalSecureKey).Password
python .\server.py
```

模型只做主题聚类与研究空白候选综合，不承担论文发现、期刊等级判断或引用校验。当前只具备题名级元数据时，所有空白必须标记为“待全文验证”；未知论文ID、未知DOI和证据不足两篇的空白会被代码丢弃。

本地页面也提供密码输入框。该入口只把密钥保存到当前Python服务进程的环境中，不写入文件、不回显，输入字段在提交前即清空；点击“清除”或重启服务都会移除配置。页面固定使用官方地址和 `deepseek-v4-pro`，不接受任意第三方API地址。

## 刷新期刊注册表

在知识库根目录运行：

```powershell
python .\11_implementation\build_journal_registry.py --mailto "your-address@example.edu"
```

脚本用本地等级文件决定资格，只使用Crossref解析或验证ISSN；Crossref不能反向决定期刊等级。

## 已知缺口

补充库已并入CSSCI 2025–2026来源刊、北大核心2023和中科院2025 SSCI 1/2区。三套体系独立存储：CSSCI扩展版不等同来源刊，CAS只作英文可选扩展且不改变默认UTD/FMS范围。Crossref当前只能直接查询3本默认合格中文期刊；后续仍需在同一 `PaperDiscoveryProvider` 边界接入创建者拥有合法权限的CNKI、万方或其他中文数据库，缺少合法接口时必须明确报告缺口。

OpenAlex可作为后续元数据增强源，但当前官方接口采用API Key与用量额度，因此本版本未把密钥写入项目，也未将其设为无凭据的隐式兜底。
