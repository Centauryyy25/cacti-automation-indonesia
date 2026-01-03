"""Root shim to launch the Flask app from the web package."""

from web.app import app

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

