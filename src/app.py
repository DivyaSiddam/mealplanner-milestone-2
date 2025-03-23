from flask import Flask, render_template, redirect, url_for, flash, request, session, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField, SelectField, TimeField
from wtforms.validators import InputRequired, Length, EqualTo, Email
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from wtforms import IntegerField  
from wtforms.validators import NumberRange 
from flask import send_file  
from wtforms import SelectField
from datetime import datetime, timedelta
import os
import pandas as pd


# Initialize Flask App
app = Flask(__name__)

# ✅ Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345@localhost:3308/mealplanner_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)  # Generates a random secret key

# Initialize Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------------
# ✅ Database Models (Without Phone Number)
# ------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    mealplan_id = db.Column(db.Integer, db.ForeignKey('meal_plan.id'), nullable=True)  # ✅ Allow NULL values

class MealPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class NutritionData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    carbohydrates = db.Column(db.Float, nullable=False)
    fiber = db.Column(db.Float, nullable=False)
    sugar = db.Column(db.Float, nullable=False)

  

class FavoriteRecipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)



# ------------------------
# ✅ Forms (Without Phone Number)
# ------------------------
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[InputRequired(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[InputRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[InputRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

class MealPlanForm(FlaskForm):
    name = StringField('Meal Plan Name', validators=[InputRequired()])
    date = DateField('Date', validators=[InputRequired()])
    submit = SubmitField('Create Meal Plan')

class RecipeForm(FlaskForm):
    name = StringField('Recipe Name', validators=[InputRequired()])
    ingredients = TextAreaField('Ingredients', validators=[InputRequired()])
    instructions = TextAreaField('Instructions', validators=[InputRequired()])
    mealplan_id = SelectField('Assign to Meal Plan', coerce=int, choices=[])  # ✅ Initialize with empty list
    submit = SubmitField('Add Recipe')

class RateRecipeForm(FlaskForm):
    rating = IntegerField('Rating (1-5)', validators=[InputRequired(), NumberRange(min=1, max=5)])
    submit = SubmitField('Rate')



# ------------------------
# ✅ User Loader for Flask-Login
# ------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------
# ✅ Routes
# ------------------------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        existing_email = User.query.filter_by(email=form.email.data).first()

        if existing_user:
            flash('❌ Username already taken. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        if existing_email:
            flash('❌ An account with this email already exists.', 'danger')
            return redirect(url_for('register'))

        # ✅ Hash password before saving
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        new_user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            password=hashed_password  # ✅ Ensure hashed password is stored
        )

        db.session.add(new_user)
        db.session.commit()

        print(f"✅ User Registered: {form.username.data} - Hashed Password: {hashed_password}")  # Debugging

        flash('✅ Registered successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user:
            print(f"✅ Found user: {user.username}")
            print(f"🔑 Stored Password Hash: {user.password}")  # Debugging stored hash
            print(f"🔐 Entered Password: {form.password.data}")  # Debugging user input
            print(f"🛠 Hash Comparison Result: {bcrypt.check_password_hash(user.password, form.password.data)}")

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('✅ Login Successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Login Failed. Check username and password.', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("✅ You have been logged out.", "success")
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    meal_plans = MealPlan.query.filter_by(user_id=current_user.id).all()
    recipes = Recipe.query.all()

    # ✅ Fetch favorite recipes correctly
    favorite_recipes = db.session.query(FavoriteRecipe, Recipe).join(Recipe).filter(FavoriteRecipe.user_id == current_user.id).all()

    messages = get_flashed_messages(with_categories=True)

    return render_template('dashboard.html', 
                           username=current_user.username, 
                           meal_plans=meal_plans, 
                           recipes=recipes, 
                           favorite_recipes=[fav.Recipe for fav in favorite_recipes],  # ✅ Fix Data Format
                           messages=messages)


@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    form = RecipeForm(obj=recipe)

    # ✅ Load meal plans into the dropdown
    mealplans = MealPlan.query.all()
    form.mealplan_id.choices = [(mp.id, mp.name) for mp in mealplans] or [(0, "No Meal Plans Available")]

    if form.validate_on_submit():
        recipe.name = form.name.data
        recipe.ingredients = form.ingredients.data
        recipe.instructions = form.instructions.data
        recipe.mealplan_id = form.mealplan_id.data
        db.session.commit()
        flash('Recipe updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_recipe.html', form=form, recipe=recipe)

@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)

    # ✅ First, delete all favorite_recipe references for this recipe
    FavoriteRecipe.query.filter_by(recipe_id=recipe_id).delete()

    # ✅ Now, delete the actual recipe
    db.session.delete(recipe)
    db.session.commit()

    flash('✅ Recipe deleted successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/rate_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def rate_recipe(recipe_id):
    form = RateRecipeForm()
    if form.validate_on_submit():
        recipe = Recipe.query.get(recipe_id)
        recipe.rating = (recipe.rating * recipe.rated_by + form.rating.data) / (recipe.rated_by + 1)
        recipe.rated_by += 1
        db.session.commit()
        flash('Recipe rated successfully!', 'success')
    
    return redirect(url_for('dashboard'))



@app.route('/export_shopping_list')
@login_required
def export_shopping_list():
    user_id = current_user.id
    meal_plans = MealPlan.query.filter_by(user_id=user_id).all()
    items = []
    
    for meal_plan in meal_plans:
        recipes = Recipe.query.filter_by(mealplan_id=meal_plan.id).all()
        for recipe in recipes:
            items.extend(recipe.ingredients.split("\n"))

    df = pd.DataFrame({"Ingredient": items})
    file_path = "shopping_list.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route('/favorite_recipe/<int:recipe_id>')
@login_required
def favorite_recipe(recipe_id):
    new_favorite = FavoriteRecipe(user_id=current_user.id, recipe_id=recipe_id)
    db.session.add(new_favorite)
    db.session.commit()
    flash("Recipe added to favorites!", "success")
    return redirect(url_for('dashboard'))


@app.route('/grocery_list/<int:mealplan_id>')
@login_required
def grocery_list(mealplan_id):
    mealplan = MealPlan.query.get_or_404(mealplan_id)
    recipes = Recipe.query.filter_by(mealplan_id=mealplan_id).all()

    grocery_items = {}  # ✅ Store ingredients and count occurrences

    if not recipes:
        flash("No recipes found for this meal plan!", "warning")
        return render_template('grocery_list.html', mealplan=mealplan, grocery_items=grocery_items)

    for recipe in recipes:
        if recipe.ingredients:  # ✅ Ensure ingredients exist
            ingredients = recipe.ingredients.split(',')  # ✅ Split comma-separated ingredients
            for ingredient in ingredients:
                ingredient = ingredient.strip().lower()  # ✅ Normalize text
                grocery_items[ingredient] = grocery_items.get(ingredient, 0) + 1

    return render_template('grocery_list.html', mealplan=mealplan, grocery_items=grocery_items)



@app.route('/mealplan/<int:mealplan_id>')
@login_required
def mealplan_detail(mealplan_id):
    mealplan = MealPlan.query.get_or_404(mealplan_id)
    return render_template('mealplan_detail.html', mealplan=mealplan)


# ✅ Add the add_mealplan route HERE (below dashboard)
@app.route('/add_mealplan', methods=['GET', 'POST'])
@login_required
def add_mealplan():
    form = MealPlanForm()
    
    if form.validate_on_submit():
        new_mealplan = MealPlan(
            name=form.name.data,
            date=form.date.data,
            user_id=current_user.id
        )
        db.session.add(new_mealplan)
        db.session.commit()
        
        flash('✅ Meal plan added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_mealplan.html', form=form)

@app.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    form = RecipeForm()
    mealplans = MealPlan.query.all()  # Fetch meal plans from the database

    # ✅ Populate the meal plan dropdown
    form.mealplan_id.choices = [(mp.id, mp.name) for mp in mealplans]

    if form.validate_on_submit():
        selected_mealplan_id = form.mealplan_id.data if form.mealplan_id.data else None  # ✅ Ensure it's valid

        new_recipe = Recipe(
            name=form.name.data,
            ingredients=form.ingredients.data,
            instructions=form.instructions.data,
            mealplan_id=selected_mealplan_id  # ✅ Assign mealplan_id properly
        )
        db.session.add(new_recipe)
        db.session.commit()
        flash('Recipe added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_recipe.html', form=form, mealplans=mealplans)

@app.route('/nutrition_analysis', methods=['GET', 'POST'])
def nutrition_analysis():
    if request.method == 'POST':
        calories = request.form.get('calories')
        protein = request.form.get('protein')
        fat = request.form.get('fat')
        carbohydrates = request.form.get('carbohydrates')
        fiber = request.form.get('fiber')
        sugar = request.form.get('sugar')

        # Store data in session
        session['nutrition_data'] = {
            'calories': calories,
            'protein': protein,
            'fat': fat,
            'carbohydrates': carbohydrates,
            'fiber': fiber,
            'sugar': sugar
        }

        print("\n--- Session Data Saved ---")
        print(session['nutrition_data'])

        flash("Nutrition data saved successfully!", "success")
        return redirect(url_for('nutrition_analysis'))

    # Print session data before rendering the template
    print("\n--- Session Data Retrieved ---")
    print(session.get('nutrition_data'))

    return render_template('nutrition_analysis.html')

@app.route('/meal_planner', methods=['GET', 'POST'])
@login_required
def meal_planner():
    if 'meal_plans' not in session:
        session['meal_plans'] = []

    if request.method == 'POST':
        date = request.form.get('date')
        meal = request.form.get('meal')
        items = request.form.get('items')

        if date and meal and items:
            session['meal_plans'].append({'date': date, 'meal': meal, 'items': items})
            session.modified = True  # ✅ Save session changes
            flash("Meal plan saved successfully!", "success")
            return redirect(url_for('meal_planner'))

    return render_template('meal_planner.html', meal_plans=session.get('meal_plans', []))



@app.route('/weekly_summary')
@login_required
def weekly_summary():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())  # Get Monday of this week
    end_of_week = start_of_week + timedelta(days=6)  # Get Sunday of this week

    # Fetch meal plans for the current week
    meal_plans = MealPlan.query.filter(
        MealPlan.user_id == current_user.id,
        MealPlan.date >= start_of_week,
        MealPlan.date <= end_of_week
    ).all()

    summary_data = []
    for plan in meal_plans:
        recipes = Recipe.query.filter_by(mealplan_id=plan.id).all()
        summary_data.append({
            'date': plan.date.strftime('%Y-%m-%d'),
            'meal_plan': plan.name,
            'recipes': [recipe.name for recipe in recipes] if recipes else []
        })

    return render_template('weekly_summary.html', weekly_summary=summary_data)



# ------------------------
# ✅ Database Initialization (Ensures Tables Exist)
# ------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)