import sqlite3
import uuid
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "intervyn.db"
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

cur.execute("PRAGMA table_info(users)")
cols = [r[1] for r in cur.fetchall()]
if "session_generation" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN session_generation VARCHAR(64) DEFAULT 'initial_session'")
    cur.execute("SELECT id FROM users")
    user_ids = [r[0] for r in cur.fetchall()]
    for uid in user_ids:
        cur.execute("UPDATE users SET session_generation = ? WHERE id = ?", (str(uuid.uuid4()), uid))
    conn.commit()
    print("Added session_generation column to users table.")
else:
    print("Column session_generation already exists in users table.")

cur.execute("""
CREATE TABLE IF NOT EXISTS revoked_tokens (
    id VARCHAR(36) PRIMARY KEY,
    jti VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(36) NOT NULL,
    session_generation VARCHAR(64),
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS ix_revoked_tokens_jti ON revoked_tokens (jti)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_revoked_tokens_user_id ON revoked_tokens (user_id)")
conn.commit()
conn.close()
print("Auth session migration completed successfully.")
