# API Documentation

Base URL: `http://localhost:8000`

## Endpoints

### Health Check

```
GET /api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "llm_provider": "mock",
  "agents": {
    "static_analysis": true,
    "semantic_review": true,
    "test_regression": true,
    "repair_patch": true
  }
}
```

### Submit Code for Review

```
POST /api/v1/review
```

Request:
```json
{
  "code": "def login(u, p): query = f'SELECT * FROM users WHERE name=\"{u}\"'",
  "file_path": "src/auth.py",
  "language": "python",
  "context": "Review login function"
}
```

Response:
```json
{
  "review_id": "a1b2c3d4",
  "status": "pending",
  "message": "Review started"
}
```

### Get Review Status

```
GET /api/v1/review/{review_id}
```

Response:
```json
{
  "review_id": "a1b2c3d4",
  "status": "completed",
  "errors": []
}
```

### Get Review Report

```
GET /api/v1/review/{review_id}/report
```

Returns the full structured review report (JSON):
```json
{
  "review_id": "a1b2c3d4",
  "pr_title": "Review: src/auth.py",
  "status": "completed",
  "summary": {
    "total_issues": 4,
    "blockers": 1,
    "warnings": 2,
    "suggestions": 0,
    "info": 1,
    "verdict": "blocked",
    "verdict_summary": "发现 1 个阻断级缺陷，须修复后方可合并。",
    "requires_human": true,
    "repair_attempts": 1,
    "total_execution_time_ms": 210
  },
  "issues": [...],
  "patches": [...],
  "agent_reports": [...],
  "errors": []
}
```

### GitHub Webhook

```
POST /api/v1/webhook/github
```

Headers:
- `X-Hub-Signature-256`: HMAC-SHA256 signature (required if `GITHUB_WEBHOOK_SECRET` is set)
- `X-GitHub-Event`: Event type (e.g., `pull_request`, `ping`)

Supported events:
- `ping`: Webhook verification
- `pull_request` (opened/synchronize): Trigger review

### Dashboard Stats

```
GET /api/v1/dashboard/stats
```

Response:
```json
{
  "total_reviews": 5,
  "blocked": 2,
  "passed": 2,
  "pending": 0,
  "total_issues_found": 16,
  "total_patches_generated": 3
}
```

### Dashboard History

```
GET /api/v1/dashboard/history?limit=10
```

Response:
```json
{
  "reviews": [
    {
      "review_id": "a1b2c3d4",
      "verdict": "blocked",
      "issues": 4,
      "pr_title": "Review: src/auth.py"
    }
  ]
}
```

### Swagger UI

```
GET /docs
```

Interactive API documentation with request/response schemas.

### Dashboard

```
GET /
```

Web-based dashboard with statistics charts and review history.
