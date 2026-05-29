import json
import csv
import io
from flask import Blueprint, render_template, request, Response
from routes.auth import login_required
from database import connect_db

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
@login_required
def index():
    conn = connect_db(row_factory=True)
    rows = conn.execute("""
        SELECT c.identification_no, c.choir, c.gender, c.status,
               g.year_of_graduation
        FROM choir_data c
        LEFT JOIN graduation_data g ON c.identification_no = g.identification_no
    """).fetchall()
    conn.close()
    data = [dict(r) for r in rows]

    total     = len({r["identification_no"] for r in data})
    graduated = len({r["identification_no"] for r in data if r["year_of_graduation"]})
    deceased  = sum(1 for r in data if r["status"] == "deceased")
    grad_rate = round(graduated / total * 100, 1) if total else 0

    male   = sum(1 for r in data if r["gender"] == "M")
    female = sum(1 for r in data if r["gender"] == "F")

    # choir stats
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
    top_choir = choir_stats[0] if choir_stats else {"choir": "—", "rate": 0}

    # yearly trend
    trend = {}
    for r in data:
        if r["year_of_graduation"]:
            yr = int(r["year_of_graduation"])
            trend[yr] = trend.get(yr, 0) + 1
    trend_labels = sorted(trend.keys())
    trend_values = [trend[y] for y in trend_labels]

    # ── Export CSV if ?export=1 ──────────────────────────────
    if request.args.get("export") == "1":
        buf = io.StringIO()
        fields = ["choir", "total", "graduated", "pending", "deceased", "rate"]
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(choir_stats)
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=choir_breakdown.csv"}
        )

    return render_template("analytics.html",
        total=total, graduated=graduated, deceased=deceased,
        grad_rate=grad_rate, male=male, female=female,
        top_choir=top_choir, choir_stats=choir_stats,
        trend_labels=json.dumps([str(y) for y in trend_labels]),
        trend_values=json.dumps(trend_values),
        choir_labels=json.dumps([s["choir"] for s in choir_stats]),
        choir_rates=json.dumps([s["rate"] for s in choir_stats]),
    )
