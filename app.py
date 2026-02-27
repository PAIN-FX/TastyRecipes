from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secretkey')

# Create data directory if it doesn't exist (for persistent storage on Render)
if not os.path.exists('data'):
    os.makedirs('data')

# Use environment variable for database or default to SQLite in data folder
import os

# Example for Render PostgreSQL
DB_USER = os.environ.get('DB_USER', 'tastyrecipes_5r15_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'oIrNMb6T15nXlOc7g2P47UCurud47qUk')
DB_HOST = os.environ.get('DB_HOST', 'dpg-d6h1p5q4d50c73f2gb20-a')
DB_NAME = os.environ.get('DB_NAME', 'tastyrecipes_5r15')
DB_PORT = os.environ.get('DB_PORT', '5432')

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)

# ===================== DATABASE MODELS =====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    recipes = db.relationship('Recipe', backref='author', lazy=True)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    prep_time = db.Column(db.Integer, nullable=False)
    cook_time = db.Column(db.Integer, nullable=False)
    servings = db.Column(db.Integer, nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===================== ROUTES =====================

@app.route('/')
def index():
    # Get featured and latest recipes
    featured_recipes = Recipe.query.order_by(Recipe.created_at.desc()).limit(3).all()
    latest_recipes = Recipe.query.order_by(Recipe.created_at.desc()).limit(4).all()
    return render_template('index.html', featured_recipes=featured_recipes, latest_recipes=latest_recipes)

@app.route('/recipes')
def view_recipes():
    category = request.args.get('category', '').lower()
    search = request.args.get('search', '')
    
    query = Recipe.query
    
    if category and category != 'all':
        query = query.filter_by(category=category.capitalize())
    
    if search:
        query = query.filter(Recipe.name.ilike(f'%{search}%'))
    
    recipes = query.order_by(Recipe.created_at.desc()).all()
    return render_template('view_recipes.html', recipes=recipes, current_category=category, search=search)

@app.route('/about')
def about():
    recipe_count = Recipe.query.count()
    user_count = User.query.count()
    return render_template('about.html', recipe_count=recipe_count, user_count=user_count)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add_recipe():
    if 'user_id' not in session:
        flash('Please login to add recipes.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        recipe = Recipe(
            name=request.form['name'],
            category=request.form['category'],
            prep_time=int(request.form['prep_time']),
            cook_time=int(request.form['cook_time']),
            servings=int(request.form['servings']),
            ingredients=request.form['ingredients'],
            instructions=request.form['instructions'],
            image_url=request.form.get('image_url', ''),
            user_id=session['user_id']
        )
        db.session.add(recipe)
        db.session.commit()
        flash('Recipe added successfully!', 'success')
        return redirect(url_for('view_recipes'))

    return render_template('add_recipe.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_recipe(id):
    recipe = Recipe.query.get_or_404(id)

    if recipe.user_id != session.get('user_id'):
        flash('You can only edit your own recipes!', 'error')
        return redirect(url_for('view_recipes'))

    if request.method == 'POST':
        recipe.name = request.form['name']
        recipe.category = request.form['category']
        recipe.prep_time = int(request.form['prep_time'])
        recipe.cook_time = int(request.form['cook_time'])
        recipe.servings = int(request.form['servings'])
        recipe.ingredients = request.form['ingredients']
        recipe.instructions = request.form['instructions']
        recipe.image_url = request.form.get('image_url', '')
        db.session.commit()
        flash('Recipe updated successfully!', 'success')
        return redirect(url_for('view_recipes'))

    return render_template('edit_recipe.html', recipe=recipe)

@app.route('/recipe/<int:id>')
def view_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    return render_template('recipe_detail.html', recipe=recipe)

@app.route('/delete/<int:id>')
def delete_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    
    if recipe.user_id != session.get('user_id'):
        flash('You can only delete your own recipes!', 'error')
        return redirect(url_for('view_recipes'))
    
    db.session.delete(recipe)
    db.session.commit()
    flash('Recipe deleted successfully!', 'success')
    return redirect(url_for('view_recipes'))

# ===================== RUN APP =====================

# Initialize database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Get port from environment variable (for Render deployment)
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 to allow external access

    app.run(host='0.0.0.0', port=port, debug=False)


