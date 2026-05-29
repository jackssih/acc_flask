from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from routes.auth import login_required, admin_required
from database import connect_db
import pandas as pd
import json

dashboard_bp = Blueprint("dashboard", __name__)


def load_full_dataset():
    conn = connect_db(row_factory=True)
    rows = conn.execute("""
        SELECT
            c.identification_no, c.name, c.choir, c.gender, c.status, c.comment,
            g.id AS id_grad, g.institute, g.course_name, g.duration, g.year_of_graduation
        FROM choir_data c
        LEFT JOIN graduation_data g ON c.identification_no = g.identification_no
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@dashboard_bp.route("/dashboard")
@login_required
def index():
    data = load_full_dataset()

    total       = len({r["identification_no"] for r in data})
    graduated   = len({r["identification_no"] for r in data if r["year_of_graduation"]})
    not_grad    = total - graduated
    deceased    = sum(1 for r in data if r["status"] == "deceased")

    # choir breakdown
    choir_map = {}
    for r in data:
        c = r["choir"] or "Unknown"
        if c not in choir_map:
            choir_map[c] = {"total": 0, "graduated": 0, "deceased": 0}
        choir_map[c]["total"] += 1
        if r["year_of_graduation"]:
            choir_map[c]["graduated"] += 1
        if r["status"] == "deceased":
            choir_map[c]["deceased"] += 1

    choir_stats = []
    for name, s in choir_map.items():
        rate = round(s["graduated"] / s["total"] * 100, 1) if s["total"] else 0
        choir_stats.append({
            "choir": name, "total": s["total"],
            "graduated": s["graduated"], "deceased": s["deceased"],
            "pending": s["total"] - s["graduated"] - s["deceased"],
            "rate": rate,
        })
    choir_stats.sort(key=lambda x: x["rate"], reverse=True)

    # graduation trend
    trend = {}
    for r in data:
        if r["year_of_graduation"]:
            yr = int(r["year_of_graduation"])
            trend[yr] = trend.get(yr, 0) + 1
    trend_labels = sorted(trend.keys())
    trend_values = [trend[y] for y in trend_labels]

    # recent graduates
    recent = [r for r in data if r["year_of_graduation"]]
    recent.sort(key=lambda x: x["year_of_graduation"] or 0, reverse=True)
    recent = recent[:10]

    return render_template("dashboard.html",
        total=total, graduated=graduated, not_grad=not_grad, deceased=deceased,
        choir_stats=choir_stats[:6],
        trend_labels=[str(y) for y in trend_labels],
        trend_values=trend_values,
        recent=recent,
    )


@dashboard_bp.route("/dashboard/search")
@login_required
def search():
    query      = request.args.get("q", "").strip()
    choir_f    = request.args.get("choir", "")
    gender_f   = request.args.get("gender", "")
    status_f   = request.args.get("status", "")

    data = load_full_dataset()

    # unique filter options
    choirs = sorted({r["choir"] for r in data if r["choir"]})

    results = data
    if query:
        ql = query.lower()
        results = [r for r in results if
                   ql in (r["name"] or "").lower() or
                   ql in (r["identification_no"] or "").lower()]
    if choir_f:
        results = [r for r in results if r["choir"] == choir_f]
    if gender_f:
        results = [r for r in results if r["gender"] == gender_f]
    if status_f == "graduated":
        results = [r for r in results if r["year_of_graduation"]]
    elif status_f == "not_graduated":
        results = [r for r in results if not r["year_of_graduation"]]
    elif status_f == "deceased":
        results = [r for r in results if r["status"] == "deceased"]

    return render_template("search_results.html",
        results=results, query=query,
        choir_f=choir_f, gender_f=gender_f, status_f=status_f,
        choirs=choirs,
    )


@dashboard_bp.route("/dashboard/view/<view_type>")
@login_required
def view(view_type):
    data = load_full_dataset()
    query = request.args.get("q", "").strip()

    if view_type == "all":
        rows = data
    elif view_type == "graduated":
        rows = [r for r in data if r["year_of_graduation"]]
    elif view_type == "not_graduated":
        rows = [r for r in data if not r["year_of_graduation"]]
    elif view_type == "deceased":
        rows = [r for r in data if r["status"] == "deceased"]
    else:
        rows = data

    if query:
        ql = query.lower()
        rows = [r for r in rows if
                ql in (r["name"] or "").lower() or
                ql in (r["identification_no"] or "").lower()]

    return render_template("table_view.html",
        rows=rows, view_type=view_type,
        is_admin=(session.get("role") == "admin"),
        query=query,
    )


@dashboard_bp.route("/dashboard/save_status", methods=["POST"])
@admin_required
def save_status():
    identification_no = request.form.get("identification_no")
    status  = request.form.get("status")
    comment = request.form.get("comment", "")
    conn = connect_db()
    conn.execute(
        "UPDATE choir_data SET status=?, comment=? WHERE identification_no=?",
        (status, comment, identification_no)
    )
    conn.commit()
    conn.close()
    flash("Record updated.", "success")
    return redirect(request.referrer or url_for("dashboard.index"))


@dashboard_bp.route("/dashboard/save_graduation", methods=["POST"])
@admin_required
def save_graduation():
    identification_no = request.form.get("identification_no")
    institute = request.form.get("institute", "")
    course    = request.form.get("course", "")
    year      = request.form.get("year", "")

    if not all([institute, course, year]):
        flash("All graduation fields are required.", "error")
        return redirect(request.referrer or url_for("dashboard.index"))

    conn = connect_db()
    conn.execute("""
        INSERT INTO graduation_data (identification_no, institute, course_name, year_of_graduation)
        VALUES (?, ?, ?, ?)
    """, (identification_no, institute, course, int(year)))
    conn.commit()
    conn.close()
    flash("Graduation record saved.", "success")
    return redirect(request.referrer or url_for("dashboard.index"))


@dashboard_bp.route("/dashboard/remove_graduation", methods=["POST"])
@admin_required
def remove_graduation():
    grad_id           = request.form.get("grad_id")
    identification_no = request.form.get("identification_no")

    if not grad_id:
        flash("No graduation record found to remove.", "error")
        return redirect(request.referrer or url_for("dashboard.index"))

    conn = connect_db()
    conn.execute("DELETE FROM graduation_data WHERE id=? AND identification_no=?",
                 (grad_id, identification_no))
    conn.commit()
    conn.close()
    flash("Graduation record removed. Student moved back to Not Graduated.", "success")
    return redirect(url_for("dashboard.view", view_type="not_graduated"))


@dashboard_bp.route("/dashboard/export/<view_type>")
@login_required
def export(view_type):
    import csv, io
    from flask import Response

    data = load_full_dataset()
    if view_type == "graduated":
        rows = [r for r in data if r["year_of_graduation"]]
        fields = ["name", "choir", "gender", "status", "institute", "course_name", "year_of_graduation"]
    elif view_type == "not_graduated":
        rows = [r for r in data if not r["year_of_graduation"]]
        fields = ["identification_no", "name", "choir", "gender", "status"]
    elif view_type == "deceased":
        rows = [r for r in data if r["status"] == "deceased"]
        fields = ["name", "choir", "gender", "comment"]
    else:
        rows = data
        fields = ["identification_no", "name", "choir", "gender", "status"]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={view_type}_students.csv"}
    )
