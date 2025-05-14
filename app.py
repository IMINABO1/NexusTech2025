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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
    avatar_url = db.Column(db.String(200), default='images/default-avatar.png')
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
    quantity = db.Column(db.Integer, default=1)
    collection_limit = db.Column(db.Integer, nullable=True)
    collected_by = db.relationship('Collection', backref='deal', lazy=True)

# Collection model for tracking who has collected free items
class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('deal.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)
    quantity = db.Column(db.Integer, default=1)
    
    # Add relationship to User model with a different backref name
    collector = db.relationship('User', backref='items_collected', lazy=True)

# Message model for chat
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    deal_id = db.Column(db.Integer, db.ForeignKey('deal.id'), nullable=False)
    read = db.Column(db.Boolean, default=False)

# Transaction model for payment processing
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('deal.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'purchase' or 'rental'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    receipt_sent = db.Column(db.Boolean, default=False)

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
        quantity = int(request.form.get('quantity', 1))
        
        is_rental = deal_type == 'rent'
        price = float(request.form.get('price', 0)) if deal_type == 'sale' else 0
        
        # Handle collection limit for free items
        collection_limit = None
        if deal_type == 'free' and not request.form.get('no_limit'):
            collection_limit = request.form.get('collection_limit')
            if collection_limit:
                collection_limit = int(collection_limit)
        
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
            user_id=current_user.id,
            quantity=quantity,
            collection_limit=collection_limit if deal_type == 'free' else None
        )
        
        db.session.add(deal)
        db.session.commit()
        flash('Deal posted successfully!', 'success')
        return redirect(url_for('deals'))
    
    return render_template('create_deal.html')

@app.route('/edit-deal/<int:deal_id>', methods=['GET', 'POST'])
@login_required
def edit_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    
    # Check if the current user owns this deal
    if deal.user_id != current_user.id:
        flash('You can only edit your own deals', 'error')
        return redirect(url_for('deals'))
    
    if request.method == 'POST':
        deal.title = request.form.get('title')
        deal.description = request.form.get('description')
        deal.deal_type = request.form.get('type')
        deal.location = request.form.get('location')
        deal.quantity = int(request.form.get('quantity', 1))
        
        deal.is_rental = deal.deal_type == 'rent'
        deal.price = float(request.form.get('price', 0)) if deal.deal_type == 'sale' else 0
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                deal.image_url = url_for('static', filename=f'uploads/{filename}')
        
        db.session.commit()
        flash('Deal updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_deal.html', deal=deal)

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

@app.route('/start-chat/<int:deal_id>')
@login_required
def start_chat(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    return redirect(url_for('chat', user_id=deal.user_id, deal_id=deal_id))

@app.route('/profile')
@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id=None):
    if user_id is None:
        user = current_user
    else:
        user = User.query.get_or_404(user_id)
    
    deals = Deal.query.filter_by(user_id=user.id).order_by(Deal.created_at.desc()).all()
    return render_template('profile.html', user=user, deals=deals)

@app.route('/collect-deal/<int:deal_id>', methods=['POST'])
@login_required
def collect_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    
    # Check if the deal is available and free
    if deal.status != 'available' or deal.price > 0 or deal.is_rental:
        flash('This item is not available for collection', 'error')
        return redirect(url_for('deals'))
      # Check if the user has already collected this deal
    existing_collection = Collection.query.filter_by(
        deal_id=deal.id,
        user_id=current_user.id
    ).first()
    
    # Check collection limit
    if existing_collection and deal.collection_limit:
        if existing_collection.quantity >= deal.collection_limit:
            flash(f'You can only collect up to {deal.collection_limit} of this item', 'error')
            return redirect(url_for('deals'))
    elif not existing_collection and deal.collection_limit:
        # First time collecting, make sure they don't exceed the limit
        if deal.collection_limit < 1:
            flash('Invalid collection limit', 'error')
            return redirect(url_for('deals'))
    
    # Create new collection or update existing one
    if existing_collection:
        existing_collection.quantity += 1
    else:
        collection = Collection(
            deal_id=deal.id,
            user_id=current_user.id,
            quantity=1
        )
        db.session.add(collection)
    
    # Update deal quantity
    deal.quantity -= 1
    if deal.quantity == 0:
        deal.status = 'completed'
    
    db.session.commit()
    flash('Item collected successfully!', 'success')
    return redirect(url_for('deals'))

def record_transaction(transaction):
    try:
        # Mark transaction as processed
        transaction.receipt_sent = True
        db.session.commit()
    except Exception as e:
        print(f"Error recording transaction: {str(e)}")
        raise

@app.route('/process-payment', methods=['POST'])
@login_required
def process_payment():
    try:
        data = request.get_json()
        deal_id = data.get('dealId')
        payment_type = data.get('type')
        amount = data.get('amount')
        email = data.get('email')
        
        deal = Deal.query.get_or_404(deal_id)
        
        # Check if deal is still available
        if deal.status != 'available':
            return jsonify({'success': False, 'error': 'This item is no longer available'})
        
        # Create transaction record
        transaction = Transaction(
            deal_id=deal_id,
            buyer_id=current_user.id,
            amount=amount,
            transaction_type=payment_type
        )
        
        # Update deal status
        if payment_type == 'buy':
            deal.status = 'completed'
        elif payment_type == 'rent':
            deal.status = 'rented'
        
        db.session.add(transaction)
        db.session.commit()
          # Record the transaction
        record_transaction(transaction)
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)