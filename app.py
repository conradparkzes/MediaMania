import os
from flask import Flask, render_template, url_for, redirect, request, flash, jsonify
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf
from forms import LoginForm, SignupForm
from models import db, User, Favorite, MediaRating, Comment, CommentLike
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
        # db.session.commit()
        # return jsonify({'result': 'removed'})
        result = 'removed'
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
        # db.session.commit()
        # return jsonify({'result': 'added'})
        result = 'added'

    db.session.commit()
    return jsonify({'result': result})

@app.route('/rate', methods=['POST'])
@login_required
def rate():
    data = request.json
    media_id = data['media_id']
    media_type = data['media_type']
    rating = data['rating']

    # check if user has already rated this media
    existing_rating = MediaRating.query.filter_by(user_id=current_user.id, media_id=media_id, media_type=media_type).first()

    if existing_rating:
        existing_rating.rating = rating
    else:
        new_rating = MediaRating(user_id=current_user.id, media_id=media_id, media_type=media_type, rating=rating)
        db.session.add(new_rating)

    db.session.commit()

    return jsonify({'result': 'success'})

@app.route('/comments', methods=['POST'])
@login_required
def post_comment():
    data = request.get_json()
    media_id = data.get('media_id')
    media_type = data.get('media_type')
    text = data.get('text')
    parent_id = data.get('parent_id')

    new_comment = Comment(
        user_id=current_user.id,
        media_id=media_id,
        media_type=media_type,
        text=text,
        parent_id=parent_id
    )
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({'result': 'success', 'comment_id': new_comment.id, 'username': current_user.username, 'timestamp': new_comment.timestamp})

@app.route('/comments/<media_type>/<int:media_id>', methods=['GET'])
def get_comments(media_type, media_id):
    comments = Comment.query.filter_by(media_id=media_id, media_type=media_type, parent_id=None).all()
    return jsonify([{
        'id': comment.id,
        'user_id': comment.user_id,
        'username': comment.user.username,
        'text': comment.text,
        'timestamp': comment.timestamp,
        'likes': len(comment.likes),
        'replies': [{
            'id': reply.id,
            'user_id': reply.user_id,
            'username': reply.user.username,
            'text': reply.text,
            'timestamp': reply.timestamp,
            'likes': len(reply.likes)
        } for reply in comment.replies]
    } for comment in comments])

@app.route('/like_comment', methods=['POST'])
@login_required
def like_comment():
    data = request.get_json()
    comment_id = data.get('comment_id')
    existing_like = CommentLike.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        return jsonify({'result': 'unliked'})
    else:
        new_like = CommentLike(user_id=current_user.id, comment_id=comment_id)
        db.session.add(new_like)
        db.session.commit()
        return jsonify({'result': 'liked'})


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

@app.route('/media/<media_type>/<int:media_id>')
def media_detail(media_type, media_id):
    response = requests.get(f'https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={TMBD_API_KEY}')

    if response.status_code == 200:
        media_data = response.json()
        liked_media_ids = []
        year = media_data.get('release_date', '')[:4] if media_type == 'movie' else media_data.get('first_air_date', '')[:4]
        imdb_rating = media_data.get('vote_average', 'N/A')
        language = media_data.get('original_language', 'N/A')
        country = media_data.get('production_countries', [{}])[0].get('name', 'N/A')

        maturity_rating = 'N/A'
        if media_type == 'movie':
            maturity_response = requests.get(f'https://api.themoviedb.org/3/movie/{media_id}/release_dates?api_key={TMBD_API_KEY}')
            if maturity_response.status_code == 200:
                release_dates = maturity_response.json().get('results', [])
                for entry in release_dates:
                    if entry['iso_3166_1'] == 'US':
                        for release in entry['release_dates']:
                            if 'certification' in release and release['certification']:
                                maturity_rating = release['certification']
                                break
                        break
        elif media_type == 'tv':
            maturity_response = requests.get(f'https://api.themoviedb.org/3/tv/{media_id}/content_ratings?api_key={TMBD_API_KEY}')
            if maturity_response.status_code == 200:
                content_ratings = maturity_response.json().get('results', [])
                for entry in content_ratings:
                    if entry['iso_3166_1'] == 'US':
                        maturity_rating = entry['rating']
                        break

        user_rating = None
        if current_user.is_authenticated:
            liked_media_ids = [f.media_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]
            user_rating_record = MediaRating.query.filter_by(user_id=current_user.id, media_id=media_id, media_type=media_type).first()
            user_rating = user_rating_record.rating if user_rating_record else None

        return render_template('media.html', media=media_data, media_type=media_type, liked_media_ids=liked_media_ids, year=year, maturity_rating=maturity_rating, imdb_rating=imdb_rating, language=language, country=country, user_rating=user_rating)

    return redirect(url_for('landing'))


@app.route('/search_results/<keyword>')
def search_results(keyword):
    search_url = f'https://api.themoviedb.org/3/search/multi?api_key={TMBD_API_KEY}&query={keyword}'
    response = requests.get(search_url)
    if response.status_code == 200:
        search_results = response.json().get('results', [])
    else:
        search_results = []

    liked_media_ids = []
    if current_user.is_authenticated:
        liked_media_ids = [f.media_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]

    return render_template('search.html', search_results=search_results, keyword=keyword, liked_media_ids=liked_media_ids)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
