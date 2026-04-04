from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from app.api.routes import api_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
