from __future__ import annotations

from pathlib import Path


PRODUCT_MANUAL = '''# 来画智能创作平台产品手册

## 1. 产品定位

来画智能创作平台面向企业市场、品牌团队、培训部门和内容服务商，提供从脚本生成、素材组织、数字人配音、在线剪辑到批量渲染的一站式视频内容生产能力。平台同时支持浏览器工作台、开放 API 和私有化部署三种交付方式。

本文档适用于平台版本 3.6，覆盖企业版与旗舰版。免费版和专业版在并发任务、存储空间、导出规格方面存在差异，产品能力的公共部分以本文档为准。

## 2. 工作空间与角色

平台使用“组织 - 工作空间 - 项目”三级结构。一个组织可以创建多个工作空间，项目、素材、模板和成片归属于具体工作空间，不在工作空间之间自动共享。

系统内置四类角色：

- 超级管理员：管理组织、成员、账单、单点登录和全部工作空间。
- 工作空间管理员：管理本空间成员、模板、素材库和项目，但不能修改组织级账单。
- 编辑者：可以创建和编辑项目、上传素材、发起渲染，不能删除空间或调整成员角色。
- 审阅者：只能查看被授权的项目、添加评论和审批版本，不能修改时间线或导出源文件。

权限遵循最小授权原则。工作空间管理员必须显式邀请成员并分配角色，普通成员默认看不到未加入空间中的项目。项目级权限可以进一步限制审阅范围，但不会扩大组织级权限。

## 3. 核心功能

### 3.1 智能脚本

智能脚本支持根据主题、受众、时长和语气生成分镜脚本。单次输入的主题描述上限为 5000 字，生成的脚本正文上限为 20000 字。每次生成会返回三个候选版本，用户可以接受、重新生成或手工修改。

脚本不会自动发布，也不会直接消耗渲染额度。只有把脚本加入项目并提交渲染后，才会产生渲染任务和相应计费。

### 3.2 素材中心

素材中心支持视频、图片、音频、字体和品牌组件。视频支持 MP4、MOV、WebM；图片支持 PNG、JPG、WEBP、SVG；音频支持 MP3、WAV、AAC。单个文件默认上限为 2 GB，超大文件必须使用分片上传。

素材进入空间后先进行病毒扫描、转码和元数据提取。状态为 processing 时可以在列表中看到，但不能加入时间线；状态为 ready 后才可被项目引用。状态为 failed 的素材需要查看 error_code 后重新上传。

素材支持标签、文件夹和品牌色板。删除素材前系统会检查引用关系。被项目引用的素材不能直接物理删除，应先解除引用或改为归档。

### 3.3 模板与品牌套件

模板分为官方模板、组织模板和个人模板。组织模板由工作空间管理员发布，成员只能使用不能覆盖。品牌套件统一管理字体、Logo、主色、片头和片尾，启用后项目默认继承品牌套件，仍允许项目管理员覆盖单个元素。

模板更新不会自动改变已经创建的项目快照。编辑者如需使用新模板，应在项目设置中点击“同步最新模板”，系统会显示变更差异并创建新的项目版本。

### 3.4 数字人与语音

数字人支持预置形象和定制形象。预置形象可直接用于企业版项目；定制形象需要完成授权材料审核，审核通常需要 1 到 3 个工作日。单个数字人片段默认最长 10 分钟，旗舰版可以申请提升到 30 分钟。

语音合成支持普通话、英语、粤语和多种情绪风格。上传参考音频进行音色复刻时，必须取得声音权利人的书面授权。平台会在合成音频中写入不可感知的来源标识，便于审计和追溯。

### 3.5 在线剪辑与协作

时间线支持多轨视频、音频、字幕、贴纸和转场。项目每 15 秒自动保存一次，用户也可以在版本面板手工创建命名版本。默认保留最近 50 个版本，旗舰版可以保留 200 个版本。

多人同时编辑时采用元素级锁。某位成员正在调整字幕轨时，其他成员仍可编辑视频轨，但同一元素不能同时修改。审阅者添加的评论会绑定时间码和当前项目版本，项目更新后评论仍保留但会标记“已过期版本”。

### 3.6 渲染与导出

渲染任务支持 720p、1080p 和 4K。720p 与 1080p 面向全部付费套餐，4K 仅旗舰版开放。输出格式包括 MP4、MOV 和 GIF，MP4 默认使用 H.264 编码，MOV 可按项目设置使用 ProRes。

标准渲染任务的状态依次为 queued、preprocessing、rendering、encoding、succeeded。任务失败时状态为 failed，用户主动终止时为 canceled。任务成功后下载地址默认有效 24 小时，过期后可以重新签发，不需要重新渲染。

## 4. 套餐与限制

| 能力 | 免费版 | 专业版 | 企业版 | 旗舰版 |
| --- | --- | --- | --- | --- |
| 单个素材上限 | 200 MB | 1 GB | 2 GB | 2 GB |
| 空间存储 | 5 GB | 100 GB | 2 TB | 10 TB |
| 同时渲染任务 | 1 | 3 | 8 | 32 |
| 单项目协作者 | 3 | 10 | 50 | 200 |
| 4K 导出 | 不支持 | 不支持 | 不支持 | 支持 |
| 私有化部署 | 不支持 | 不支持 | 可选 | 可选 |
| 审计日志保留 | 7 天 | 30 天 | 180 天 | 365 天 |

套餐限制按组织计算。超出并发限制的任务不会失败，而是进入 queued 状态等待空闲渲染槽位。任务排队超过 24 小时仍未被调度时，系统会发送告警并保留任务。

## 5. 账号与安全

企业版支持密码登录、短信验证码和 SAML 2.0 单点登录。开启强制单点登录后，组织成员不能再使用密码直接登录。超级管理员可以配置 IP 白名单、登录时段和会话有效期。

普通成员的会话默认 12 小时无操作后失效。API access_token 的有效期是 2 小时，refresh_token 的有效期是 30 天。refresh_token 被吊销后，关联的 access_token 最迟在 5 分钟内失效。

平台对下载、外链分享和成员权限变更记录审计日志。日志包含操作者、时间、来源 IP、目标资源和 request_id。审计日志不可由工作空间管理员删除，只有组织超级管理员可以申请导出。

## 6. 常见问题

### 6.1 为什么素材上传成功但不能加入时间线

上传成功只表示文件已经写入对象存储，不代表处理完成。素材还需要完成转码和元数据提取。请在素材详情中查看 status，只有 ready 状态才能被项目引用。processing 状态通常需要几十秒到数分钟，超大视频会更久。

### 6.2 为什么渲染任务一直处于 queued

queued 表示任务已经创建但还没有获得渲染槽位。常见原因包括套餐并发已满、任务所需模板版本正在维护、4K 能力未开通。可以先查看 GET /v1/render/jobs/{job_id} 返回的 queue_reason 字段。

### 6.3 为什么 API 返回 4010

4010 表示 access_token 已过期或签名无效。access_token 有效期为 2 小时。客户端应使用 refresh_token 调用令牌刷新接口，然后使用新的 access_token 重试原请求。不要使用同一个过期令牌反复重试。

### 6.4 删除项目后能否恢复

管理员删除项目后进入回收站，默认保留 30 天。回收站中的项目不能继续渲染，但可以恢复。超过保留期后项目、时间线和派生文件会被永久清理。原始素材是否删除取决于素材是否仍被其他项目引用。

### 6.5 私有化部署是否支持离线运行

企业版和旗舰版支持私有化部署。基础渲染、素材管理和模板服务可以离线运行；智能脚本、语音合成和部分 AI 数字人能力是否可离线使用，取决于客户购买的模型授权包。未部署对应模型时，相关入口会显示“未启用”，API 返回 5030。

## 7. 版本兼容说明

平台 3.6 保留 v1 API 兼容。v1 的 POST /v1/render 接口已标记为弃用，但仍可使用到 2027-06-30，新项目应使用 POST /v1/render/jobs。弃用接口不会新增字段，也不会保证返回 4K 相关能力。

项目文件格式在 3.6 中升级到 project-schema-v5。旧版 v4 项目首次打开时会创建只读快照并引导升级，升级后不能降级回 v4，但可以继续从快照导出旧版工程文件。
'''


TECHNICAL_DOCS = '''# 来画智能创作平台技术文档

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
'''


API_REFERENCE = '''# 来画智能创作平台 API 参考

## 1. 基础约定

SaaS 环境基础地址：https://api.laihua.example.com。所有接口使用 HTTPS，请求和响应均为 JSON，字符集为 UTF-8。文件上传先获取预签名 URL，再直接 PUT 到对象存储。

公共请求头：

| 请求头 | 必填 | 说明 |
| --- | --- | --- |
| Authorization | 是 | Bearer <access_token> |
| Content-Type | 是 | application/json，上传会话除外 |
| X-Request-Id | 建议 | 客户端生成的 UUID，服务端原样返回 |
| Idempotency-Key | 创建任务时建议 | 24 小时内保证创建幂等 |
| X-Org-Id | 多组织账号必填 | 指定当前组织 |

分页接口使用 cursor 和 limit。limit 默认 20，最大 100。响应中的 next_cursor 为空表示没有下一页。不要使用 offset 做深度分页，项目和事件列表只支持游标分页。

## 2. 获取访问令牌

### POST /v1/oauth/token

使用 client_credentials 获取应用级 access_token。

请求示例：

```json
{
  "grant_type": "client_credentials",
  "client_id": "lh_client_xxx",
  "client_secret": "your-secret",
  "scope": "project:read project:write render:write"
}
```

响应示例：

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 7200,
  "refresh_token": "rt_xxx",
  "refresh_expires_in": 2592000,
  "scope": "project:read project:write render:write"
}
```

access_token 有效期 7200 秒，即 2 小时。refresh_token 有效期 2592000 秒，即 30 天。刷新令牌使用 POST /v1/oauth/token，grant_type 为 refresh_token。每次刷新都会轮换 refresh_token。

## 3. 项目管理

### POST /v1/projects

创建项目。name 长度 1 到 128 个字符；template_id 可选；aspect_ratio 支持 16:9、9:16、1:1；resolution 支持 720p、1080p、4k。

```json
{
  "name": "秋季新品介绍",
  "template_id": "tpl_xxx",
  "aspect_ratio": "16:9",
  "resolution": "1080p",
  "brand_kit_id": "brand_xxx"
}
```

成功返回 201。项目初始 status 为 draft。项目每 15 秒自动保存，版本号从 1 开始递增，默认最多保留 50 个版本。

### GET /v1/projects/{project_id}

返回项目元数据、当前版本号、协作者和最近一次渲染任务。项目不存在返回 4040；项目存在但当前用户无权查看返回 4030。

### PATCH /v1/projects/{project_id}

更新项目名称、画布比例、品牌套件或模板同步策略。更新名称只产生新版本，不会触发重新渲染。同步模板会创建新版本并返回 diff_url。

## 4. 素材上传

### POST /v1/assets/upload-sessions

创建上传会话。单文件最大 2 GB。超过 100 MB 建议使用分片上传，分片大小 8 MB 到 64 MB。

```json
{
  "filename": "intro.mp4",
  "content_type": "video/mp4",
  "size_bytes": 52428800,
  "workspace_id": "ws_123",
  "multipart": true,
  "part_size": 8388608
}
```

响应包含 asset_id、upload_url、expires_at。预签名 URL 默认 15 分钟有效。分片上传完成后调用 POST /v1/assets/{asset_id}/complete，传入 part_etags。

素材状态为 uploading、processing、ready、failed。只有 ready 状态可以加入项目。processing 通常需要几十秒到数分钟；超过 30 分钟仍未完成应查询媒体服务日志。

## 5. 模板查询

### GET /v1/templates

查询官方模板和组织模板。参数：

- category：模板分类，例如 marketing、training、social。
- aspect_ratio：16:9、9:16 或 1:1。
- cursor：分页游标。
- limit：默认 20，最大 100。

响应中的 visibility 为 official 或 organization。organization 模板只对同一工作空间成员可见。模板更新不会自动修改已创建项目，项目需要显式同步。

## 6. 创建渲染任务

### POST /v1/render/jobs

创建渲染任务。推荐携带 Idempotency-Key，避免网络重试导致重复扣费。

```json
{
  "project_id": "prj_123",
  "project_version": 7,
  "output": {
    "format": "mp4",
    "resolution": "1080p",
    "fps": 30,
    "watermark": false
  },
  "callback_url": "https://example.com/hooks/render"
}
```

响应示例：

```json
{
  "job_id": "job_123",
  "status": "queued",
  "queue_reason": "concurrency_limit",
  "estimated_start_at": "2026-10-20T10:15:00Z",
  "created_at": "2026-10-20T10:00:00Z"
}
```

创建成功返回 202。4K 输出仅旗舰版可用，未开通时返回 4030。project_version 省略时使用最新版本，但生产环境建议显式指定，避免编辑期间版本变化。

### GET /v1/render/jobs/{job_id}

返回状态、进度、queue_reason、error_code、download_url 和 expires_at。状态包括 queued、preprocessing、rendering、encoding、succeeded、failed、canceled。

download_url 默认 24 小时有效。过期后可调用 POST /v1/render/jobs/{job_id}/download-url 重新签发。渲染任务默认最长执行 2 小时，超时返回 RENDER_TIMEOUT。

### POST /v1/render/jobs/{job_id}/cancel

取消排队中或执行中的任务。已经进入 succeeded 的任务不能取消，返回 4090。取消请求是异步的，响应返回 202 后应继续轮询直到状态变为 canceled。

## 7. 事件与 WebSocket

### GET /v1/events

补拉事件。参数 after_event_id、topic、limit。事件默认保留 24 小时。topic 支持 asset、render、approval、permission。

### WebSocket /ws/v1/events

连接参数 access_token 和 topics。空闲超时 10 分钟，客户端每 30 秒发送 ping。断线重连采用指数退避，初始 1 秒，最大 30 秒。事件可能重复或乱序，客户端按 event_id 去重，按 sequence 取最新状态。

## 8. Webhook

平台向 callback_url 推送任务事件。请求头包含 X-Laihua-Signature 和 X-Laihua-Timestamp。签名算法为 HMAC-SHA256，签名内容为 timestamp + "." + raw_body。时间戳偏差超过 5 分钟应拒绝。

Webhook 失败后重试 5 次，间隔采用指数退避。收到 2xx 即视为成功。业务处理应保证幂等，推荐使用 event_id 作为幂等键。不要只根据回调更新最终状态，必要时调用任务查询接口补偿。

## 9. 错误码

| 错误码 | HTTP 状态 | 含义 | 建议处理 |
| --- | --- | --- | --- |
| 4001 | 400 | 参数格式错误 | 根据 field 修正请求 |
| 4010 | 401 | access_token 过期或签名错误 | 刷新令牌后重试 |
| 4011 | 429 | 刷新令牌频率超限 | 按 Retry-After 退避 |
| 4030 | 403 | 无权限或能力未开通 | 检查角色和套餐 |
| 4035 | 403 | 内容安全策略拦截 | 修改内容或提交人工复核 |
| 4040 | 404 | 资源不存在 | 检查 ID 和工作空间 |
| 4090 | 409 | 状态冲突 | 重新查询资源状态 |
| 4290 | 429 | API 频率超限 | 指数退避，默认每分钟 600 次 |
| 5003 | 502 | 上游服务超时 | 可重试一次并携带 request_id |
| 5030 | 503 | 模型能力未启用或维护中 | 检查部署授权或稍后重试 |

错误响应统一包含 code、message、request_id 和 details。客户端日志应记录 request_id，但不要记录完整 token。

## 10. 频率限制与幂等

默认每个应用每分钟 600 次请求，突发上限 60 次。响应头 X-RateLimit-Limit、X-RateLimit-Remaining 和 Retry-After 用于控制重试。4290 时不要在 1 秒内循环重试。

创建渲染任务、创建上传会话和刷新令牌支持幂等。Idempotency-Key 至少 16 个字符，建议使用 UUID。相同幂等键但请求体不同会返回 4090。

## 11. 调用示例

```bash
curl -X POST https://api.laihua.example.com/v1/render/jobs \\
  -H "Authorization: Bearer $ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -H "X-Request-Id: 8f14e45f-ea2b-4b5d-9d5d-0f4f3b2a1c11" \\
  -H "Idempotency-Key: 0d1f6b4e-6f65-4d1e-9f3d-6c2a5b8e7a10" \\
  -d '{"project_id":"prj_123","project_version":7,"output":{"format":"mp4","resolution":"1080p","fps":30}}'
```

```python
import httpx

response = httpx.post(
    "https://api.laihua.example.com/v1/render/jobs",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Idempotency-Key": idempotency_key,
    },
    json={
        "project_id": "prj_123",
        "project_version": 7,
        "output": {"format": "mp4", "resolution": "1080p", "fps": 30},
    },
    timeout=30,
)
response.raise_for_status()
job = response.json()
```

## 12. 版本与弃用

v1 API 继续兼容。POST /v1/render 自 2026-09 起弃用，将于 2027-06-30 下线，替代接口为 POST /v1/render/jobs。弃用接口不会新增 4K、批量渲染和项目版本锁定能力。

客户端应在启动时读取 OpenAPI 文档的 version 和 deprecation 字段。服务端新增响应字段属于兼容变更，客户端不得因为出现未知字段而解析失败。
'''


DOCUMENTS = {
    "product-manual.md": PRODUCT_MANUAL,
    "technical-docs.md": TECHNICAL_DOCS,
    "api-reference.md": API_REFERENCE,
}


def write_offline_documents(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename, content in DOCUMENTS.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        paths.append(path)
    return paths
