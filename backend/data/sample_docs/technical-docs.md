# 来画智能创作平台技术文档

## 1. 总体架构

平台由接入层、业务服务、AI 服务、媒体处理服务和数据层组成。接入层提供 HTTPS API、WebSocket 和静态资源 CDN；业务服务负责组织、权限、项目、模板和素材元数据；AI 服务负责脚本生成、语音合成和数字人驱动；媒体处理服务负责转码、合成、编码和成片质检。

核心数据存储在 MySQL，项目快照和审计事件写入对象存储，缓存与任务幂等键使用 Redis，检索服务使用向量数据库。渲染任务通过消息队列分发，任务状态以数据库记录为准，消息只负责触发，不作为最终状态来源。

## 2. 环境与部署

SaaS 环境的基础域名是 https://api.laihua.example.com，WebSocket 地址是 wss://api.laihua.example.com/ws/v1/events。私有化环境由交付团队分配域名，客户应通过环境变量读取 base_url，不要在代码中写死 SaaS 域名。

私有化部署包含 api、worker-render、worker-media、mysql、redis、object-storage 和 vector-db 等组件。生产环境至少部署两个 API 副本和两个渲染工作节点。渲染节点需要 GPU 时，应保证驱动版本与交付包中的 CUDA 运行时匹配。

服务健康检查分为两层：/health/live 只检查进程是否存活，/health/ready 检查数据库、Redis、对象存储和消息队列是否可用。负载均衡应使用 ready 探针，避免把请求转发到依赖未就绪的实例。

## 3. 鉴权与会话

API 使用 OAuth 2.0 风格的 Bearer Token。客户端先通过 client_id 和 client_secret 获取 access_token，access_token 有效期 2 小时。refresh_token 有效期 30 天，每次刷新会轮换 refresh_token，旧 refresh_token 立即失效。

请求头必须包含 Authorization 和 X-Request-Id。X-Request-Id 由客户端生成，建议使用 UUID。服务端会在响应头原样返回该值，并在日志、审计和异步任务中贯穿同一个 request_id，便于跨服务排障。

服务端时间与客户端时间偏差超过 5 分钟时，签名校验可能失败。NTP 同步是部署检查项。多实例环境必须共享同一套 JWT 公钥或密钥，不能在单个副本内随机生成。

## 4. 素材接入管道

素材上传采用预签名 URL。客户端先调用创建上传会话接口，拿到 upload_url 和 asset_id，再使用 HTTP PUT 上传文件内容。预签名 URL 默认 15 分钟有效，分片上传的每个分片 URL 单独签名。

上传完成后，客户端调用 complete 接口通知服务端合并分片。服务端随后执行病毒扫描、媒体探测、转码和封面抽帧。素材状态从 uploading 变为 processing，最终进入 ready 或 failed。

转码规则：

- 视频统一生成 H.264 MP4 预览文件和原始文件索引。
- 音频统一生成 AAC 预览，原始 WAV 保留在冷存储。
- 图片生成多尺寸缩略图，保留原始文件用于最终渲染。
- SVG 需要经过安全清洗，禁止脚本和外部资源引用。

处理失败时，error_code 会区分 unsupported_codec、corrupted_file、virus_detected、quota_exceeded 和 internal_error。corrupted_file 不建议自动重试，应提示用户重新导出源文件。

## 5. 渲染任务生命周期

渲染任务通过 POST /v1/render/jobs 创建。创建请求支持 Idempotency-Key，服务端在 24 小时内对相同幂等键返回同一任务。幂等键只保证创建不重复，不保证渲染结果一定成功。

任务状态机：

1. queued：任务已持久化，等待调度。
2. preprocessing：检查项目快照、素材和模板依赖。
3. rendering：执行时间线合成和数字人驱动。
4. encoding：编码为目标格式并执行质量检查。
5. succeeded：成片可下载。
6. failed：不可恢复错误，需要查看 error_code。
7. canceled：用户或管理员终止。

状态只能向前流转。succeeded、failed 和 canceled 是终态。客户端不要在 failed 后继续轮询同一个任务，应该根据 error_code 决定修复项目后创建新任务。

渲染任务默认最长执行 2 小时。超时后任务进入 failed，error_code 为 RENDER_TIMEOUT。企业版默认并发 8 个任务，旗舰版 32 个；私有化环境的并发数由部署配置决定。

## 6. WebSocket 事件

WebSocket 用于推送素材处理、渲染进度、审批和成员权限变更事件。连接地址为 /ws/v1/events，连接时通过 query 参数 access_token 鉴权。生产环境必须使用 wss。

连接默认空闲超时为 10 分钟。客户端应每 30 秒发送一次 ping，服务端返回 pong。断线后使用指数退避重连，初始等待 1 秒，最大等待 30 秒，并在重连请求中携带原 request_id 和 last_event_id。

事件推送可能重复，客户端必须按 event_id 去重。事件可能乱序到达，渲染进度应以 event.sequence 较大者为准。断线期间的事件可以通过 GET /v1/events?after_event_id=... 补拉，默认保留 24 小时。

错误码 4010 表示鉴权过期，应刷新 token 后重连；4011 表示连接频率超限；4012 表示订阅主题不存在。收到 4010 时不要立即高频重连，应先完成 token 刷新。

## 7. 存储与数据保留

对象存储分为热存储和归档存储。项目快照、最近 30 天的成片和预览文件放在热存储；原始素材和超过 30 天的成片可以转归档。归档文件下载前需要解冻，解冻通常需要 1 到 5 分钟。

数据库只保存对象键，不保存二进制文件。删除任务采用异步清理：先标记 deleted_at，再由清理任务删除对象存储文件。审计记录和计费记录按合规要求保留，不随项目删除而立即清除。

默认备份策略为 MySQL 每日全量加每小时增量，对象存储开启版本控制。私有化部署应至少保留 14 天备份。恢复演练每季度一次，恢复目标 RPO 不超过 1 小时，RTO 不超过 4 小时。

## 8. 可观测性

每条结构化日志包含 timestamp、level、service、request_id、trace_id、user_id、org_id、route、latency_ms、status_code 和 error_code。禁止在日志中记录 access_token、refresh_token、client_secret 和原始素材内容。

关键指标包括 API P95 延迟、渲染排队时长、渲染成功率、素材处理失败率、WebSocket 重连率、对象存储错误率和队列积压量。渲染成功率按 15 分钟窗口计算，低于 95% 时应触发告警。

追踪链路从 API 网关开始，经过任务创建、消息队列、渲染 worker 和编码器。异步任务必须把 trace_id 写入任务载荷，否则跨进程链路会断开。

## 9. 故障排查

### 9.1 401 鉴权失败

先确认 Authorization 头没有多余空格，再检查 token 是否过期。4010 表示过期或签名错误，4011 表示刷新频率超限，4030 表示 token 有效但无权限。不要把所有 401 都当作账号密码错误。

### 9.2 素材一直 processing

检查上传会话是否已 complete，对象存储是否收到完整文件，媒体 worker 是否有积压。若超过 30 分钟仍为 processing，可使用 request_id 查询媒体服务日志。不要重复创建上传会话，否则可能产生多个孤儿对象。

### 9.3 渲染一直 queued

查看 queue_reason。concurrency_limit 表示套餐并发已满，template_maintenance 表示模板维护，capability_not_enabled 表示未开通 4K 或数字人能力。排队任务不会因为等待而扣费，成功编码后才计费。

### 9.4 WebSocket 频繁断线

检查客户端是否每 30 秒发送 ping，代理是否把空闲连接在 60 秒内断开，访问令牌是否在连接期间过期。反向代理需要允许 Upgrade 和 Connection 头，并将读超时设置为大于 90 秒。

### 9.5 下载地址 403

下载地址默认 24 小时过期。过期后调用重新签发接口获取新地址。若地址未过期仍返回 403，检查请求是否来自被 IP 白名单限制的网络，以及当前用户是否仍有项目查看权限。

## 10. 安全要求

生产接入必须使用 TLS 1.2 及以上。client_secret 只能保存在服务端密钥管理系统，不能写入前端代码、移动端包或公开仓库。服务端应对回调进行签名校验，并校验时间戳偏差不超过 5 分钟。

外链分享支持密码、有效期和下载次数限制。默认有效期 7 天，最长 30 天。包含数字人定制形象或未公开品牌素材的项目，管理员可以禁止外链分享，只允许组织内成员访问。

所有用户输入在进入脚本生成和数字人驱动前都要经过内容安全检查。命中高风险策略时返回 4035，低风险内容进入人工复核队列。安全审核结果和操作者信息写入审计日志。
