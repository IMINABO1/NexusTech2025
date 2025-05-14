from app import app, db, User, Deal, Collection, Message, Transaction

with app.app_context():
    db.drop_all()
    db.create_all()
    
    # Create test users
    admin = User(
        username='admin',
        email='admin@example.com',
        password='sha256$abc123',
        avatar_url='images/default-avatar.png'
    )
    
    user1 = User(
        username='testuser1',
        email='user1@example.com',
        password='sha256$abc123',
        avatar_url='images/default-avatar.png'
    )
    
    user2 = User(
        username='testuser2',
        email='user2@example.com',
        password='sha256$abc123',
        avatar_url='images/default-avatar.png'
    )
    
    db.session.add_all([admin, user1, user2])
    db.session.commit()

    print("Database initialized successfully!")
