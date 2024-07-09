import requests
import pandas as pd
import sqlalchemy as db
import tmdbsimple as tmdb

extracted_data = []

tmdb.API_KEY = 'f506f78c7f61db273279624ae6df02d9'

def get_movies(page):
    search = tmdb.Movies()
    response = search.popular(page=page)
    return response['results']

def get_tv_shows(page):
    search = tmdb.TV()
    response = search.popular(page=page)
    return response['results']

# stores movie and tv show data in a list of dictionaries
def get_data(items, item_type):
    global extracted_data
    for item in items:
        if item_type == 'movie':
            title = item.get('title')
        else:
            title = item.get('name')
        poster_path = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}"
        rating = item.get('vote_average')
        extracted_data.append({
            'title': title,
            'poster_path': poster_path,
            'rating': rating,
            'type': item_type
        })
    return extracted_data

def make_table(data):
    # error handling
    if not extracted_data:
        print("Unable to create table.")
    else:
        dataf = pd.DataFrame(extracted_data)
        engine = db.create_engine('sqlite:///tmdb_data.db')
        dataf.to_sql('all_media', con=engine, if_exists='replace', index=False)
        with engine.connect() as connection:
            query_result = (
                connection.execute(db.text("SELECT * FROM all_media;"))
                .fetchall()
            )
            print(pd.DataFrame(query_result))

def main():
    all_data = []
    for page in range(1, 6):  # sample range - first 5 pages
        movies = get_movies(page)
        tv_shows = get_tv_shows(page)
        all_data.extend(get_data(movies, 'movie'))
        all_data.extend(get_data(tv_shows, 'tv_show'))
    
    make_table(all_data)

if __name__ == '__main__':
    main()