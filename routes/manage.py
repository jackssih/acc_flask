import uuid, io
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from routes.auth import admin_required
from database import connect_db

manage_bp = Blueprint("manage", __name__)


def generate_id():
    return "ACC-" + str(uuid.uuid4())[:8].upper()


@manage_bp.route("/manage", methods=["GET"])
@admin_required
def index():
    return render_template("manage.html")


@manage_bp.route("/manage/add_student", methods=["POST"])
@admin_required
def add_student():
    name   = request.form.get("name", "").strip()
    choir  = request.form.get("choir", "").strip()
    gender = request.form.get("gender", "M")
    status = request.form.get("status", "alive")

    if not name or not choir:
        flash("Name and choir are required.", "error")
        return redirect(url_for("manage.index"))

    student_id = generate_id()
    conn = connect_db()
    conn.execute(
        "INSERT INTO choir_data (identification_no, name, choir, gender, status) VALUES (?,?,?,?,?)",
        (student_id, name, choir, gender, status)
    )
    conn.commit()
    conn.close()
    flash(f"Student '{name}' added successfully.", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/delete_student", methods=["POST"])
@admin_required
def delete_student():
    name    = request.form.get("name", "").strip()
    confirm = request.form.get("confirm")

    if not name:
        flash("Please enter a student name.", "error")
        return redirect(url_for("manage.index"))
    if not confirm:
        flash("Please check the confirmation box.", "error")
        return redirect(url_for("manage.index"))

    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("SELECT identification_no FROM choir_data WHERE name = ?", (name,))
    matches = cur.fetchall()

    if not matches:
        flash(f"No student found with name '{name}'.", "error")
        conn.close()
        return redirect(url_for("manage.index"))

    for (idn,) in matches:
        conn.execute("DELETE FROM graduation_data WHERE identification_no = ?", (idn,))
        conn.execute("DELETE FROM choir_data WHERE identification_no = ?", (idn,))

    conn.commit()
    conn.close()
    flash(f"Removed {len(matches)} record(s) for '{name}'.", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/upload_choir", methods=["POST"])
@admin_required
def upload_choir():
    f = request.files.get("choir_file")
    if not f:
        flash("No file selected.", "error")
        return redirect(url_for("manage.index"))

    try:
        df = pd.read_excel(f) if f.filename.endswith(".xlsx") else pd.read_csv(f)
    except Exception as e:
        flash(f"Could not read file: {e}", "error")
        return redirect(url_for("manage.index"))

    required = {"name", "choir", "gender"}
    if missing := required - set(df.columns):
        flash(f"Missing columns: {missing}", "error")
        return redirect(url_for("manage.index"))

    df["status"]  = df.get("status",  pd.Series(["alive"] * len(df))).fillna("alive")
    df["comment"] = df.get("comment", pd.Series([""]     * len(df))).fillna("")

    conn = connect_db()
    inserted = 0
    for _, row in df.iterrows():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO choir_data (identification_no,name,choir,gender,status,comment) VALUES (?,?,?,?,?,?)",
                (generate_id(), str(row["name"]), str(row["choir"]),
                 str(row["gender"]), str(row["status"]), str(row["comment"]))
            )
            inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    flash(f"Uploaded {inserted} choir records.", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/upload_graduation", methods=["POST"])
@admin_required
def upload_graduation():
    f = request.files.get("grad_file")
    if not f:
        flash("No file selected.", "error")
        return redirect(url_for("manage.index"))

    try:
        df = pd.read_excel(f) if f.filename.endswith(".xlsx") else pd.read_csv(f)
    except Exception as e:
        flash(f"Could not read file: {e}", "error")
        return redirect(url_for("manage.index"))

    if "identification_no" not in df.columns:
        flash("Missing column: identification_no", "error")
        return redirect(url_for("manage.index"))

    conn = connect_db()
    inserted = 0
    for _, row in df.iterrows():
        try:
            conn.execute(
                "INSERT INTO graduation_data (identification_no,institute,course_name,duration,year_of_graduation) VALUES (?,?,?,?,?)",
                (str(row["identification_no"]),
                 str(row.get("institute", "") or ""),
                 str(row.get("course_name", "") or ""),
                 str(row.get("duration", "") or ""),
                 int(row["year_of_graduation"]) if pd.notna(row.get("year_of_graduation")) else None)
            )
            inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    flash(f"Uploaded {inserted} graduation records.", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/template/<kind>")
@admin_required
def download_template(kind):
    if kind == "choir":
        header = "name,choir,gender,status\n"
        fname  = "choir_template.csv"
    else:
        header = "identification_no,name,institute,course_name,duration,year_of_graduation\n"
        fname  = "graduation_template.csv"

    return Response(header, mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={fname}"})
import uuid, io
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from routes.auth import admin_required
from database import connect_db

manage_bp = Blueprint("manage", __name__)


def generate_id():
    return "ACC-" + str(uuid.uuid4())[:8].upper()


def load_full_dataset():
    """Load and merge choir and graduation data"""
    conn = connect_db()

    choir = pd.read_sql("SELECT * FROM choir_data", conn)
    grad = pd.read_sql("SELECT * FROM graduation_data", conn)

    conn.close()

    if choir.empty:
        return pd.DataFrame()

    choir["identification_no"] = choir["identification_no"].astype(str).str.strip()
    if not grad.empty:
        grad["identification_no"] = grad["identification_no"].astype(str).str.strip()

    choir = choir.drop_duplicates(subset=["identification_no"])

    if not grad.empty:
        grad["year_of_graduation"] = pd.to_numeric(grad["year_of_graduation"], errors="coerce")
        grad = grad.sort_values("year_of_graduation").drop_duplicates(
            subset=["identification_no"], keep="last"
        )

        # Only keep needed columns from grad to avoid name_x / name_y collision
        grad_cols = ["identification_no", "institute", "course_name", "year_of_graduation"]
        grad = grad[[c for c in grad_cols if c in grad.columns]]

        df = pd.merge(choir, grad, on="identification_no", how="left")
    else:
        df = choir.copy()

    required = ["name", "choir", "gender", "status", "institute", "course_name", "year_of_graduation", "comment"]
    for col in required:
        if col not in df.columns:
            df[col] = None

    df["name"] = df["name"].fillna("Unknown")
    df["graduated"] = df["year_of_graduation"].notna()
    df["status"] = df["status"].fillna("alive")

    return df


@manage_bp.route("/manage", methods=["GET"])
@admin_required
def index():
    return render_template("manage.html")


@manage_bp.route("/manage/add_student", methods=["POST"])
@admin_required
def add_student():
    name   = request.form.get("name", "").strip()
    choir  = request.form.get("choir", "").strip()
    gender = request.form.get("gender", "M")
    status = request.form.get("status", "alive")

    if not name or not choir:
        flash("Name and choir are required.", "error")
        return redirect(url_for("manage.index"))

    conn = connect_db()
    
    # Check for duplicate name before inserting
    existing = conn.execute(
        "SELECT name FROM choir_data WHERE name = ?", (name,)
    ).fetchone()
    
    if existing:
        flash(f"A student with name '{name}' already exists. Please use a different name or delete the existing record.", "error")
        conn.close()
        return redirect(url_for("manage.index"))
    
    student_id = generate_id()
    conn.execute(
        "INSERT INTO choir_data (identification_no, name, choir, gender, status) VALUES (?,?,?,?,?)",
        (student_id, name, choir, gender, status)
    )
    conn.commit()
    conn.close()
    
    flash(f"Student '{name}' added successfully with ID: {student_id}", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/delete_student", methods=["POST"])
@admin_required
def delete_student():
    name    = request.form.get("name", "").strip()
    confirm = request.form.get("confirm")

    if not name:
        flash("Please enter a student name.", "error")
        return redirect(url_for("manage.index"))
    if not confirm:
        flash("Please check the confirmation box.", "error")
        return redirect(url_for("manage.index"))

    conn = connect_db()
    cur  = conn.cursor()
    cur.execute("SELECT identification_no FROM choir_data WHERE name = ?", (name,))
    matches = cur.fetchall()

    if not matches:
        flash(f"No student found with name '{name}'.", "error")
        conn.close()
        return redirect(url_for("manage.index"))

    for (idn,) in matches:
        conn.execute("DELETE FROM graduation_data WHERE identification_no = ?", (idn,))
        conn.execute("DELETE FROM choir_data WHERE identification_no = ?", (idn,))

    conn.commit()
    conn.close()
    
    flash(f"Removed {len(matches)} record(s) for '{name}'.", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/upload_choir", methods=["POST"])
@admin_required
def upload_choir():
    f = request.files.get("choir_file")
    if not f:
        flash("No file selected.", "error")
        return redirect(url_for("manage.index"))

    try:
        df = pd.read_excel(f) if f.filename.endswith(".xlsx") else pd.read_csv(f)
    except Exception as e:
        flash(f"Could not read file: {e}", "error")
        return redirect(url_for("manage.index"))

    # Check required columns (including identification_no)
    required = {"identification_no", "name", "choir", "gender"}
    if missing := required - set(df.columns):
        flash(f"Missing columns: {missing}", "error")
        return redirect(url_for("manage.index"))

    # Fill missing optional columns
    df["status"]  = df.get("status",  pd.Series(["alive"] * len(df))).fillna("alive")
    df["comment"] = df.get("comment", pd.Series([""] * len(df))).fillna("")

    conn = connect_db()
    inserted = 0
    duplicate_ids = 0
    duplicate_names = 0
    errors = 0
    
    # Track unique IDs and names in current upload to prevent duplicates within file
    seen_ids = set()
    seen_names = set()
    
    for _, row in df.iterrows():
        try:
            # Clean the identification_no
            id_no = str(row["identification_no"]).strip()
            name = str(row["name"]).strip()
            
            # Check for duplicate ID within the same upload
            if id_no in seen_ids:
                duplicate_ids += 1
                print(f"Duplicate ID '{id_no}' found within upload file")
                continue
            
            # Check for duplicate name within the same upload
            if name in seen_names:
                duplicate_names += 1
                print(f"Duplicate name '{name}' found within upload file")
                continue
            
            # Check if student already exists by identification_no in database
            existing_by_id = conn.execute(
                "SELECT identification_no FROM choir_data WHERE identification_no = ?", 
                (id_no,)
            ).fetchone()
            
            if existing_by_id:
                duplicate_ids += 1
                print(f"ID '{id_no}' already exists in database")
                continue
            
            # Check if student already exists by name in database
            existing_by_name = conn.execute(
                "SELECT name FROM choir_data WHERE name = ?", 
                (name,)
            ).fetchone()
            
            if existing_by_name:
                duplicate_names += 1
                print(f"Name '{name}' already exists in database")
                continue
            
            # Insert new record with provided identification_no
            conn.execute(
                "INSERT INTO choir_data (identification_no, name, choir, gender, status, comment) VALUES (?,?,?,?,?,?)",
                (id_no, name, str(row["choir"]),
                 str(row["gender"]), str(row["status"]), str(row["comment"]))
            )
            inserted += 1
            seen_ids.add(id_no)
            seen_names.add(name)
                
        except Exception as e:
            errors += 1
            print(f"Error inserting row: {e}")
            
    conn.commit()
    conn.close()
    
    # Reload merged dataset after upload
    merged_df = load_full_dataset()
    
    flash(f"Uploaded choir records - Inserted: {inserted}, Duplicate IDs: {duplicate_ids}, Duplicate Names: {duplicate_names}, Errors: {errors}", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/upload_graduation", methods=["POST"])
@admin_required
def upload_graduation():
    f = request.files.get("grad_file")
    if not f:
        flash("No file selected.", "error")
        return redirect(url_for("manage.index"))

    try:
        df = pd.read_excel(f) if f.filename.endswith(".xlsx") else pd.read_csv(f)
    except Exception as e:
        flash(f"Could not read file: {e}", "error")
        return redirect(url_for("manage.index"))

    # Check required columns
    required = {"identification_no", "year_of_graduation"}
    if missing := required - set(df.columns):
        flash(f"Missing columns: {missing}", "error")
        return redirect(url_for("manage.index"))

    conn = connect_db()
    inserted = 0
    duplicate_ids = 0
    id_not_found = 0
    errors = 0
    
    # Track unique IDs in current upload to prevent duplicates within file
    seen_ids = set()
    
    for _, row in df.iterrows():
        try:
            # Clean the identification_no
            id_no = str(row["identification_no"]).strip()
            
            # Check for duplicate ID within the same upload
            if id_no in seen_ids:
                duplicate_ids += 1
                print(f"Duplicate ID '{id_no}' found within upload file")
                continue
            
            # Verify that the identification_no exists in choir_data
            exists = conn.execute(
                "SELECT identification_no FROM choir_data WHERE identification_no = ?",
                (id_no,)
            ).fetchone()
            
            if not exists:
                id_not_found += 1
                print(f"Warning: ID {id_no} not found in choir_data")
                continue
            
            # Check if graduation record already exists for this ID
            existing = conn.execute(
                "SELECT identification_no FROM graduation_data WHERE identification_no = ?",
                (id_no,)
            ).fetchone()
            
            if existing:
                duplicate_ids += 1
                print(f"Graduation record already exists for ID '{id_no}'")
                continue
            
            # Handle year_of_graduation properly
            year = None
            if pd.notna(row.get("year_of_graduation")):
                try:
                    year = int(float(row["year_of_graduation"]))
                except (ValueError, TypeError):
                    year = None
            
            # Insert new record
            conn.execute(
                "INSERT INTO graduation_data (identification_no, institute, course_name, duration, year_of_graduation) VALUES (?,?,?,?,?)",
                (id_no,
                 str(row.get("institute", "") or ""),
                 str(row.get("course_name", "") or ""),
                 str(row.get("duration", "") or ""),
                 year)
            )
            inserted += 1
            seen_ids.add(id_no)
            
        except Exception as e:
            errors += 1
            print(f"Error on row: {e}")
            
    conn.commit()
    conn.close()
    
    # Reload merged dataset after upload
    merged_df = load_full_dataset()
    
    flash(f"Uploaded graduation records - Inserted: {inserted}, Duplicate IDs: {duplicate_ids}, ID Not Found in Choir: {id_not_found}, Errors: {errors}", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/template/<kind>")
@admin_required
def download_template(kind):
    if kind == "choir":
        # Include identification_no in the template
        header = "identification_no,name,choir,gender,status,comment\n"
        # Add sample data as comments or just header
        sample = "# Example: ACC-12345678,John Doe,Tenor,M,alive,\n"
        content = header + sample
        fname = "choir_template.csv"
    else:
        # Graduation template with identification_no
        header = "identification_no,institute,course_name,duration,year_of_graduation\n"
        sample = "# Example: ACC-12345678,XYZ University,Computer Science,4 Years,2024\n"
        content = header + sample
        fname = "graduation_template.csv"
    
    return Response(content, mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={fname}"})


@manage_bp.route("/manage/remove_duplicates", methods=["POST"])
@admin_required
def remove_duplicates():
    """Utility route to clean existing duplicates from database"""
    conn = connect_db()
    
    # Find and remove duplicate choir records (keeping the first one)
    choir_duplicates = conn.execute("""
        DELETE FROM choir_data 
        WHERE identification_no IN (
            SELECT identification_no FROM choir_data 
            GROUP BY identification_no 
            HAVING COUNT(*) > 1
        )
        AND identification_no NOT IN (
            SELECT MIN(identification_no) FROM choir_data 
            GROUP BY identification_no 
            HAVING COUNT(*) > 1
        )
    """)
    
    # Find and remove duplicate graduation records
    grad_duplicates = conn.execute("""
        DELETE FROM graduation_data 
        WHERE identification_no IN (
            SELECT identification_no FROM graduation_data 
            GROUP BY identification_no 
            HAVING COUNT(*) > 1
        )
        AND identification_no NOT IN (
            SELECT MIN(identification_no) FROM graduation_data 
            GROUP BY identification_no 
            HAVING COUNT(*) > 1
        )
    """)
    
    conn.commit()
    conn.close()
    
    flash(f"Removed duplicate records from database", "success")
    return redirect(url_for("manage.index"))


@manage_bp.route("/manage/view_merged_data")
@admin_required
def view_merged_data():
    """Optional route to view the merged dataset"""
    merged_df = load_full_dataset()
    
    if merged_df.empty:
        flash("No data available", "info")
        return redirect(url_for("manage.index"))
    
    # Convert to HTML table or JSON
    table_html = merged_df.to_html(classes='table table-striped', index=False)
    
    return render_template("merged_data.html", table=table_html, count=len(merged_df))