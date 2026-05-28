import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import login_required
from database import connect_db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        current_pw  = request.form.get("current_password", "")
        new_pw      = request.form.get("new_password", "")
        confirm_pw  = request.form.get("confirm_password", "")

        if new_pw != confirm_pw:
            flash("New passwords do not match.", "error")
            return redirect(url_for("settings.index"))

        conn = connect_db(row_factory=True)
        user = conn.execute(
            "SELECT * FROM users WHERE username=?", (session["username"],)
        ).fetchone()

        if not bcrypt.checkpw(current_pw.encode(), user["password_hash"].encode()):
            flash("Current password is incorrect.", "error")
            conn.close()
            return redirect(url_for("settings.index"))

        hashed = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "UPDATE users SET password_hash=? WHERE username=?",
            (hashed, session["username"])
        )
        conn.commit()
        conn.close()
        flash("Password changed successfully.", "success")
        return redirect(url_for("settings.index"))

    return render_template("settings.html")
