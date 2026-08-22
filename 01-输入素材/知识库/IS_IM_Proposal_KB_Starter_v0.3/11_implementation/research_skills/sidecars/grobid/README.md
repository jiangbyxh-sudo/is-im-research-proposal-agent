# GROBID全文证据Sidecar

本Sidecar仅把本地PDF转换为TEI XML，随后由主进程提取句级全文证据、章节和页码锚点。它不拥有P1 direct判定、P2论文归属、P3研究空白或Claim Store的决定权。

## 当前运行状态

- 客户端、TEI解析器、Evidence Matrix转换和离线测试已实现；
- 当前开发机未检测到Docker，因此未拉取、安装或启动GROBID容器；
- 未完成真实容器健康检查和真实PDF解析前，只能标记“客户端链路完成”，不能标记“全文服务已部署”。

## 受控启用

服务由运维人员独立部署。正式启用前必须锁定镜像digest，记录许可证与升级审计；不要使用浮动`latest`标签。主进程只读取以下环境变量：

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

## 数据边界

- PDF只在请求期读取并发送给配置的GROBID地址；Provider不创建PDF副本；
- 原始TEI只在内存解析，不由Provider持久化；
- Skill输出不包含PDF路径、PDF字节或原始TEI；
- Evidence Matrix仅保留证据句、paper ID、章节、页码、坐标和不可逆哈希；
- 若GROBID部署在远端，须在上线前另行完成传输、数据驻留和访问控制审计。
