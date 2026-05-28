"""
Run once to create your first admin user:
    python seed_admin.py
"""
import bcrypt
from database import connect_db, init_db

init_db()

username = input("Admin username: ").strip()
password = input("Admin password: ").strip()

hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
conn = connect_db()
try:
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
        (username, hashed, "admin")
    )
    conn.commit()
    print(f"Admin user '{username}' created.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
