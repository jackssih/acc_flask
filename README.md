# ACC Archives — Flask App

## Project Structure
```
acc_flask/
├── app.py                  # Flask entry point
├── database.py             # SQLite connection + schema
├── seed_admin.py           # Run once to create first admin
├── requirements.txt
├── Procfile                # For Railway/Render deployment
├── routes/
│   ├── auth.py             # Login, logout, decorators
│   ├── dashboard.py        # Dashboard, search, table views
│   ├── manage.py           # Upload, add, delete students
│   ├── analytics.py        # Analytics page
│   ├── users.py            # User management
│   └── settings.py         # Account settings
├── templates/
│   ├── base.html           # Sidebar layout (all pages inherit this)
│   ├── login.html          # Standalone login page
│   ├── dashboard.html
│   ├── table_view.html     # All/graduated/not_graduated/deceased
│   ├── search_results.html
│   ├── manage.html
│   ├── analytics.html
│   ├── users.html
│   └── settings.html
└── static/
    ├── css/main.css
    ├── js/main.js
    └── img/                # Place slide1.jpg … slide5.jpg here
```

## Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your admin user
python seed_admin.py

# 3. Run the app
python app.py
# → http://localhost:5000
```

## Migrate existing SQLite data
If you have an existing `choir_data.db` from your Streamlit app,
just copy it into the project root — the schema is identical.

## Deployment (Railway or Render — free tier, persistent disk)

### Railway
1. Push to a GitHub repo
2. New project → Deploy from GitHub
3. Add environment variable: `SECRET_KEY=your-random-secret`
4. Add a Volume (persistent disk) mounted at `/app` so the SQLite file survives restarts
5. Railway auto-detects the Procfile

### Render
1. New Web Service → connect GitHub repo
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add a Disk (persistent storage) mounted at `/app`

## Slide images
Place `slide1.jpg` through `slide5.jpg` in `static/img/`.
The login page will auto-detect and use whichever ones exist.

## Production: change the secret key
In `app.py` replace:
```python
app.secret_key = "change-this-to-a-random-secret-key-in-production"
```
with an environment variable:
```python
import os
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-key")
```
