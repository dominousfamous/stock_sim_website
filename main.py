import os
from logging import debug
from flask import Flask, session
from flask_session import Session
from tempfile import mkdtemp
from views import views

#Configure application
app = Flask(__name__)

#Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

#Ensure templates are auto-reloaded
app.config['TEMPLATES_AUTO_RELOAD'] = True

#Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

#Configure session to use filesystem(instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#Register blueprint
app.register_blueprint(views)

#Run app
if __name__ == "__main__":
    app.run(debug=True)