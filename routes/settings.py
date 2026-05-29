import os
import bcrypt
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, send_file, current_app)
from routes.auth import login_required, admin_required
from database import connect_db

settings_bp = Blueprint('settings', __name__)

# ── point this at your actual .db file ───────────────────────
_DB_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "choir_data.db"
)


# ── change password ───────────────────────────────────────────
@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw     = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

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


# ── backup to computer ────────────────────────────────────────
@settings_bp.route("/settings/backup/local")
@login_required
def backup_local():
    if not os.path.exists(_DB_FILE):
        flash("Database file not found. Check _DB_FILE path in settings.py.", "error")
        return redirect(url_for("settings.index"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        _DB_FILE,
        as_attachment=True,
        download_name=f"acc_backup_{timestamp}.db",
        mimetype="application/octet-stream"
    )


# ── backup to cloud (Dropbox) ─────────────────────────────────
@settings_bp.route("/settings/backup/cloud", methods=["POST"])
@admin_required
def backup_cloud():
    token = current_app.config.get("DROPBOX_TOKEN", "").strip()

    if not token:
        flash(
            "No Dropbox token configured. "
            "Add DROPBOX_TOKEN = 'your_token' to your app config.",
            "error"
        )
        return redirect(url_for("settings.index"))

    try:
        import dropbox                                  # pip install dropbox
        from dropbox.exceptions import AuthError, ApiError

        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        remote_path = f"/ACC_Backups/acc_backup_{timestamp}.db"

        dbx = dropbox.Dropbox(token)
        with open(_DB_FILE, "rb") as f:
            dbx.files_upload(
                f.read(), remote_path,
                mode=dropbox.files.WriteMode.overwrite,
                mute=True
            )
        flash(f"Backup saved to Dropbox → {remote_path}", "success")

    except ImportError:
        flash("Dropbox SDK missing. Run:  pip install dropbox", "error")
    except AuthError:
        flash("Dropbox authentication failed. Check your DROPBOX_TOKEN.", "error")
    except Exception as e:
        flash(f"Cloud backup failed: {e}", "error")

    return redirect(url_for("settings.index"))
