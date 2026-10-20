# WebSocket 连接指南

## 连接生命周期

WebSocket 连接默认空闲超时为 10 分钟。客户端应每 30 秒发送一次 ping，服务端在收到 ping 后返回 pong。

## 断线重连

连接中断后，客户端应使用指数退避策略重连，初始等待 1 秒，最大等待 30 秒。重连请求必须携带原请求的 request_id，服务端据此恢复订阅关系。

```python
await websocket.send_json({"type": "ping"})
```

## 常见错误

- 错误码 4010：鉴权过期，需要重新获取 access_token。
- 错误码 4011：请求频率超限，应在 Retry-After 后再连接。
- 错误码 4012：订阅主题不存在，需要检查 topic 参数。
