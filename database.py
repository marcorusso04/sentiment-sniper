import os
import sqlite3

DATABASE_PATH = "tokens.db"


def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shop_tokens (
                shop TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_token(shop: str, token: str):
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            INSERT INTO shop_tokens (shop, access_token)
            VALUES (?, ?)
            ON CONFLICT(shop) DO UPDATE SET access_token=excluded.access_token
        """, (shop, token))
        conn.commit()


def load_token(shop: str) -> str | None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute(
            "SELECT access_token FROM shop_tokens WHERE shop = ?", (shop,)
        ).fetchone()
    return row[0] if row else None
