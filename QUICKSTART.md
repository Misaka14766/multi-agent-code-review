# 多智能体代码审查系统 — 快速上手指南

## 一、环境要求

- Python 3.11+
- Windows / Linux / macOS
- 已安装依赖：`pip install -r requirements.txt`

## 二、安装（首次使用）

```bash
cd "c:\Users\张朴\Desktop\多智能体代码审查"

# 安装 Python 依赖
pip install -r requirements.txt

# 安装外部工具（Pylint 已含于 requirements，以下独立安装）
pip install pylint semgrep tree-sitter tree-sitter-python chromadb openai

# 验证安装
python -c "import langgraph, fastapi, chromadb; print('OK')"
```

## 三、配置 API Key（启用真实 AI 审查）

编辑项目根目录 `.env` 文件：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的真实密钥
```

系统自动切换规则：

| LLM_PROVIDER | API Key | 模式 |
|-------------|---------|------|
| `mock` | 任意 | 内置样例数据，不调用 API |
| `deepseek` | 占位符 | 降级为 Mock，提示替换真实 Key |
| `deepseek` | 真实 Key | 启用全部真实 Agent |

> 无需改任何代码，改 `.env` 一行即切换。

## 四、三种使用方式

### 方式一：CLI 命令行（推荐日常使用）

```bash
# 审查单个文件
python scripts/run_cli.py --file "D:\你的项目\某文件.py"

# Mock 模式快速演示（不消耗 API）
python scripts/run_cli.py --mock

# 输出 JSON 报告到文件
python scripts/run_cli.py --file code.py --format json --output report.json
```

执行流程：读文件 → 3 个 Agent 并行审查 → 仲裁去重 → 质量门控 → 输出 Markdown 报告。约 20-30 秒完成。

### 方式二：API 服务器（团队使用 / CI 集成）

```bash
# 启动服务（默认 8000 端口，被占用时换端口）
python scripts/run_server.py --port 8080
```

浏览器打开：
- `http://localhost:8080/docs` → Swagger UI（可视化调用，可直接在网页上提交审查）
- `http://localhost:8080/` → Dashboard（审查统计 + 图表 + 历史）

Curl 调用：

```bash
# 提交审查
curl -X POST http://localhost:8080/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{"code": "def login(u,p):\n  sql = \"SELECT * FROM users WHERE name=\" + u\n  db.execute(sql)", "file_path": "auth.py"}'

# 返回 {"review_id": "abc123", "status": "pending"}

# 查看报告（等 20 秒后）
curl http://localhost:8080/api/v1/review/abc123/report
```

### 方式三：5 分钟演示

```bash
python scripts/demo.py        # 完整 5 分钟演示
python scripts/demo.py --fast  # 1 分钟快速版
```

## 五、API 端点速查

| Method | Path | 说明 |
|--------|------|------|
| `GET` | `/api/v1/health` | 健康检查 + Agent 状态 |
| `POST` | `/api/v1/review` | 提交代码审查 |
| `GET` | `/api/v1/review/{id}` | 查询审查进度 |
| `GET` | `/api/v1/review/{id}/report` | 获取完整审查报告 |
| `POST` | `/api/v1/webhook/github` | GitHub PR Webhook |
| `GET` | `/api/v1/dashboard/stats` | 聚合统计数据 |
| `GET` | `/api/v1/dashboard/history` | 最近审查历史 |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/` | Web Dashboard |

## 六、四个审查 Agent

| Agent | 技术栈 | 审查内容 |
|-------|--------|----------|
| **Static Analysis** | Semgrep + Pylint + Tree-sitter | SQL 注入、XSS、代码风格、圈复杂度 |
| **Semantic Review** | DeepSeek LLM + ChromaDB RAG | 根因分析、历史相似 Bug 引用、架构审查 |
| **Test & Regression** | LLM + coverage.py | 测试覆盖率评估、自动生成缺失测试 |
| **Repair & Patch** | LLM + Sandbox | 自动修复补丁 + 语法/静态分析/沙箱三重验证 |

## 七、报告解读

```
审查结论: [PASS] / [BLOCK] / [WARN]

[BLOCK] 阻断级 — 必须修复才能合并（如 SQL 注入）
[WARN]  警告级 — 建议修复，需人工确认
[SUGG]  建议级 — 参考性改进建议
[INFO]  信息级 — 风格提示 / 最佳实践
```

每条 Issue 包含：根因分析、证据代码、修复建议（含 unified diff）、置信度、来源 Agent。

## 八、常见问题

**Q: 端口被占用？**
```bash
python scripts/run_server.py --port 8080
```

**Q: 只想测试不消耗 API？**

`.env` 中设 `LLM_PROVIDER=mock`，或 CLI 加 `--mock` 参数。

**Q: Semgrep 首次运行慢？**

首次需要下载规则库（~30 秒），后续缓存后秒级完成。

**Q: 审查大文件超时？**

`.env` 中增大 `AGENT_TIMEOUT_SECONDS=60`。

**Q: DeepSeek API 报错？**

检查 `.env` 中 `DEEPSEEK_API_KEY` 是否正确。系统自动将占位符检测并降级为 Mock。

## 九、运行测试

```bash
pytest tests/ -v          # 全部 101 个测试
pytest tests/ -q          # 简洁输出
pytest tests/test_agents/ # 仅 Agent 测试
```

## 十、审查自己项目的示例

```bash
# 审查单个文件
python scripts/run_cli.py --file "C:\Users\张朴\Desktop\EStin\setup.py"

# 批量审查目录
for f in C:\Users\张朴\Desktop\EStin\*.py; do
    python scripts/run_cli.py --file "$f" --output "report_$(basename $f).json"
done
```

---

**10 分钟就能跑通全流程。** Mock 模式开箱即用，填入 DeepSeek Key 后启用真实 AI 审查。
