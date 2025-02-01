from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, WatchlistItem
from app import db, login_manager, app, logger
from utils import fetch_company_data
from stock_collection import resolve_ticker_symbol
from concurrent.futures import ThreadPoolExecutor
import logging

main = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.config['STATIC_FOLDER'], filename)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists')
            return redirect(url_for('main.signup'))

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password, method='sha256')
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('main.signin'))

    return render_template('signup.html')

@main.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid credentials')
            return redirect(url_for('main.signin'))

        login_user(user)
        return redirect(url_for('main.dashboard'))

    return render_template('signin.html')

@main.route('/dashboard')
@login_required
def dashboard():
    watchlist = WatchlistItem.query.filter_by(user_id=current_user.id)\
        .order_by(WatchlistItem.created_at.desc()).all()

    # Fetch initial data for watchlist companies
    company_data = {}
    for item in watchlist[:5]:  # Limit initial load to 5 companies
        try:
            data = fetch_company_data(item.company_name)
            company_data[item.company_name] = data
        except Exception as e:
            company_data[item.company_name] = {
                'ticker': None,
                'stock_data': None,
                'news': None,
                'error': str(e)
            }

    return render_template('dashboard.html',
                         username=current_user.username,
                         watchlist=watchlist,
                         company_data=company_data)

@main.route('/watchlist/add', methods=['POST'])
@login_required
def add_to_watchlist():
    try:
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

        # Verify company exists by attempting to resolve ticker
        ticker = resolve_ticker_symbol(company_name)

        # Create new watchlist item
        new_item = WatchlistItem(
            company_name=company_name,
            user_id=current_user.id
        )

        db.session.add(new_item)
        db.session.commit()

        return jsonify({
            'id': new_item.id,
            'company_name': new_item.company_name,
            'created_at': new_item.created_at.isoformat()
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error adding company to watchlist: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to add company to watchlist'}), 500

@main.route('/watchlist/delete/<int:item_id>', methods=['DELETE'])
@login_required
def delete_from_watchlist(item_id):
    try:
        item = WatchlistItem.query.get_or_404(item_id)

        # Verify item belongs to current user
        if item.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting watchlist item: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to delete item'}), 500

@main.route('/watchlist/data', methods=['GET'])
@login_required
def get_watchlist_data():
    try:
        watchlist = WatchlistItem.query.filter_by(user_id=current_user.id).all()

        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Create mapping of company names to their data
            company_data = {}
            futures = {
                executor.submit(fetch_company_data, item.company_name): item.company_name
                for item in watchlist
            }

            for future in futures:
                company_name = futures[future]
                try:
                    data = future.result()
                    company_data[company_name] = data
                except Exception as e:
                    logger.error(f"Error fetching data for {company_name}: {str(e)}")
                    company_data[company_name] = {
                        'ticker': None,
                        'stock_data': None,
                        'news': None,
                        'error': str(e)
                    }

        return jsonify(company_data)
    except Exception as e:
        logger.error(f"Error getting watchlist data: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch watchlist data'}), 500

@main.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# Error handlers
@main.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@main.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
