# 01：幂等、事务与重试

日期：2026-10-08。范围：本地 SQLite 审核接口；未验证分布式发布。

## 业务问题

n8n 调用审核接口后超时，不能确定服务是否已经保存结果。直接重试可能生成两份任务。幂等让相同业务请求重试时复用同一结果；它不保证外部系统恰好执行一次。

## 工作原理

调用方给同一个逻辑任务传入稳定的 job_id。服务计算输入摘要，再在事务内检查：

- ID 不存在：生成并保存结果。
- ID 存在、摘要相同：返回已保存结果。
- ID 存在、摘要不同：拒绝，HTTP 409；修改内容必须创建新版本 ID。

摘要用于判断输入是否一致，不替代身份认证。多租户系统还应把租户加入唯一键。

## 已有项目中的位置

[n8n 重试] → [POST /reviews] → [SQLite 事务] → [保存或复用报告] → [人工审批]。

[实现：industry_lab/api.py](../industry_lab/api.py) 的 submit 使用主键约束和 BEGIN IMMEDIATE，在读取、比较、插入期间串行化写事务。避免两个请求同时看到“记录不存在”后重复处理。占锁期间应保持操作短小，不放慢速模型调用。

SQLite 可用于本地原型；Python 提供 sqlite3 数据库接口。连接上下文管理器负责事务提交或回滚，但不会自动关闭连接。[Python 官方资料](https://docs.python.org/3/library/sqlite3.html)

## 最小例子

从仓库根目录启动已有 Skill：

```powershell
.\.venv\Scripts\python.exe -m uvicorn industry_lab.api:app_factory --factory --host 127.0.0.1 --port 8091
```

另开 PowerShell：

```powershell
$body = @{
  job_id = 'kb-idempotency-001'
  product = @{ name = 'Demo Bread'; facts = @{ ingredients = 'flour'; storage = 'cool place' } }
  claims = @()
  copy = 'Demo Bread'
  max_chars = 100
} | ConvertTo-Json -Depth 5
Invoke-RestMethod http://127.0.0.1:8091/reviews -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod http://127.0.0.1:8091/reviews -Method Post -ContentType 'application/json' -Body $body
```

两次返回同一报告；人工审核仍必需。修改 copy、保持 job_id 后再请求，会返回 409。重新运行例子时可复用原输入，或更换 ID。

## 可复现验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_review.py -q
```

覆盖重复请求、相同 ID 不同内容、人工决定不可重复覆盖、跨重启保留决定。2026-10-08：11 项通过。这里验证的是应用测试客户端与本地数据库，不代表 n8n 实机重试已验证。

## 失败边界与取舍

只有瞬时故障才做有上限的退避重试；输入校验错误和内容冲突不应无限重试。模型调用或外部发送与数据库事务不是同一原子操作，需进一步设计任务状态、outbox 或外部幂等键。不能用“已有 ID”代替权限检查。

轻量案例先用 SQLite；跨服务、较高写并发时评估 PostgreSQL，任务耗时较长时再引入队列。Redis 缓存不能自动替代持久化任务记录。

官方资料核查：2026-10-08；示例使用仓库已有 Python 环境与锁定依赖。
