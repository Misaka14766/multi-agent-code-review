"""Pre-built knowledge documents for seeding the RAG vector store."""

from .schemas import KnowledgeDocument, KnowledgeType


def get_seed_documents() -> list[KnowledgeDocument]:
    """Return a set of initial knowledge documents covering common defect patterns."""
    return [
        KnowledgeDocument(
            doc_id="BUG-SQL-001",
            knowledge_type=KnowledgeType.BUG_PATTERN,
            title="SQL注入 — 字符串拼接构建查询",
            content="SQL注入是最常见的安全漏洞之一。当用户输入通过字符串拼接(f-string、+、format)直接嵌入SQL语句时，攻击者可构造恶意输入篡改查询逻辑。修复方案：使用参数化查询(占位符?或%s)，将用户输入与SQL逻辑分离。参考OWASP SQL Injection Prevention Cheat Sheet。",
            metadata={"language": "python", "severity": "blocker", "cwe": "CWE-89", "owasp": "A03:2021-Injection"},
        ),
        KnowledgeDocument(
            doc_id="BUG-SQL-002",
            knowledge_type=KnowledgeType.BUG_PATTERN,
            title="SQL注入 — 动态表名/列名拼接",
            content="当ORDER BY、GROUP BY或表名需要动态指定时，不应直接拼接用户输入。应对输入做白名单校验，只允许预定义的值。例如：ALLOWED_COLUMNS = {'id','name','date'}; if column not in ALLOWED_COLUMNS: raise ValueError。",
            metadata={"language": "python", "severity": "blocker", "cwe": "CWE-89"},
        ),
        KnowledgeDocument(
            doc_id="BUG-NULL-001",
            knowledge_type=KnowledgeType.BUG_PATTERN,
            title="空指针/None引用 — 未检查返回值",
            content="调用可能返回None的函数(如dict.get()、re.search()、数据库查询)后，直接访问其属性或方法会导致AttributeError或TypeError。修复方案：使用if x is not None检查，或使用walrus运算符(Python 3.8+)在条件中同时赋值和检查。",
            metadata={"language": "python", "severity": "warning", "cwe": "CWE-476"},
        ),
        KnowledgeDocument(
            doc_id="BUG-XSS-001",
            knowledge_type=KnowledgeType.BUG_PATTERN,
            title="跨站脚本(XSS) — 未转义的用户输出",
            content="将用户输入直接渲染到HTML响应中会导致XSS攻击。修复方案：使用模板引擎的自动转义功能(Jinja2的{{ }}默认转义)、对输出做HTML实体编码、设置Content-Security-Policy头。",
            metadata={"language": "python", "severity": "blocker", "cwe": "CWE-79", "owasp": "A03:2021-Injection"},
        ),
        KnowledgeDocument(
            doc_id="BUG-RACE-001",
            knowledge_type=KnowledgeType.BUG_PATTERN,
            title="竞态条件 — TOCTOU (Time-of-Check-Time-of-Use)",
            content="在检查条件和执行操作之间存在时间窗口，可能被并发请求利用。例如：先检查文件是否存在再写入、先检查余额再扣款。修复方案：使用原子操作、数据库事务(SELECT FOR UPDATE)、文件锁(fcntl.flock)或适当的隔离级别。",
            metadata={"language": "python", "severity": "warning", "cwe": "CWE-367"},
        ),
        KnowledgeDocument(
            doc_id="STD-PY-001",
            knowledge_type=KnowledgeType.CODING_STANDARD,
            title="PEP 8 — Python代码风格指南",
            content="Python代码应遵循PEP 8规范：使用4空格缩进、每行最多79字符(文档字符串/注释72)、函数和类之间用两个空行、导入按标准库→第三方→本地顺序分组、变量名使用snake_case、类名使用PascalCase、常量使用UPPER_CASE。",
            metadata={"language": "python", "standard": "PEP 8"},
        ),
        KnowledgeDocument(
            doc_id="STD-PY-002",
            knowledge_type=KnowledgeType.CODING_STANDARD,
            title="Python类型注解最佳实践",
            content="所有公共函数应包含类型注解。使用typing模块的List、Dict、Optional等泛型(Python 3.9+可直接使用list、dict)。使用mypy进行静态类型检查。避免使用Any，除非确实需要动态类型。",
            metadata={"language": "python", "standard": "PEP 484"},
        ),
        KnowledgeDocument(
            doc_id="ARCH-001",
            knowledge_type=KnowledgeType.ARCHITECTURE_RULE,
            title="单一职责原则 — 函数/类应只做一件事",
            content="一个函数或类应该只有一个改变的理由。如果函数中混合了HTTP请求解析、数据库操作和业务逻辑，应拆分为独立的处理层。推荐分层架构：Controller(请求处理) → Service(业务逻辑) → Repository(数据访问)。",
            metadata={"principle": "Single Responsibility Principle", "pattern": "Layered Architecture"},
        ),
        KnowledgeDocument(
            doc_id="EXP-001",
            knowledge_type=KnowledgeType.REVIEW_EXPERIENCE,
            title="审查经验：参数化查询修复后需验证所有路径",
            content="历史Issue#234：修复SQL注入时只修改了login函数，但create_user和reset_password函数仍有相同问题。教训：同类漏洞通常在整个文件中重复出现，修复时应全局搜索所有类似模式。采纳结果：修复采纳，新增安全测试。",
            metadata={"source": "Issue#234", "lesson": "全局搜索相同模式", "date": "2023-08"},
        ),
        KnowledgeDocument(
            doc_id="EXP-002",
            knowledge_type=KnowledgeType.REVIEW_EXPERIENCE,
            title="审查经验：输入校验应尽早进行",
            content="历史审查发现：输入校验放在业务逻辑深处，已进行了不安全的数据库操作。最佳实践是在函数入口(API边界)进行校验(类型、长度、格式)，使用Pydantic或marshmallow进行声明式校验，尽早拒绝非法输入。",
            metadata={"source": "Review#567", "lesson": "Fail Fast原则", "date": "2024-01"},
        ),
    ]
