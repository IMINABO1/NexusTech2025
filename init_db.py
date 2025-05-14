from app import app, db

with app.app_context():
    db.drop_all()  # Remove any existing tables
    db.create_all()  # Create all tables fresh
    print("Database tables created successfully!")
