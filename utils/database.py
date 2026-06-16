"""
数据库模块 - 支持本地 SQLite 和云端 Neon PostgreSQL 双模式

本地开发：自动使用 data/tracker.db (SQLite)
云端部署：设置 DATABASE_URL 环境变量即可切换到 PostgreSQL
"""

import os
import sqlite3
from datetime import datetime, timedelta

# ---------- 数据库连接 ----------
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # ------------------ PostgreSQL (Neon) ------------------
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # 清理连接串：去掉 psycopg2 不支持的参数（如 channel_binding）
    _base_url = DATABASE_URL.split("?")[0]
    _full_url = _base_url + "?sslmode=require"

    def get_connection():
        conn = psycopg2.connect(_full_url)
        conn.autocommit = True
        return conn

    def _query(sql, params=None, fetchone=False):
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                if sql.strip().upper().startswith("SELECT"):
                    rows = cur.fetchall()
                    result = [dict(r) for r in rows]
                    if fetchone:
                        return result[0] if result else None
                    return result
                return None
        finally:
            conn.close()

    def _execute(sql, params=None):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur
        finally:
            conn.close()

    def init_db():
        # 用户表
        _execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 物品表
        _execute("""
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '其他',
                purchase_date TEXT NOT NULL,
                shelf_life_days INTEGER NOT NULL,
                expire_date TEXT NOT NULL,
                is_notified INTEGER NOT NULL DEFAULT 0
            )
        """)
        # 迁移：给旧表加 user_id 列（如果不存在可以忽略错误）
        try:
            _execute("ALTER TABLE items ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        except Exception:
            pass

    def add_item(user_id, name, category, purchase_date, shelf_life_days):
        purchase = datetime.strptime(purchase_date, "%Y-%m-%d")
        expire = purchase + timedelta(days=shelf_life_days)
        expire_date = expire.strftime("%Y-%m-%d")
        _execute(
            "INSERT INTO items (user_id, name, category, purchase_date, shelf_life_days, expire_date) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, name, category, purchase_date, shelf_life_days, expire_date),
        )

    def get_all_items(user_id=None):
        if user_id:
            return _query("SELECT * FROM items WHERE user_id = %s ORDER BY expire_date ASC", (user_id,))
        return _query("SELECT * FROM items ORDER BY expire_date ASC")

    def get_expiring_soon_items(days=5, user_id=None):
        today = datetime.today().strftime("%Y-%m-%d")
        deadline = (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")
        if user_id:
            return _query(
                "SELECT * FROM items WHERE user_id = %s AND expire_date BETWEEN %s AND %s AND is_notified = 0 "
                "ORDER BY expire_date ASC",
                (user_id, today, deadline),
            )
        return _query(
            "SELECT * FROM items WHERE expire_date BETWEEN %s AND %s AND is_notified = 0 "
            "ORDER BY expire_date ASC",
            (today, deadline),
        )

    def get_expired_items(user_id=None):
        today = datetime.today().strftime("%Y-%m-%d")
        if user_id:
            return _query(
                "SELECT * FROM items WHERE user_id = %s AND expire_date < %s ORDER BY expire_date ASC",
                (user_id, today),
            )
        return _query(
            "SELECT * FROM items WHERE expire_date < %s ORDER BY expire_date ASC",
            (today,),
        )

    def mark_notified(item_id):
        _execute("UPDATE items SET is_notified = 1 WHERE id = %s", (item_id,))

    def delete_item(item_id):
        _execute("DELETE FROM items WHERE id = %s", (item_id,))

    def get_shopping_suggestions(user_id=None):
        today = datetime.today().strftime("%Y-%m-%d")
        deadline = (datetime.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        if user_id:
            rows = _query(
                "SELECT * FROM items WHERE user_id = %s AND (expire_date < %s OR "
                "(expire_date BETWEEN %s AND %s)) ORDER BY category, expire_date ASC",
                (user_id, today, today, deadline),
            )
        else:
            rows = _query(
                "SELECT * FROM items WHERE expire_date < %s OR "
                "(expire_date BETWEEN %s AND %s) ORDER BY category, expire_date ASC",
                (today, today, deadline),
            )
        return rows

    # ---------- 统一导出函数 ----------
    def _execute_sql(sql, params=None): return _execute(sql, params)
    def _query_sql(sql, params=None, fetchone=False): return _query(sql, params, fetchone=fetchone)
    is_postgres = True

else:
    # ------------------ SQLite (本地开发) ------------------
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    DB_PATH = os.path.join(DB_DIR, "tracker.db")

    def get_connection():
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db():
        conn = get_connection()
        # 用户表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # 物品表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '其他',
                purchase_date TEXT NOT NULL,
                shelf_life_days INTEGER NOT NULL,
                expire_date TEXT NOT NULL,
                is_notified INTEGER NOT NULL DEFAULT 0
            )
        """)
        # 迁移：给旧表加 user_id 列
        try:
            conn.execute("ALTER TABLE items ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        except Exception:
            pass
        conn.commit()
        conn.close()

    def add_item(user_id, name, category, purchase_date, shelf_life_days):
        purchase = datetime.strptime(purchase_date, "%Y-%m-%d")
        expire = purchase + timedelta(days=shelf_life_days)
        expire_date = expire.strftime("%Y-%m-%d")
        conn = get_connection()
        conn.execute(
            "INSERT INTO items (user_id, name, category, purchase_date, shelf_life_days, expire_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, category, purchase_date, shelf_life_days, expire_date),
        )
        conn.commit()
        conn.close()

    def get_all_items(user_id=None):
        conn = get_connection()
        if user_id:
            rows = conn.execute("SELECT * FROM items WHERE user_id = ? ORDER BY expire_date ASC", (user_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM items ORDER BY expire_date ASC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_expiring_soon_items(days=5, user_id=None):
        today = datetime.today().strftime("%Y-%m-%d")
        deadline = (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")
        conn = get_connection()
        if user_id:
            rows = conn.execute(
                "SELECT * FROM items WHERE user_id = ? AND expire_date BETWEEN ? AND ? AND is_notified = 0 "
                "ORDER BY expire_date ASC",
                (user_id, today, deadline),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM items WHERE expire_date BETWEEN ? AND ? AND is_notified = 0 "
                "ORDER BY expire_date ASC",
                (today, deadline),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_expired_items(user_id=None):
        conn = get_connection()
        today = datetime.today().strftime("%Y-%m-%d")
        if user_id:
            rows = conn.execute(
                "SELECT * FROM items WHERE user_id = ? AND expire_date < ? ORDER BY expire_date ASC",
                (user_id, today),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM items WHERE expire_date < ? ORDER BY expire_date ASC",
                (today,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_notified(item_id):
        conn = get_connection()
        conn.execute("UPDATE items SET is_notified = 1 WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    def delete_item(item_id):
        conn = get_connection()
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    def get_shopping_suggestions(user_id=None):
        today = datetime.today().strftime("%Y-%m-%d")
        deadline = (datetime.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        conn = get_connection()
        if user_id:
            rows = conn.execute(
                "SELECT * FROM items WHERE user_id = ? AND (expire_date < ? OR "
                "(expire_date BETWEEN ? AND ?)) ORDER BY category, expire_date ASC",
                (user_id, today, today, deadline),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM items WHERE expire_date < ? OR "
                "(expire_date BETWEEN ? AND ?) ORDER BY category, expire_date ASC",
                (today, today, deadline),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---------- 统一导出函数 ----------
    def _execute_sql(sql, params=None):
        conn = get_connection()
        try:
            cur = conn.execute(sql, params or ())
            conn.commit()
            return cur
        finally:
            conn.close()

    def _query_sql(sql, params=None, fetchone=False):
        conn = get_connection()
        try:
            rows = conn.execute(sql, params or ()).fetchall()
            result = [dict(r) for r in rows]
            if fetchone:
                return result[0] if result else None
            return result
        finally:
            conn.close()

    is_postgres = False