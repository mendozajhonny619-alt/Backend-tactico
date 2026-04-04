from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from app.api.routes import register_routes

app = Flask(__name__)
register_routes(app)

# 👇 IMPORTANTE PARA RENDER
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
