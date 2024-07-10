const API_KEY = '6002916285f553db6971e37d6512b036';
const BASE_URL = 'https://api.themoviedb.org/3';
const API_URL = BASE_URL + '/discover/movie?sort_by=popularity.desc&' + API_KEY;
const IMG_URL = 'https://image.tmdb.org/t/p/w500';
const searchURL = BASE_URL + '/search/movie?' + API_KEY;

//checking if user is logged in
const isLoggedIn = () => !!localStorage.getItem('user');

//getting movies from TMDB
function getMovies(url) {
    fetch(url)
        .then(response => response.json())
        .then(data => {
            showMovies(data.results);
        })
        .catch(error => {
            console.error('Error fetching movies:', error);
        });
}

//show trending movies on the page for the Home Page and Search Page
function showMovies(movies) {
    const moviesEl = document.getElementById('movies') || document.getElementById('search-results') || document.getElementById('liked-movies');
    moviesEl.innerHTML = '';

    movies.forEach(movie => {
        const { title, poster_path, id } = movie;
        const movieEl = document.createElement('div');
        movieEl.classList.add('movie');
        movieEl.innerHTML = `
            <img src="${IMG_URL + poster_path}" alt="${title}">
            <h3>${title}</h3>
            <button class="like-btn" data-id="${id}">❤</button>
        `;
        moviesEl.appendChild(movieEl);
    });

    document.querySelectorAll('.like-btn').forEach(button => {
        button.addEventListener('click', () => {
            if (isLoggedIn()) {
                saveToLocalStorage(button.dataset.id);
            } else {
                window.location.href = 'login.html';
            }
        });
    });
}

//saving liked movie to local storage (client-side)
function saveToLocalStorage(movieId) {
    let likedMovies = JSON.parse(localStorage.getItem('likedMovies')) || [];
    if (!likedMovies.includes(movieId)) {
        likedMovies.push(movieId);
        localStorage.setItem('likedMovies', JSON.stringify(likedMovies));
    }
}

//showing Favorited movies on profile page
function showLikedMovies() {
    let likedMovies = JSON.parse(localStorage.getItem('likedMovies')) || [];
    likedMovies.forEach(movieId => {
        fetch(`${BASE_URL}/movie/${movieId}?${API_KEY}`)
            .then(response => response.json())
            .then(movie => {
                showMovies([movie]);
            })
            .catch(error => {
                console.error('Error fetching liked movies:', error);
            });
    });
}
