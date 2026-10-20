# 来画智能创作平台 API 参考

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
curl -X POST https://api.laihua.example.com/v1/render/jobs \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: 8f14e45f-ea2b-4b5d-9d5d-0f4f3b2a1c11" \
  -H "Idempotency-Key: 0d1f6b4e-6f65-4d1e-9f3d-6c2a5b8e7a10" \
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
