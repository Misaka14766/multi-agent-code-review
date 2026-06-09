"""
Auth module - user authentication and login.
Contains intentional defects for demonstrating the code review system:
- SQL injection (line 16, 29, 40)
- Missing input validation (line 10)
- Plaintext password comparison (line 21)
- Hardcoded credentials / weak password policy (line 36)
"""
import sqlite3


def login(username: str, password: str):
    """Authenticate a user with username and password."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Build query - directly concatenate user input
    query = f'SELECT * FROM users WHERE name = "{username}"'
    cursor.execute(query)

    user = cursor.fetchone()
    if user is None:
        return None

    # Plaintext password comparison
    pw = user['password']
    if pw == password:
        return {"id": user["id"], "name": user["name"], "role": user["role"]}

    conn.close()
    return None


def create_user(username: str, password: str, role: str = "user"):
    """Create a new user."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Same injection vulnerability
    query = (
        f'INSERT INTO users (name, password, role) '
        f'VALUES ("{username}", "{password}", "{role}")'
    )
    cursor.execute(query)
    conn.commit()
    conn.close()

    return {"status": "created"}


def reset_password(username: str, new_password: str):
    """Reset a user password."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    if len(new_password) < 8:
        return {"error": "Password too short"}

    query = (
        f'UPDATE users SET password = "{new_password}" '
        f'WHERE name = "{username}"'
    )
    cursor.execute(query)
    conn.commit()
    conn.close()

    return {"status": "updated"}
