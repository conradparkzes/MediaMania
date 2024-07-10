from flask import Flask, render_template, url_for, redirect, request
import requests

app = Flask(__name__)
TMBD_API_KEY = 'f506f78c7f61db273279624ae6df02d9'

trending_movies_url = f'https://api.themoviedb.org/3/trending/movie/day?api_key={TMBD_API_KEY}'
trending_shows_url = f'https://api.themoviedb.org/3/trending/tv/day?api_key={TMBD_API_KEY}'

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
def search():
    keyword = request.args.get('keyword')
    if not keyword:
        return "No keyword provided."
    return redirect(url_for('search_results', keyword=keyword))

@app.route('/search_results/<keyword>')
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
    app.run(debug=True)