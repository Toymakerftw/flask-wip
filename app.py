from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging
import os

app = Flask(__name__)
app.config.from_object('config.Config')

# Ensure static folder exists
os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

login_manager = LoginManager()
login_manager.login_view = 'signin'
login_manager.init_app(app)

from routes import main
app.register_blueprint(main)

# Initialize the database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
