from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    read = db.Column(db.Boolean, default=False)

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
        
        # Handle image upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_url = url_for('static', filename=f'uploads/{filename}')
        
        deal = Deal(
            title=title,
            description=description,
            price=price,
            is_rental=is_rental,
            location=location,
            image_url=image_url,
            user_id=current_user.id
        )
        
        db.session.add(deal)
        db.session.commit()
        flash('Deal posted successfully!', 'success')
        return redirect(url_for('deals'))
    
    return render_template('create_deal.html')

@app.route('/send-message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    recipient_id = data.get('recipient_id')
    content = data.get('content')
    deal_id = data.get('deal_id')
    
    message = Message(
        content=content,
        sender_id=current_user.id,
        recipient_id=recipient_id,
        deal_id=deal_id or 0  # Use 0 for general messages
    )
    
    db.session.add(message)
    db.session.commit()
    return jsonify({'success': True, 'message_id': message.id})

@app.route('/check-messages')
@login_required
def check_messages():
    recipient_id = request.args.get('recipient_id', type=int)
    last_message_id = request.args.get('last_message_id', type=int)
    
    new_messages = Message.query.filter(
        Message.id > last_message_id,
        ((Message.sender_id == current_user.id) & (Message.recipient_id == recipient_id)) |
        ((Message.sender_id == recipient_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp).all()
    
    return jsonify({
        'messages': [{
            'id': msg.id,
            'content': msg.content,
            'sender_id': msg.sender_id,
            'timestamp': msg.timestamp.isoformat()
        } for msg in new_messages]
    })

@app.route('/messages')
@login_required
def messages():
    # Get all messages involving the current user
    all_messages = Message.query.filter(
        (Message.sender_id == current_user.id) | 
        (Message.recipient_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()
    
    # Group messages by conversation (unique user pairs)
    conversations = []
    seen_pairs = set()
    
    for message in all_messages:
        other_user_id = message.recipient_id if message.sender_id == current_user.id else message.sender_id
        pair_key = tuple(sorted([current_user.id, other_user_id]))
        
        if pair_key not in seen_pairs:
            other_user = User.query.get(other_user_id)
            deal = Deal.query.get(message.deal_id) if message.deal_id != 0 else None
            
            # Count unread messages
            unread_count = Message.query.filter(
                Message.recipient_id == current_user.id,
                Message.sender_id == other_user_id,
                Message.id >= message.id  # Messages after or including this one
            ).count()
            
            conversations.append({
                'other_user': other_user,
                'deal': deal,
                'last_message': message,
                'unread_count': unread_count
            })
            seen_pairs.add(pair_key)
    
    return render_template('messages.html', conversations=conversations)

@app.route('/chat/<int:user_id>')
@app.route('/chat/<int:user_id>/<int:deal_id>')
@login_required
def chat(user_id, deal_id=None):
    recipient = User.query.get_or_404(user_id)
    deal = Deal.query.get(deal_id) if deal_id else None
    
    # Get messages for this conversation
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp).all()
    
    # Mark messages as read
    for message in messages:
        if message.recipient_id == current_user.id and not message.read:
            message.read = True
    db.session.commit()
    
    return render_template('chat.html', recipient=recipient, messages=messages, deal=deal)