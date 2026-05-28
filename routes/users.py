import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import admin_required, login_required
from database import connect_db

users_bp    = Blueprint("users",    __name__)
settings_bp = Blueprint("settings", __name__)


# ── USER MANAGEMENT ──────────────────────────────────────────────────────────

@users_bp.route("/users")
@admin_required
def index():
    conn  = connect_db(row_factory=True)
    users = conn.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
    conn.close()
    return render_template("users.html", users=[dict(u) for u in users])


@users_bp.route("/users/add", methods=["POST"])
@admin_required
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role     = request.form.get("role", "viewer")

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("users.index"))

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn   = connect_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (username, hashed, role)
        )
        conn.commit()
        flash(f"User '{username}' created.", "success")
    except Exception:
        flash(f"Username '{username}' already exists.", "error")
    finally:
        conn.close()
    return redirect(url_for("users.index"))


@users_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    conn = connect_db(row_factory=True)
    user = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
    if user and user["username"] == session.get("username"):
        flash("You cannot delete your own account.", "error")
        conn.close()
        return redirect(url_for("users.index"))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted.", "success")
    return redirect(url_for("users.index"))


@users_bp.route("/users/change_role/<int:user_id>", methods=["POST"])
@admin_required
def change_role(user_id):
    new_role = request.form.get("role", "viewer")
    conn = connect_db()
    conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    conn.commit()
    conn.close()
    flash("Role updated.", "success")
    return redirect(url_for("users.index"))
