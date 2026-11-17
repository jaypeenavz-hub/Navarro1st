"""Application factory for ByteBodega."""

import os
import re

from flask import Flask, g, render_template, session

from . import db

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    db.init_app(app)

    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .cart import bp as cart_bp
    from .checkout import bp as checkout_bp
    from .notifications import bp as notifications_bp
    from .orders import bp as orders_bp
    from .profile import bp as profile_bp
    from .shop import bp as shop_bp

    for blueprint in (auth_bp, shop_bp, cart_bp, checkout_bp, orders_bp,
                      profile_bp, notifications_bp, admin_bp):
        app.register_blueprint(blueprint)

    from .services import (cart_count, initials, money, nice_date, nice_datetime,
                           unread_count)

    app.jinja_env.filters["money"] = money
    app.jinja_env.filters["datetime_ph"] = nice_datetime
    app.jinja_env.filters["date_ph"] = nice_date
    app.jinja_env.filters["initials"] = initials

    @app.before_request
    def load_signed_in_user():
        g.user = None
        user_id = session.get("user_id")
        if user_id is None:
            return
        row = db.get_db().execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None or not row["is_active"]:
            session.clear()
            return
        g.user = row

    @app.context_processor
    def shared_template_state():
        user = g.get("user")
        return {
            "current_user": user,
            "nav_cart_count": cart_count(user["id"]) if user else 0,
            "nav_unread_count": unread_count(user["id"]) if user else 0,
        }

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    return app
