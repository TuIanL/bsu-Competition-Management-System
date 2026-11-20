from routes.applications import bp as applications_bp
from routes.assignments import bp as assignments_bp
from routes.auth_routes import bp as auth_bp
from routes.catalog import bp as catalog_bp
from routes.dashboard import bp as dashboard_bp
from routes.shifts import bp as shifts_bp
from routes.volunteer_me import bp as volunteer_me_bp
from routes.volunteers import bp as volunteers_bp

ALL_BLUEPRINTS = [
    auth_bp,
    volunteers_bp,
    catalog_bp,
    shifts_bp,
    assignments_bp,
    applications_bp,
    volunteer_me_bp,
    dashboard_bp,
]
