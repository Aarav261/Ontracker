"""OnTracker web app — token-paste setup + scheduled email briefs."""

from __future__ import annotations

import logging
import os
import secrets

import sentry_sdk
from flask import Flask
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics

from core.jobs import startup
from extensions import limiter
from routes.main import main_bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# Error/performance monitoring. Only initialises when SENTRY_DSN is set, so local
# dev stays quiet and the DSN never lives in source. The Flask integration is
# picked up automatically once flask is importable.
_sentry_dsn = os.environ.get("SENTRY_DSN")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        # Off: this app handles student emails/usernames — don't ship request
        # headers/IPs or PII to Sentry.
        send_default_pii=False,
        # Forward logging.* records to Sentry.
        enable_logs=True,
    )
    log.info("Sentry initialised (env=%s)", os.environ.get("SENTRY_ENVIRONMENT", "production"))

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    CORS(app, resources={r"/*": {"origins": "*"}})

    # Initialize extensions
    limiter.init_app(app)

    # Register blueprints
    app.register_blueprint(main_bp)

    # Prometheus metrics — exposes /metrics with request counts, latencies and
    # process metrics. Guarded because the test suite builds the app repeatedly
    # against the global registry, which would otherwise raise DuplicateTimeseries.
    try:
        metrics = PrometheusMetrics(app)
        metrics.info("ontracker_app_info", "Application info", version="1.13")
    except ValueError:
        pass

    # Startup logic (DB init, restore schedules, start scheduler)
    startup()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
