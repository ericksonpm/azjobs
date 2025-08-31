from app import app

# Import and start scheduler when module loads (for gunicorn)
from scheduler import start_scheduler
start_scheduler()

if __name__ == '__main__':
    # Run the Flask app (only for direct python execution)
    app.run(host='0.0.0.0', port=5000, debug=False)
