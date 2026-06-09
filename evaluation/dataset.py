"""Evaluation dataset — code samples with known defects and ground truth labels.

Each sample has:
  - code: the source code under review
  - file_path: logical file name
  - ground_truth: list of expected issue types/severities
  - description: what the sample is testing
"""

from dataclasses import dataclass, field


@dataclass
class EvalSample:
    id: str
    code: str
    file_path: str
    description: str
    expected_issues: list[dict] = field(default_factory=list)
    # Each expected issue: {"type": "security", "severity": "blocker", "title_keyword": "SQL"}


EVAL_DATASET: list[EvalSample] = []


def _sample(id: str, file_path: str, description: str, code: str, expected: list[dict]) -> EvalSample:
    s = EvalSample(id=id, code=code.strip(), file_path=file_path, description=description, expected_issues=expected)
    EVAL_DATASET.append(s)
    return s


# === 12 Evaluation Samples ===

_sample(
    "E01", "auth.py", "SQL injection via f-string",
    '''def login(username, password):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()''',
    [{"type": "security", "severity": "blocker", "keyword": "SQL"}],
)

_sample(
    "E02", "auth.py", "SQL injection via string concatenation",
    '''def find_user(name):
    sql = "SELECT * FROM users WHERE name = '" + name + "'"
    return db.query(sql)''',
    [{"type": "security", "severity": "blocker", "keyword": "SQL"}],
)

_sample(
    "E03", "user.py", "Plaintext password comparison",
    '''def check_password(user, pw):
    stored = get_stored_password(user)
    if stored == pw:
        return True
    return False''',
    [{"type": "security", "severity": "warning", "keyword": "password"}],
)

_sample(
    "E04", "api.py", "Missing input validation",
    '''def create_item(data):
    name = data['name']
    price = data['price']
    db.insert('items', name=name, price=price)
    return {"status": "ok"}''',
    [{"type": "bug", "severity": "warning", "keyword": "validation"},
     {"type": "bug", "severity": "warning", "keyword": "input"}],
)

_sample(
    "E05", "process.py", "Bare except catches all",
    '''def process_file(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return None''',
    [{"type": "maintainability", "severity": "warning", "keyword": "except"}],
)

_sample(
    "E06", "calc.py", "Division by zero not handled",
    '''def divide(a, b):
    return a / b''',
    [{"type": "bug", "severity": "warning", "keyword": "zero"}],
)

_sample(
    "E07", "config.py", "Hardcoded secret key",
    '''SECRET_KEY = "sk-1234567890abcdef"
API_TOKEN = "ghp_0123456789abcdef"''',
    [{"type": "security", "severity": "blocker", "keyword": "secret"},
     {"type": "security", "severity": "blocker", "keyword": "hardcoded"}],
)

_sample(
    "E08", "loop.py", "N+1 query pattern",
    '''def get_users_with_posts():
    users = db.query("SELECT * FROM users")
    for user in users:
        user['posts'] = db.query(f"SELECT * FROM posts WHERE user_id = {user['id']}")
    return users''',
    [{"type": "performance", "severity": "warning", "keyword": "N+1"},
     {"type": "security", "severity": "blocker", "keyword": "SQL"}],
)

_sample(
    "E09", "style.py", "Poor naming and style",
    '''def f(x, y, z):
    a = x + y
    b = a * z
    return b''',
    [{"type": "style", "severity": "info", "keyword": "name"}],
)

_sample(
    "E10", "clean_util.py", "Clean code — no defects",
    '''def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b''',
    [],  # Expected: no issues
)

_sample(
    "E11", "xss.py", "XSS vulnerability in web output",
    '''def render_profile(username):
    html = "<h1>Welcome, " + username + "</h1>"
    return html''',
    [{"type": "security", "severity": "blocker", "keyword": "XSS"}],
)

_sample(
    "E12", "file.py", "Path traversal vulnerability",
    '''def read_file(filename):
    path = "/var/data/" + filename
    with open(path) as f:
        return f.read()''',
    [{"type": "security", "severity": "blocker", "keyword": "path"}],
)


def get_dataset() -> list[EvalSample]:
    return list(EVAL_DATASET)
