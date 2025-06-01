# run.py
# This script creates the Flask app instance from the 'app' package
# and runs the development server.

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Runs the Flask development server.
    # host='0.0.0.0' makes it accessible from other devices on your network.
    # debug=True enables the debugger and auto-reloader.
    app.run(host='0.0.0.0', port=5000, debug=True)
