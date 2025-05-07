from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    ratings = db.Column(db.Float, default=0.0)
    num_ratings = db.Column(db.Integer, default=0)
    deals = db.relationship('Deal', backref='owner', lazy=True)

# Deal model
class Deal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float)
    is_rental = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='available')  # available, rented, completed
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Message model for chat
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    deal_id = db.Column(db.Integer, db.ForeignKey('deal.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    featured_deals = Deal.query.filter_by(status='available').order_by(Deal.created_at.desc()).limit(6).all()
    return render_template('index.html', featured_deals=featured_deals)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/deals')
def deals():
    location = request.args.get('location', '')
    deal_type = request.args.get('type', 'all')
    query = Deal.query.filter_by(status='available')
    
    if deal_type != 'all':
        if deal_type == 'free':
            query = query.filter_by(price=0, is_rental=False)
        elif deal_type == 'sale':
            query = query.filter(Deal.price > 0, Deal.is_rental.is_(False))
        elif deal_type == 'rent':
            query = query.filter_by(is_rental=True)
    
    deals = query.order_by(Deal.created_at.desc()).all()
    # In a real app, we would filter by distance here using the location
    
    return render_template('deals.html', deals=deals)

@app.route('/create-deal', methods=['GET', 'POST'])
@login_required
def create_deal():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        deal_type = request.form.get('type')
        location = request.form.get('location')
        
        is_rental = deal_type == 'rent'
        price = float(request.form.get('price', 0)) if deal_type == 'sale' else 0
        
        deal = Deal(
            title=title,
            description=description,
            price=price,
            is_rental=is_rental,
            location=location,
            user_id=current_user.id
        )
        
        db.session.add(deal)
        db.session.commit()
        flash('Deal posted successfully!', 'success')
        return redirect(url_for('deals'))
    
    return render_template('create_deal.html')

@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    recipient = User.query.get_or_404(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp).all()
    
    return render_template('chat.html', recipient=recipient, messages=messages)

@app.route('/send-message', methods=['POST'])
@login_required
def send_message():
    recipient_id = request.form.get('recipient_id')
    content = request.form.get('content')
    deal_id = request.form.get('deal_id')
    
    message = Message(
        content=content,
        sender_id=current_user.id,
        recipient_id=recipient_id,
        deal_id=deal_id
    )
    
    db.session.add(message)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/rate-user', methods=['POST'])
@login_required
def rate_user():
    user_id = request.form.get('user_id')
    rating = float(request.form.get('rating'))
    
    user = User.query.get_or_404(user_id)
    total_rating = user.ratings * user.num_ratings
    user.num_ratings += 1
    user.ratings = (total_rating + rating) / user.num_ratings
    
    db.session.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)