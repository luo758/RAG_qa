# DocFlow 智文通

企业级多知识库 RAG 技术文档助手。用户上传技术文档后，可以基于选定的知识库进行自然语言问答，并获得流式回答和文档引用。

## 项目背景

项目面向内容创作 SaaS 场景，服务于产品、研发、客服和运营人员。平台把分散的产品手册、技术文档和 API 参考统一接入知识库，解决全文搜索找不到自然语言答案、文档权限复杂、回答缺少依据等问题。

系统按部门级试点设计，目标覆盖 30 名左右内部用户，支持超级管理员、管理员和员工三级权限。员工默认不可见知识库，授权后可查看和问答，拥有上传权限也不能修改或删除已有内容。

## 技术栈

- 前端：Vue 3 + TypeScript + Vite + Pinia + Element Plus + Lucide
- 后端：FastAPI + SQLAlchemy
- 关系数据库：本机 MySQL 8.0.12（phpStudy）
- 向量数据库：Milvus 2.5
- 大模型：通义千问 `qwen-max`，兼容 DashScope OpenAI API
- 检索：本地 BGE-M3 稠密向量 + BM25 + BGE-reranker-v2-m3 重排
- 缓存：Redis Embedding 缓存、问答缓存和知识库版本号
- 测试：pytest + FastAPI TestClient

## 功能

- 登录、注册和图形验证码
- JWT 用户认证
- 超级管理员、管理员、员工三级角色与知识库 ACL
- 管理员创建、编辑、删除知识库，并配置员工查看/上传权限
- 员工默认不可见，授权后可检索；有上传权限仍不能修改或删除内容
- 预置产品手册、技术文档、API 参考三类离线资料
- PDF、PPTX、Markdown、TXT、图片上传解析
- 可配置切块大小、重叠大小和检索模式
- 文档块预览、编辑、删除和重新向量化
- 多知识库联合检索
- 对话会话创建、重命名和删除
- 模型、温度、TopP、输出 Token、历史轮数配置
- SSE 流式回答与 Redis 语义缓存命中
- 文档引用和会话历史
- 日志输出到控制台和 `backend/data/logs/backend.log`

## 试点规模与成本

### 当前 POC 规模

当前仓库内已完成小规模闭环验证：

- 1 个“企业离线知识库”
- 3 份核心文档：产品手册、技术文档、API 参考
- 13,538 字，切分为 19 个 chunk，写入 19 条 Milvus 向量
- 3 个演示账号：超级管理员、管理员、员工

### 目标试点规模

| 项目 | 设计规模 |
| --- | --- |
| 文档数量 | 50 到 100 份产品手册、技术文档和 API 参考 |
| 文档块 | 约 2,000 个 chunk |
| 用户数量 | 约 30 名内部用户 |
| 同时在线 | 3 到 8 人 |
| 评测问题 | 50 到 100 条 |
| 知识库 | 可按产品、技术、API 拆分，也可统一为一个知识库 |

2,000 条 1024 维向量的原始大小约 8.2 MB，加上 Milvus 索引、MySQL 文本、Redis 缓存和备份，整体存储通常小于 1 GB。空间主要被本地 BGE-M3 与 Reranker 模型占用，两者合计约 4.3 GB。

部署建议：

- 一台 8 核 16 GB 服务器承载应用、MySQL、Redis 和单机 Milvus，或使用两台 4 核 8 GB 服务器拆分部署。
- 存储预留 50 到 100 GB。
- Milvus 使用 Standalone 单机模式即可，2,000 个 chunk 不需要分布式集群。
- BGE-M3 与 Reranker 优先使用 CPU；需要降低重排延迟时可配置 8 GB 显存 GPU。

成本估算，不含研发人力：

| 成本项 | 月成本估算 |
| --- | --- |
| 云服务器和存储 | 800 到 1,800 元 |
| Qwen API 调用 | 300 到 1,200 元 |
| Redis、Milvus 自建 | 已包含在服务器成本中 |
| 合计 | 约 1,000 到 3,000 元/月 |

如果复用公司现有服务器，云资源增量可以接近 0。前期建议按 2 到 3 人、4 到 6 周估算研发投入，主要工作量在文档清洗、权限梳理、测试集建设和检索效果调优。

以上成本为试点容量估算，不是已经发生的生产账单；实际金额取决于云厂商、模型调用量、文档清洗方式和部署环境。

## 目录

```text
docflow/
├── backend/
│   ├── app/
│   │   ├── routers/       # 认证、知识库、对话 API
│   │   ├── services/      # 解析、切块、Embedding、Milvus、RAG
│   │   ├── models.py
│   │   └── main.py
│   ├── data/
│   │   ├── sample_docs/   # 测试技术文档
│   │   └── uploads/       # 用户文档
│   └── tests/
├── frontend/              # Vue 3 应用
├── scripts/
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

## 启动基础设施

先确保本机 phpStudy MySQL 已启动，并创建 `docflow` 数据库；Milvus 依赖使用 Docker：

```powershell
cd docflow
docker compose up -d etcd minio milvus
docker compose ps
```

服务端口：

- MySQL：`3306`
- Milvus：`19530`
- MinIO：`9000`，控制台 `9001`
- etcd：`2379`

## 配置

```powershell
Copy-Item .env.example .env
```

至少修改：

```text
JWT_SECRET=<32 位以上随机字符串>
```

通义千问密钥会依次读取 `QWEN_API_KEY`、`DASHSCOPE_API_KEY`、`API_KEY`。
当前项目已支持系统环境变量中的 `DASHSCOPE_API_KEY`。

默认模型：

```text
QWEN_CHAT_MODEL=qwen-max
QWEN_EMBEDDING_MODEL=text-embedding-v3
QWEN_VISION_MODEL=qwen-vl-max
```

图片解析使用 `qwen-vl-max` OCR，因此需要有效的 DashScope API Key。

本地 BGE 与 Redis 配置：

```text
EMBEDDING_PROVIDER=bge_m3
BGE_M3_MODEL=BAAI/bge-m3
BGE_DEVICE=cpu
RERANKER_ENABLED=true
BGE_RERANKER_MODEL=BAAI/bge-reranker-v2-m3
REDIS_URL=redis://127.0.0.1:6379/0
```

如果 Redis 开启了密码认证，使用 `redis://:<password>@127.0.0.1:6379/0` 配置，并把真实密码放在 `.env` 或部署环境的密钥管理系统中。不要将真实密码提交到 Git。

## 启动后端

```powershell
cd docflow
uv sync
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

接口文档：`http://127.0.0.1:8000/docs`

健康检查：`http://127.0.0.1:8000/health`

## 启动前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

访问：`http://127.0.0.1:5173`

Vite 会把 `/api` 代理到 `http://127.0.0.1:8000`。

## 示例文档

生成 Markdown、PDF、PPTX 和图片示例：

```powershell
uv run python scripts\create_sample_docs.py
```

文件位于 `backend/data/sample_docs`。

## 初始化离线知识库

脚本会幂等创建三个账号、一个“企业离线知识库”，并把以下资料切块、向量化后写入 MySQL 和 Milvus：

- `product-manual.md`：来画智能创作平台产品手册
- `technical-docs.md`：架构、部署、素材管道、渲染任务和故障排查
- `api-reference.md`：鉴权、项目、素材、渲染、WebSocket、Webhook 和错误码

```powershell
uv run python scripts\seed_offline_kb.py
```

重复运行不会重复插入文档。已有 `ready` 文档会跳过，失败或残缺文档会重新入库。

本地演示账号：

| 角色 | 账号 | 密码 |
| --- | --- | --- |
| 超级管理员 | `superadmin` | `SuperAdmin@2026` |
| 管理员 | `admin` | `Admin@2026` |
| 员工 | `employee` | `Employee@2026` |

员工已获得“企业离线知识库”的查看和上传权限。生产环境必须通过环境变量覆盖默认密码。

## 测试

```powershell
uv run pytest backend/tests -q
cd frontend
npm run build
```

测试环境使用内存 SQLite、确定性 Embedding、Fake LLM 和内存向量库，仅用于隔离测试。生产运行配置固定为 MySQL、Milvus 和通义千问，不会自动降级到这些测试实现。

## 主要 API

- `GET /api/auth/captcha`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET/POST /api/knowledge-bases`
- `POST /api/knowledge-bases/{id}/documents`
- `GET /api/documents/{id}`
- `PATCH/DELETE /api/chunks/{id}`
- `GET/POST /api/sessions`
- `PATCH/DELETE /api/sessions/{id}`
- `GET /api/sessions/{id}/messages`
- `POST /api/chat/stream`

## 生产注意事项

- 必须修改 `JWT_SECRET` 和 MySQL 默认密码。
- 必须通过 HTTPS 部署。
- 本机 MySQL 可直接用于开发；Milvus 使用 Docker Compose，生产环境应使用托管或高可用集群。
- 数据库结构当前由 SQLAlchemy 启动时自动建表，正式生产建议接入 Alembic 迁移。
- 图片 OCR 依赖通义视觉模型；没有 API Key 时会明确报错，不会返回伪造内容。



## 角色与知识库权限

- 超级管理员：管理全部知识库，并在“用户与权限”中设置管理员或员工。
- 管理员：创建、编辑、删除知识库和文档；为员工配置查看、上传权限。
- 员工：默认看不到知识库；只有 `can_view` 为真时才能检索和查看；只有 `can_upload` 为真时才能上传新文档。员工永远不能修改或删除已有文档和文档块。

权限由服务端统一校验，前端只负责隐藏不可用入口。检索接口会再次校验知识库访问权，避免绕过页面直接调用 API。

## 稳定性与可观测

### 当前实现版本

实现 Redis 不可用时缓存 fail-open、Qwen 与本地模型异常快速失败；文档处理维护 `processing/ready/failed` 状态和错误信息，知识库变更通过版本号使缓存失效；提供 `/health` 健康检查、滚动日志和异常记录，结合 19 项 pytest 回归测试保障核心链路可用性。

当前 `/health` 会返回服务状态、Embedding Provider、Reranker 开关和 Redis 实际可用性。日志同时输出到控制台和 `backend/data/logs/backend.log`，单文件 10 MB，保留 5 个备份。

### 生产化增强目标

为大模型调用增加超时、单次重试、熔断降级和首 token 前重试策略，依赖服务断连时快速失败；基于 Redis 令牌桶实现用户级和接口级限流，按问答、上传和检索链路隔离并发，配置 30 秒优雅停机；通过 `request_id` 贯穿结构化日志，采集 P50/P95/P99、通道占比、缓存命中率、429 次数、越权拦截数和 token 成本，并接入 Prometheus/Grafana 看板与告警阈值。

### 完成度与边界

| 能力 | 当前状态 |
| --- | --- |
| Redis fail-open | 已实现 |
| Qwen/本地模型异常快速失败 | 已实现基础错误返回 |
| 文档 processing/ready/failed 状态 | 已实现 |
| 知识库版本化缓存失效 | 已实现 |
| `/health` 基础健康检查 | 已实现 Redis 检查，未覆盖 MySQL/Milvus 深度探针 |
| 滚动日志与异常记录 | 已实现 |
| 19 项 pytest 回归 | 已实现 |
| 大模型超时、重试、熔断 | 未实现，属于增强目标 |
| 用户级/接口级限流 | 未实现，属于增强目标 |
| 问答、上传、检索并发隔离 | 未实现，属于增强目标 |
| 30 秒优雅停机 | 未实现，属于增强目标 |
| `request_id` 贯穿日志 | 未实现，属于增强目标 |
| P50/P95/P99、缓存命中率、token 成本 | 未实现，属于增强目标 |
| Prometheus/Grafana 与告警 | 未实现，属于增强目标 |

当前版本不能表述为“已实现生产级限流、熔断、优雅停机和 Grafana 监控”。这些能力需要在试点前补齐，并通过故障注入和压测验证。

## 容灾与兜底策略

项目当前是部门级试点，容灾目标优先保证“数据可恢复、故障可降级、不会因依赖异常产生越权或伪造答案”。单机 Docker 重启不属于完整容灾演练，正式试点仍需补齐备份恢复和故障注入记录。

### 数据责任边界

- MySQL：用户、角色、知识库、知识库权限、文档元数据、chunk 正文和会话记录的唯一业务数据源。
- 上传目录：用户上传的原始文件，必须和 MySQL 一样纳入备份。仅恢复 MySQL 无法恢复丢失的源文件。
- Milvus：派生向量索引，可由 MySQL 中的 `document_chunks` 重新生成，不作为唯一数据源。
- Redis：Embedding 和问答缓存，允许丢失；恢复后按访问逐步重建。
- BGE-M3 与 Reranker：本地模型缓存，可通过模型仓库重新下载。
- Qwen：外部推理服务，不可用时快速失败，不使用其他模型伪造答案。

### 运行期兜底

| 依赖故障 | 当前行为或目标策略 |
| --- | --- |
| Redis 不可用 | 已实现 fail-open，缓存关闭，问答和管理接口继续运行 |
| Qwen 不可用 | 返回 503 或 SSE error；已有缓存命中时仍可返回缓存答案 |
| BGE-M3 或 Reranker 加载失败 | 返回明确的模型不可用错误，不执行无向量检索的伪回答 |
| Milvus 不可用 | 目标策略为快速失败并返回明确错误，禁止跳过检索直接调用大模型 |
| 检索无命中 | 向模型提供“没有检索到相关内容”，要求明确回答信息不足，不编造 API 或参数 |
| MySQL 不可用 | 采用 fail-closed，不绕过用户、角色和权限校验继续服务 |
| 上传目录损坏 | 从备份恢复原始文件；缺失文件需要重新上传或从不可变对象存储恢复 |

MySQL 故障时宁可暂时不可用，也不能跳过权限校验返回数据。Redis 和 Milvus 属于可降级或可重建组件，但二者不能成为权限判断的依据。

### 备份与恢复

试点环境建议至少执行：

```text
MySQL：每日全量备份，开启 binlog 后支持 1 小时级恢复点
上传目录：每日增量备份，保留 14 天
配置与密钥：由部署环境或密钥管理系统单独保存，不进入 Git
Redis：不做业务备份
Milvus：保留重建脚本，必要时从 MySQL 重新向量化
```

恢复顺序：

```text
恢复环境变量与密钥
→ 恢复 MySQL
→ 恢复上传目录
→ 从 document_chunks 分批调用 BGE-M3 重建 Milvus 向量
→ 清空 Redis 派生缓存
→ 启动 FastAPI 与前端
→ 执行登录、角色权限、检索引用和问答回归
```

向量重建完成后必须校验：

```text
MySQL 中目标知识库的 chunk 数量 == Milvus 中对应 kb_id 的向量数量
```

当前离线知识库应恢复为 19 个 chunk 和 19 条向量。后续封装 `rebuild_vectors.py` 时，应按知识库分批读取、分批生成向量并支持断点续跑，避免一次加载全部文档导致内存峰值过高。

### 演练目标

对 50 到 100 份文档、约 2,000 个 chunk、30 名用户的试点，建议设置：

- RPO：不高于 24 小时；接入 MySQL binlog 后目标不高于 1 小时。
- RTO：不高于 4 小时。
- 恢复后验收：员工默认不可见、授权后可检索、越权请求被拒绝、引用可追溯。
- 故障注入场景：Redis 停止、Milvus collection 删除、MySQL 备份恢复、上传目录丢失、Qwen Key 失效和应用进程重启。

### 当前完成度

已完成 Redis fail-open、幂等离线知识库初始化、Docker Compose 中间件拉起、健康检查和端到端问答验收。完整的 MySQL 备份恢复、Milvus 重建脚本、上传目录恢复和 RPO/RTO 演练记录尚未落地，不能将“容器重启成功”表述为已经通过容灾测试。
