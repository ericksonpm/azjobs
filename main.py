from app import app

if __name__ == '__main__':
    from scheduler import start_scheduler
    
    # Start the scheduler in production
    start_scheduler()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
