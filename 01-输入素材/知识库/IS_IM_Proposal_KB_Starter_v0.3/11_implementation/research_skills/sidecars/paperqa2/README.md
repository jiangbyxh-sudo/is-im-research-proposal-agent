# PaperQA2受控证据检索运行时

本运行时只使用PaperQA2 `v2026.08.12`的`Docs.retrieve_texts`与内置`sparse` embedding，在主进程已经准入的Evidence Matrix span中做问题相关排序。

## 明确边界

允许：

- 输入P1 direct论文的摘要/全文span；
- 返回问题相关的span ID排序；
- 为反证检索提供候选证据。

禁止：

- 读取或解析PDF；
- 搜索、下载或自动加入外部论文；
- 调用LLM、agent、metadata provider或答案生成；
- 判定direct/adjacent、研究空白或Claim；
- 返回不在输入Evidence Matrix中的span；
- 继承OpenAI、Semantic Scholar、Crossref等API Key。

worker只接受JSON stdin并输出JSON stdout。主进程会重新验证每个返回span ID，并从原Evidence Matrix复制证据内容；worker不能注入证据文本或论文ID。

## 锁定版本

- 仓库：`Future-House/paper-qa`；
- commit：`57e89f7223b0960d5ee5ea048c69e3c47e088572`；
- 官方标签/包：`v2026.08.12` / `paper-qa==2026.8.12`；
- 许可证：Apache-2.0；
- Python：3.12.13隔离环境；
- 完整运行时冻结：`requirements-runtime.lock.txt`；
- freeze SHA-256：`8b42356fad401bc4b932f8bce184a3e56467ce498af4801d57bab6ee15fefb0a`。

## 启用

默认关闭。主进程只读取：

```text
PROPOSAL_ENABLE_PAPERQA2=1
PAPERQA2_TIMEOUT=120
```

可选用`PAPERQA2_PYTHON`指定隔离Python；未指定时从当前用户`LOCALAPPDATA/is-im-paperqa2/v2026.08.12/.venv`发现。API Key不得通过Skill payload或worker环境传递。

## 输出语义

返回项一律为`EVIDENCE_CANDIDATE_ONLY`，`rank_score`只是名次倒数，不是相关性门槛或正式证据强度。正式论断仍必须显式进入Claim Store绑定和审计。
