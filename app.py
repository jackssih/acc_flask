from flask import Flask
from database import init_db
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.manage import manage_bp
from routes.analytics import analytics_bp
from routes.users import users_bp
from routes.settings import settings_bp

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-key-in-production"

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(manage_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(users_bp)
app.register_blueprint(settings_bp)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
