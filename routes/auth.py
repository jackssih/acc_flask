import bcrypt
from functools import wraps
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from database import connect_db

auth_bp = Blueprint("auth", __name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def get_user(username: str):
    conn = connect_db(row_factory=True)
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return user


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


# ── routes ───────────────────────────────────────────────────────────────────

@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("auth"):
        return redirect(url_for("dashboard.index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user(username)
        if user and verify_password(password, user["password_hash"]):
            session["auth"]     = True
            session["username"] = user["username"]
            session["role"]     = user["role"]
            return redirect(url_for("dashboard.index"))
        else:
            error = "Incorrect username or password."

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
