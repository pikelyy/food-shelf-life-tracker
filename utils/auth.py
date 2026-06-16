"""
用户认证模块 - 注册 / 登录 / 密码加密
"""

import hashlib
import secrets
import re
from .database import _execute_sql, _query_sql, is_postgres


# ---------- 密码加密 ----------

def _hash_password(password: str) -> str:
    """生成带随机盐的密码哈希 (salt$hash)"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def _verify_password(password: str, stored: str) -> bool:
    """验证密码"""
    if "$" not in stored:
        return False
    salt, pwd_hash = stored.split("$", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == pwd_hash


# ---------- 用户操作 ----------

def register_user(username: str, password: str) -> tuple[bool, str]:
    """
    注册新用户
    返回 (成功?, 消息)
    """
    username = username.strip()
    if not username or len(username) < 2:
        return False, "用户名至少 2 个字符"
    if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fff]+$", username):
        return False, "用户名只能包含字母、数字、下划线和中文"
    if len(password) < 4:
        return False, "密码至少 4 个字符"

    # 检查是否已存在
    existing = _query_sql("SELECT id FROM users WHERE username = %s", (username,), fetchone=True)
    if existing:
        return False, "用户名已被注册"

    password_hash = _hash_password(password)
    _execute_sql(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
        (username, password_hash),
    )
    return True, "注册成功！请登录"


def login_user(username: str, password: str) -> tuple[bool, str, int | None]:
    """
    用户登录
    返回 (成功?, 消息, user_id)
    """
    username = username.strip()
    user = _query_sql(
        "SELECT id, password_hash FROM users WHERE username = %s",
        (username,),
        fetchone=True,
    )
    if not user:
        return False, "用户名或密码错误", None

    if not _verify_password(password, user["password_hash"]):
        return False, "用户名或密码错误", None

    return True, "登录成功", user["id"]