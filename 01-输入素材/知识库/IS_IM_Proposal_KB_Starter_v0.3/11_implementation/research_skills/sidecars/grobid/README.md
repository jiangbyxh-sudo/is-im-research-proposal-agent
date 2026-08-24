# GROBID全文证据Sidecar

本Sidecar仅把本地PDF转换为TEI XML，随后由主进程提取句级全文证据、章节和页码锚点。它不拥有P1 direct判定、P2论文归属、P3研究空白或Claim Store的决定权。

## 当前运行状态

- 客户端、TEI解析器、Evidence Matrix转换和离线测试已实现；
- 2026-08-23已在当前开发机完成Docker Desktop、WSL2和GROBID 0.9.0运行时验收；
- 镜像以digest锁定，端口只绑定`127.0.0.1:8070`；
- 健康检查12个模型加载、0失败；真实PDF提取126条全文span并通过Claim Store绑定；
- 可机读验收记录见`runtime-validation-2026-08-23.json`。

## 受控启用

服务由运维人员独立部署。正式启用前必须锁定镜像digest，记录许可证与升级审计；不要使用浮动`latest`标签。当前可复现配置位于`compose.yaml`，固定GROBID 0.9.0 CRF镜像digest并只绑定本机回环地址。主进程只读取以下环境变量：

```text
PROPOSAL_ENABLE_GROBID=1
GROBID_BASE_URL=http://127.0.0.1:8070
GROBID_TIMEOUT=120
```

默认`PROPOSAL_ENABLE_GROBID=0`。主服务不得自动安装Docker、拉取镜像或执行第三方仓库脚本。

## 健康与接口契约

启用前依次验证：

1. `GET /api/health`返回ready/up状态；
2. `GET /api/version`返回已审计版本；
3. `POST /api/processFulltextDocument`接受multipart PDF；
4. 请求固定启用`segmentSentences=1`和`teiCoordinates=s`；
5. 真实PDF结果至少含一个正文句级span，并可被`ClaimStore`校验。

503、超时、坏PDF、无正文句或非法TEI都必须返回显式阻断/失败状态。任何情况下都不得把题名、文件名或未解析PDF标成fulltext证据。

GROBID 0.9.0的`/api/version`响应为JSON；客户端必须以`application/json`读取，不能请求`text/plain`。该兼容性已由真实服务验收和回归测试覆盖。

## 数据边界

- PDF只在请求期读取并发送给配置的GROBID地址；Provider不创建PDF副本；
- 原始TEI只在内存解析，不由Provider持久化；
- Skill输出不包含PDF路径、PDF字节或原始TEI；
- Evidence Matrix仅保留证据句、paper ID、章节、页码、坐标和不可逆哈希；
- 若GROBID部署在远端，须在上线前另行完成传输、数据驻留和访问控制审计。
