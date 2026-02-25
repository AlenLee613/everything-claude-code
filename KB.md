# Ephemeral Key System 知识库

本文档汇总了系统的核心业务流程、架构模块以及数据流向。

## 1. 系统概览

本系统是一个基于 **FastAPI + SQLite/Redis** 的轻量级临时密钥管理服务 (Ephemeral Key Service)。它提供了一套完整的密钥生命周期管理、访问控制、流量限制以及可观测性方案，适用于为 AI 模型服务提供安全的临时访问凭证。

核心能力：
*   **临时密钥 (Ephemeral Keys)**: 支持自定义 TTL (生存时间) 和最大请求次数。
*   **访问控制**: 基于 Token 的认证，支持动态配置 IP 白名单/黑名单。
*   **流量控制**:
    *   **总量配额**: 密钥耗尽即失效。
    *   **速率限制 (RPM)**: 支持针对每个密钥设置每分钟请求数限制 (Sliding Window 算法)。
*   **可观测性**:
    *   **用量统计 (Usage Export)**: 记录 Token 消耗与成本，支持 CSV 导出。
    *   **归因追踪 (Attribution Logging)**: 全链路记录请求详情（包括耗时、并发、状态码、模型信息），支持多维度查询。

---

## 2. 核心业务流程 (Sequence Diagram)

以下时序图展示了密钥管理、配置、以及请求处理的全生命周期。

```plantuml
@startuml
skinparam boxPadding 10

participant Client
participant "AuthMiddleware" as Middleware
participant "API/KeyService" as Router
participant "StorageBackend (Local/Redis)" as Storage

box "Management Plane" #f9f9f9
    Client -> Router: POST /api/keys/ephemeral (TTL, MaxReqs)
    Router -> Storage: create_key(uuid, info, ttl)
    Storage --> Router: key_id
    Router --> Client: {key: "ephem_...", expire_at: ...}

    Client -> Router: PUT /api/keys/{key}/rpm (rpm=60)
    Router -> Storage: set_key_rpm(key, 60)
    Router --> Client: 200 OK
end

box "Data Plane" #e6f3ff
    Client -> Middleware: GET /api/data (Header: X-API-Key)
    activate Middleware
    
    ' 1. Authentication
    Middleware -> Storage: get_key_status(key)
    alt Key Invalid / Expired
        Storage --> Middleware: None
        Middleware --> Client: 403 Forbidden
    else Key Valid
        Storage --> Middleware: {info, remaining}
    end

    ' 2. IP Policy Check
    opt IP Policy Configured
        Middleware -> Middleware: check_ip_allowed(client_ip, policy)
        alt IP Blocked
            Middleware --> Client: 403 (IP_NOT_ALLOWED)
        end
    end

    ' 3. RPM Rate Limiting
    opt RPM Limit Configured
        Middleware -> Storage: check_rate_limit(key, rpm)
        alt Rate Limit Exceeded
            Storage --> Middleware: False
            Middleware --> Client: 429 Too Many Requests
        end
    end

    ' 4. Quota Management
    Middleware -> Storage: decrement_remaining(key)
    alt Quota Exhausted (remaining < 0)
        Storage -> Storage: delete_key(key)
        Middleware --> Client: 403 (Usage Limit Exceeded)
    else Quota Available
        ' 5. Forward to Handler
        Middleware -> Router: Forward Request
        activate Router
        Router --> Middleware: Response (data, model, tokens)
        deactivate Router
    end

    ' 6. Observability (Async/Post-Response)
    par Logging
        Middleware -> Storage: log_usage(key, {tokens, cost...})
        Middleware -> Storage: log_attribution({request_id, latency, concurrency...})
    end
    
    deactivate Middleware
    Middleware --> Client: Response
end
@enduml
```

---

## 3. 功能模块详解

### 3.1 认证与权限 (Authentication & Authorization)
*   **入口**: `app/middleware/auth.py` -> `dispatch`
*   **逻辑**: 
    1.  从 Header (`X-API-Key`) 或 Path 中提取密钥。
    2.  调用 `storage.get_key_status` 验证密钥存在性及有效期。
    3.  解析存储在 Key Info 中的 IP 策略 (`whitelist`/`blacklist`) 并执行校验。

### 3.2 流量控制 (Traffic Control)
*   **总量配额**: 
    *   在 Key 创建时设定 `max_requests`。
    *   每次请求原子递减 (`decrement_remaining`)。
    *   归零时触发 Key 删除。
*   **速率限制 (RPM)**:
    *   **接口**: `PUT /api/keys/{key}/rpm`
    *   **实现**: `storage.check_rate_limit(key, rpm)`
    *   **算法**: 滑动窗口 (Sliding Window)。
        *   **SQLite**: 查询 `request_timestamps` 表中过去 60s 的记录数。
        *   **Redis**: 使用 `ZSET` (Sorted Set) 存储时间戳，`ZREMRANGEBYSCORE` 清理过期数据，`ZCARD` 统计当前窗口请求数。

### 3.3 可观测性 (Observability)

#### 用量统计 (Usage Logging)
*   **目的**: 成本核算与计费。
*   **数据**: 记录 `timestamp`, `key_id`, `model`, `tokens`, `cost`。
*   **接口**: 
    *   `GET /api/usage/export?start=..&end=..&granularity=day/hour` (支持 CSV 导出)。

#### 归因追踪 (Attribution Logging)
*   **目的**: 性能分析、错误定位、系统健康度监控。
*   **数据**:
    *   `request_id`: 全局唯一请求 ID。
    *   `inflight_concurrency`: 请求开始时的系统并发数。
    *   `latency_ms`: 请求耗时。
    *   `status_code`: HTTP 状态码（覆盖 200, 4xx, 5xx）。
    *   `endpoint`, `model`, `token_id` 等上下文信息。
*   **接口**:
    *   `GET /api/attribution/requests`: 支持按时间、Token、模型、状态码过滤及分页查询。

---

## 4. 数据存储设计 (SQLite Schema)

系统主要包含 4 张核心表：

| 表名 | 描述 | 关键字段 |
| :--- | :--- | :--- |
| **`ephemeral_keys`** | 存储密钥元数据与配额 | `key_id` (PK), `info_json` (RPM/IP配置), `remaining`, `expires_at` |
| **`usage_logs`** | 业务用量流水 | `timestamp`, `key_id`, `model`, `tokens`, `cost` |
| **`request_timestamps`** | RPM 速率限制滑动窗口记录 | `key_id`, `timestamp` (Unix), `expiration` |
| **`attribution_logs`** | 详细请求归因日志 | `request_id` (PK), `latency_ms`, `inflight_concurrency`, `status_code` |

*注：Redis 实现使用相应的 Key-Value, Hash, ZSet 结构映射上述逻辑。*
