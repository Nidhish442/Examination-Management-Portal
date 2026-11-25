
from flask import Flask
from application.database import db


def create_app():

    app = Flask(__name__)

    app.debug = True

    app.config['SECRET_KEY'] = 'emp-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///e-dine.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    return app


app = create_app()


# Import only the route registration function
from application.controllers import register_routes

# Register all application routes
register_routes(app)


if __name__ == '__main__':

    with app.app_context():

        db.create_all()

        from application.models import User

        admin_user = User.query.filter_by(
            email="admin@123.com",
            role="admin"
        ).first()

        if not admin_user:

            admin_user = User(
                username="admin",
                full_name="System Administrator",
                email="admin@123.com",
                role="admin",
                status="Active"
            )

            admin_user.set_password("admin123")

            db.session.add(admin_user)
            db.session.commit()

    app.run(debug=True)
