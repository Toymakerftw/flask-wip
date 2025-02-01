from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://flaskuser:flaskpass@db/flaskdb'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'signin'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    watchlist = db.relationship('WatchlistItem', backref='user', lazy=True)

class WatchlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists')
            return redirect(url_for('signup'))

        new_user = User(
            username=username, 
            email=email,
            password=generate_password_hash(password, method='sha256')
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('signin'))
    
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid credentials')
            return redirect(url_for('signin'))
        
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('signin.html')

@app.route('/dashboard')
@login_required
def dashboard():
    watchlist = WatchlistItem.query.filter_by(user_id=current_user.id).order_by(WatchlistItem.created_at.desc()).all()
    return render_template('dashboard.html', username=current_user.username, watchlist=watchlist)

@app.route('/watchlist/add', methods=['POST'])
@login_required
def add_to_watchlist():
    company_name = request.form.get('company_name')
    if not company_name:
        return jsonify({'error': 'Company name is required'}), 400
    
    # Check if company already exists in user's watchlist
    existing_item = WatchlistItem.query.filter_by(
        user_id=current_user.id,
        company_name=company_name
    ).first()
    
    if existing_item:
        return jsonify({'error': 'Company already in watchlist'}), 400
    
    new_item = WatchlistItem(company_name=company_name, user_id=current_user.id)
    db.session.add(new_item)
    db.session.commit()
    
    return jsonify({
        'id': new_item.id,
        'company_name': new_item.company_name,
        'created_at': new_item.created_at.isoformat()
    })

@app.route('/watchlist/delete/<int:item_id>', methods=['DELETE'])
@login_required
def delete_from_watchlist(item_id):
    item = WatchlistItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item deleted successfully'})


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Initialize the database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)