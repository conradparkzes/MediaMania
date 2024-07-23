import os
from flask import Flask, render_template, url_for, redirect, request, flash, jsonify
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf
from forms import LoginForm, SignupForm
from models import db, User, Favorite, UserRating
from flask_migrate import Migrate
import random

app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = 'a6954a670f86a75ebd2521b5dac89289'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "users.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

TMBD_API_KEY = 'f506f78c7f61db273279624ae6df02d9'
trending_movies_url = f'https://api.themoviedb.org/3/trending/movie/day?api_key={TMBD_API_KEY}'
trending_shows_url = f'https://api.themoviedb.org/3/trending/tv/day?api_key={TMBD_API_KEY}'
migrate = Migrate(app, db)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/profile')
@login_required
def profile():
    liked_movies = Favorite.query.filter_by(user_id=current_user.id, media_type='movie').all()
    liked_tv_shows = Favorite.query.filter_by(user_id=current_user.id, media_type='tv').all()
    liked_media_ids = [f.media_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]

    recommended_movies = []
    recommended_shows = []

    for movie in liked_movies:
        recommended_movies.extend(get_recommendations('movie', movie.media_id))

    for show in liked_tv_shows:
        recommended_shows.extend(get_recommendations('tv', show.media_id))

    # Remove duplicate recommendations
    recommended_movies = list({movie['id']: movie for movie in recommended_movies}.values())
    recommended_shows = list({show['id']: show for show in recommended_shows}.values())

    # Shuffling due to recs coming in groups and in orderand limit to 10
    random.shuffle(recommended_movies)
    random.shuffle(recommended_shows)
    recommended_movies = recommended_movies[:10]
    recommended_shows = recommended_shows[:10]

    #Sorting feature. CURRENTLY NOT WORKING
    sort_by = request.args.get('sort_by', 'default')

    if sort_by == 'alpha':
        liked_movies = sorted(liked_movies, key=lambda x: x.title)
        liked_tv_shows = sorted(liked_tv_shows, key=lambda x: x.title)
    elif sort_by == 'release':
        # Placeholder if release date can be implemented
        liked_movies = sorted(liked_movies, key=lambda x: x.media_id)
        liked_tv_shows = sorted(liked_tv_shows, key=lambda x: x.media_id)

    return render_template('profile.html', 
                           name=current_user.username, 
                           liked_movies=liked_movies, 
                           liked_tv_shows=liked_tv_shows, 
                           liked_media_ids=liked_media_ids,
                           recommended_movies=recommended_movies,
                           recommended_shows=recommended_shows)
                           
@app.route('/recommend', methods=['GET'])
@login_required
def recommend():
    media_type = request.args.get('media_type')
    recommendations = []

    if media_type == 'movie' or media_type == 'tv':
        favorites = Favorite.query.filter_by(user_id=current_user.id, media_type=media_type).all()
        for item in favorites:
            recommendations.extend(get_recommendations(media_type, item.media_id))
    
    recommendations = {rec['id']: rec for rec in recommendations}.values()
    return jsonify(list(recommendations))

def get_recommendations(media_type, media_id):
    url = f'https://api.themoviedb.org/3/{media_type}/{media_id}/recommendations'
    params = {'api_key': TMBD_API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get('results', [])
    return []

@app.route('/rate', methods=['POST'])
@login_required
def rate():
    data = request.json
    media_id = data.get('media_id')
    rating = data.get('rating')
    
    user_rating = UserRating.query.filter_by(user_id=current_user.id, media_id=media_id).first()
    if user_rating:
        user_rating.rating = rating
    else:
        new_rating = UserRating(user_id=current_user.id, media_id=media_id, rating=rating)
        db.session.add(new_rating)

@app.route('/favorite', methods=['POST'])
@login_required
def favorite():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid data'}), 400

    media_id = data.get('media_id')
    media_type = data.get('media_type')
    title = data.get('title')
    poster_path = data.get('poster_path')
    vote_average = data.get('vote_average')

    favorite = Favorite.query.filter_by(user_id=current_user.id, media_id=media_id, media_type=media_type).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'result': 'removed'})
    else:
        new_favorite = Favorite(
            user_id=current_user.id,
            media_id=media_id,
            media_type=media_type,
            title=title,
            poster_path=poster_path,
            vote_average=vote_average
        )
        db.session.add(new_favorite)
        db.session.commit()
        return jsonify({'result': 'added'})

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email address already exists', 'danger')
            return redirect(url_for('signup'))

        new_user = User(
            username=form.username.data,
            email=form.email.data,
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('landing'))
    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('landing'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/search', methods=['GET'])
def search():
    keyword = request.args.get('query')
    if not keyword:
        return redirect(url_for('landing'))
    return redirect(url_for('search_results', keyword=keyword))

@app.route('/')
def landing():
    movies_response = requests.get(trending_movies_url)
    shows_response = requests.get(trending_shows_url)

    trending_movies = movies_response.json().get('results', [])[:10] if movies_response.status_code == 200 else []
    trending_shows = shows_response.json().get('results', [])[:10] if shows_response.status_code == 200 else []

    liked_media_ids = []
    if current_user.is_authenticated:
        liked_media_ids = [f.media_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]

    return render_template('home.html', trending_movies=trending_movies, trending_shows=trending_shows, liked_media_ids=liked_media_ids)

@app.route('/search_results/<keyword>')
def search_results(keyword):
    response = requests.get(
        f'https://api.themoviedb.org/3/search/multi?api_key={TMBD_API_KEY}&query={keyword}'
    )

    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        liked_media_ids = []
        if current_user.is_authenticated:
            liked_media_ids = [f.media_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]
        return render_template('search.html', keyword=keyword, search_results=results, liked_media_ids=liked_media_ids)
    else:
        return f"Error: {response.status_code} - {response.text}"

if __name__ == '__main__':
    os.makedirs(app.instance_path, exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
