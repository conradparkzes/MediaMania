from flask import Flask, render_template, url_for, redirect, request, flash
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, SignupForm
from models import db, User

app = Flask(__name__)
app.config['Secret_Key'] = 'a6954a670f86a75ebd2521b5dac89289'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

TMBD_API_KEY = 'f506f78c7f61db273279624ae6df02d9'

trending_movies_url = f'https://api.themoviedb.org/3/trending/movie/day?api_key={TMBD_API_KEY}'
trending_shows_url = f'https://api.themoviedb.org/3/trending/tv/day?api_key={TMBD_API_KEY}'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/profile')
@login_required
# profile page
def profile():
    return render_template('profile.html', name=current_user.username)

@app.route('/signup', methods=['GET', 'POST'])
# signup function
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
# login function
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.date).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('landing'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
# logout function
def logout():
    logout_user()
    return redirect(url_for('landing'))


@app.route('/')
# search / landing page to display top trending media, home page
def landing():
    movies_response = requests.get(trending_movies_url)
    shows_response = requests.get(trending_shows_url)

    if movies_response.status_code == 200 and shows_response.status_code == 200:
        trending_movies = movies_response.json().get('results', [])
        trending_shows = shows_response.json().get('results', [])
    else:
        trending_movies = []
        trending_shows = []

    return render_template('search.html', trending_movies=trending_movies, trending_shows=trending_shows)

@app.route('/search', methods=['GET'])
# search page
def search():
    keyword = request.args.get('keyword')
    if not keyword:
        return "No keyword provided."
    return redirect(url_for('search_results', keyword=keyword))

@app.route('/search_results/<keyword>')
# search results page
def search_results(keyword):
    response = requests.get(
        f'https://api.themoviedb.org/3/search/multi?api_key={TMBD_API_KEY}&query={keyword}'
    )

    if response.status_code == 200:
        data = response.json()
        if 'results' in data:
            results = data.get('results', [])
        else:
            results = []
        return render_template('results.html', keyword=keyword, results=results)
    else:
        return f"Error: {response.status_code} - {response.text}"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)