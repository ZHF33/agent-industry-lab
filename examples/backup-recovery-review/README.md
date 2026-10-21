# 备份恢复证据复核 Agent

面向运维和业务连续性负责人：备份任务显示成功，但最近一次恢复演练早已过期、测试的也不是最新备份。Agent读取合成清单和演练记录，核对恢复点、历史服务恢复时间与证据缺项，整理人工下一步建议。

**输入**：case_id、system_id、含UTC偏移的as_of、description，见[sample.json](sample.json)。**输出**：thread_id、recovery_report、带来源的建议与工具轨迹。示例恢复点落后14分钟，记录中的历史演练22分钟完成；演练已超过30天，且使用旧备份，因此最新备份实际可恢复性仍需另行证据。

流程：n8n提交 → FastAPI严格字段校验 → LangGraph模型自行选择清单/演练/评估工具并读取结果 → 人工中断 → n8n审核 → 恢复记录。最多四轮模型、每消息三个工具调用；参数错误可在预算内纠正。approve仅接受建议，不恢复数据库、不切换系统、不改保留策略或发送业务消息。

## 运行

前提：Python3.12+，已有Ollama和支持工具调用的qwen3:4b。可用OLLAMA_MODEL指定本机已有的兼容模型。以下命令由使用者手动执行，在本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:RECOVERY_API_KEY = '替换为自己生成的随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8104 --workers 1
```

提交与人工审核：

```powershell
$headers = @{ 'X-API-Key' = $env:RECOVERY_API_KEY }
$result = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8104/triage' -Headers $headers -ContentType 'application/json' -Body (Get-Content sample.json -Raw)
$result | ConvertTo-Json -Depth 20
# 人工对照报告后选择approve或reject，审核不执行恢复。
$body = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8104/threads/$($result.thread_id)/review" -Headers $headers -ContentType 'application/json' -Body $body
```

只支持合成系统RECOVERY-DEMO-01；as_of是分析参考时刻，不是自动读取的真实事故时间。记录中的恢复点与完成时间分开；时间、快照新鲜度、演练状态、备份编号分别检查。清单中checksum_recorded_match只表示存在合成记录，未读取文件计算哈希。

## 工作流和Skill

导入[n8n-workflow.json](n8n-workflow.json)，默认停用。提交路径backup-recovery-case；审核路径backup-recovery-review，审核正文含thread_id、decision、reviewer。Webhook节点设置独立Header Auth，HTTP节点设置含X-API-Key的Header Auth凭据，与RECOVERY_API_KEY一致。工作流不嵌凭据，等待510秒，不自动重试。容器中的127.0.0.1需改为可达API地址。

LangGraph负责唯一Agent循环，n8n负责入口和转发。结构化证据用精确ID查询，不需要RAG、向量库、Dify或独立LangChain重复编排。单进程内存检查点、串行锁、忙时429；重启会丢失审核状态，共享密钥面向可信操作员，不提供租户隔离。

[Skill入口](SKILL.md) · [工程检查与完整基建评估](CHECKS.md)。源码MIT；依赖和模型保留自身许可。只含合成元数据，没有数据库、备份文件、密钥或真实运行日志。
