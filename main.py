import pandas as pd
import streamlit as st
import streamlit_antd_components as sac
from themoviedb import TMDb
import time
from datetime import date

# gets API key for TMDB (The Movie Database)from Streamlit secrets
api_key = st.secrets["TMDB_API_KEY"]

## Initialize TMDb with the API key
tmdb = TMDb(key=api_key, language='en-GB', region='GB')

#%% Get a list of top rated movies (sync mode)

# movies = tmdb.movies().top_rated()
# for movie in movies:
#     print(movie)

#%% Discover movies by different types of data.

# movies = tmdb.discover().movie(
#     sort_by="vote_average.desc",
#     primary_release_date__gte="1997-08-15",
#     vote_count__gte=10000,
#     vote_average__gte=6.0,
# ) 

# # Create a DataFrame to store movie details
# movie_details_df = pd.DataFrame(columns=['Title', 'Overview'])

# # Loop through the first 10 movies and get details and add to dataframe 
# for movie in range(10):
#     movie_details = tmdb.movie(movie.id).details()
#     movie_details_df.loc[len(movie_details_df)] = [movie_details.title, movie_details.overview]
 

#%% Movie search function:

movie_df = pd.DataFrame(columns=['Title', 'Overview'])

# function to search for movies, actors and tv shows(slow: takes 5-10 seconds)
def multi_search(search_term="Jack", search_type="multi"):

    # checks search type and calls the appropriate TMDb search method
    if search_type == "movie":
        results = tmdb.search().movies(search_term)
    elif search_type == "tv":
        results = tmdb.search().tv(search_term)
    elif search_type == "person":
        results = tmdb.search().people(search_term)
    elif search_type == "multi":
        results = tmdb.search().multi(search_term)
    else:
        raise ValueError("Invalid search type. Choose from 'movie', 'tv', or 'person'.")

    # creates empty dataframes for each type of result
    movie_df = pd.DataFrame(columns=['Title', 'Overview'])
    person_df = pd.DataFrame(columns=['Name', 'Biography'])
    tv_df = pd.DataFrame(columns=['Title', 'Overview'])

    # loops through results and appends to the appropriate dataframe
    for result in results:
        if result.media_type == "movie":
            movie = tmdb.movie(result.id).details()
            movie_df.loc[len(movie_df)] = [movie.title, movie.overview]
            
        elif result.media_type == "person":
            person = tmdb.person(result.id).details()
            person_df.loc[len(person_df)] = [person.name, person.biography]

        elif result.media_type == "tv":
            tv = tmdb.tv(result.id).details()
            tv_df.loc[len(tv_df)] = [tv.title, tv.overview]

    # creates dict of all results dataframes
    results_dict = {
        'movie': movie_df, 
        'person': person_df,
        'tv': tv_df
    }
    
    # returns all results in a dict if search_type is 'multi', otherwise returns the specific type
    if search_type == "multi":
        return results_dict
    else:
        return results_dict[search_type]

        
# function to search for only one of movies, tv shows or actors (may be faster?)
def single_search(search_term="Jack", search_type="movie"):
    if search_type == "movie":
        results = tmdb.search().movies(search_term)
    elif search_type == "tv":
        results = tmdb.search().tv(search_term)
    elif search_type == "person":
        results = tmdb.search().people(search_term)
    else:
        raise ValueError("Invalid search type. Choose from 'movie', 'tv', or 'person'.")


    # Convert results to a DataFrame
    results_df = pd.DataFrame(columns=['Title', 'Overview'])
    for result in results:
        if search_type == "movie":
            movie = tmdb.movie(result.id).details()
            results_df.loc[len(results_df)] = [movie.title, movie.overview]
        elif search_type == "tv":
            tv = tmdb.tv(result.id).details()
            results_df.loc[len(results_df)] = [tv.title, tv.overview]
        elif search_type == "person":
            person = tmdb.person(result.id).details()
            results_df.loc[len(results_df)] = [person.name, person.biography]
    return results


#%% Top movies by genre

# Get and cache a list of genre IDs from TMDb and create a dict for mapping genre names to IDs
st.cache_data(ttl=3600)  # Cache for 1 hour
def get_genre_map(reverse=False):
    if reverse == False:
        genre_map = dict((g.name, g.id) for g in tmdb.genres().movie().genres)
    else:
        genre_map = dict((g.id, g.name) for g in tmdb.genres().movie().genres)
    return genre_map

# Create a mapping of genre names to IDs and vice versa
genre_name_to_id = get_genre_map()
genre_id_to_name = get_genre_map(reverse=True)

def where_to_watch(tmdb_id, region='GB'):
    providers = (tmdb.movie(tmdb_id) # searches on given tmdb id e.g. 5255
                 .watch_providers() # gets watch providers 
                 .results # gets dict of result 
                 .get(region) # gets results for only given region code
    )

    # returns a list of the top 5 'flatrate' providers, where flatrate providers are subscription providers
    try:
        provider_names = [p.provider_name for p in providers.flatrate[:5]]
        provider_names_string = ", ".join(provider_names) # converts to string for streamlit st.dataframe comprehension
    except:
        provider_names_string = ""

    return(provider_names_string)

    

st.cache_data(ttl=3600)  # Cache for 1 hour
def top_movies_by_genre(genre=['Action', 'Drama'], 
                        keyword = None, # e.g. a list such as ['Christmas'] or ['Fast', 'Furious'] 
                        people = None, # e.g. directors or actors
                        sort_by="popularity.desc",
                        primary_release_date__gte="1997-08-15",
                        primary_release_date__lte="2025-12-31",
                        vote_count__gte=10000,
                        get_watch_providers=True # defaults to False due to slow 20s API call
                        ): 
    
    genre_ids = [str(genre_name_to_id[g]) for g in genre if g in genre_name_to_id]

    # Join into a string so that it can be passed to the TMDb API in 'with_genres'
    # join with '|' for OR and ',' for AND, i.e. whether to include films with one of the genres or exclusively films with ALL genres given
    genre_string = "|".join(genre_ids)

    progress_bar = st.progress(0, "Fetching movies...")
        

    # Fetches top movies by genre using the TMDb API for given criteria
    results = tmdb.discover().movie(
        sort_by=sort_by,
        primary_release_date__gte=primary_release_date__gte,
        primary_release_date__lte=primary_release_date__lte,
        vote_count__gte=vote_count__gte,
        with_genres=genre_string,
        with_keywords=keyword,
        with_people=people
    )

    # Create a DataFrame to store movie details
    movie_details_df = pd.DataFrame(columns=['Poster', 'Title', 'Overview', 'Popularity', 
                                               'Release Date', 'Vote Average',
                                               'Vote Count', 'Genres', 'Trailer', 'Where to Watch'])

    # Loop through the movies and get details
    movie_count=1
    for movie in results:
        progress_bar.progress(movie_count/len(results), f"Finding where to watch ({movie_count} / {len(results)}) ...")
        # Full details of object functions here: https://github.com/leandcesar/themoviedb/blob/7879120fb550f17741d3f8b26add27549e7ed192/themoviedb/schemas/_partial.py#L61
        movie_details_df.loc[len(movie_details_df)] = [f"https://image.tmdb.org/t/p/w1280{movie.poster_path}", 
                                                       movie.title,
                                                       movie.overview, 
                                                       movie.popularity,
                                                       movie.release_date,
                                                       movie.vote_average,
                                                       movie.vote_count,
                                                       [genre_id_to_name[g] for g in movie.genre_ids if g in genre_id_to_name],
                                                       f"https://www.youtube.com/results?search_query={movie.title.replace(" ", "+")} trailer",
                                                       where_to_watch(movie.id) if get_watch_providers else [] # finds where to watch for given movie.id or returns empty list

        ]
        movie_count+=1 

    if get_watch_providers==False:
        movie_details_df.drop(columns=['Where to Watch']) # drops null where to watch column if parameter is False

    
    progress_bar.progress(100, "Loading Complete")
    time.sleep(0.2)
    progress_bar.empty()

    return movie_details_df

@st.cache_data(ttl=3600)  # Cache for 1 hour
def top_tv_shows_by_genre(genre=['Action', 'Comedy'], 
                          sort_by="popularity.desc",
                          primary_release_date__gte="1997-08-15",
                          primary_release_date__lte="2025-12-31",
                          keyword=None,
                          vote_count__gte=10000):
    
    genre_ids = [str(genre_name_to_id[g]) for g in genre if g in genre_name_to_id]

    # Join into a string so that it can be passed to the TMDb API in 'with_genres'
    # join with '|' for OR and ',' for AND, i.e. whether to include films with one of the genres or exclusively films with ALL genres given
    genre_string = "|".join(genre_ids)
        

    # Fetches top tv shows by genre using the TMDb API for given criteria
    results = tmdb.discover().tv(
        sort_by=sort_by,
        first_air_date__gte=primary_release_date__gte,
        first_air_date__lte=primary_release_date__lte,
        with_keywords=keyword,
        vote_count__gte=vote_count__gte,
        with_genres=genre_string
    )

    # Create a DataFrame to store tv show details
    tv_details_df = pd.DataFrame(columns=['Poster', 'Title', 'Overview', 'Popularity', 
                                           'Release Date', 'Vote Average',
                                           'Vote Count', 'Genres'])

    # Loop through the tv shows and get details
    for show in results:
        # Full details of object functions here: https://github.com/leandcesar/themoviedb/blob/7879120fb550f17741d3f8b26add27549e7ed192/themoviedb/schemas/_partial.py#L61
        tv_details_df.loc[len(tv_details_df)] = [f"https://image.tmdb.org/t/p/w1280{show.poster_path}", 
                                                 show.name,
                                                 show.overview, 
                                                 show.popularity,
                                                 show.first_air_date,
                                                 show.vote_average,
                                                 show.vote_count,
                                                 [genre_id_to_name[g] for g in show.genre_ids if g in genre_id_to_name]
        ]

    return tv_details_df
    
st.set_page_config(layout="centered", # centers page content, with width set in styles.css
                   page_title="TMDb Streamlit App",
                   page_icon="🍿"
                   ) 

# helper function to load CSS styles
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css("styles.css")

# initialises app with a run_id, which is appended to each widget key, and incremented each time the 'clear filter' button is pressed
if "run_id" not in st.session_state:
    st.session_state.run_id = 1

def clear_widgets():
    st.session_state.run_id += 1

# function to magically type a sentence in streamlit 
def stream_sentence(sentence, interval=0.015):
    sentence_array = [char for char in sentence] # splits sentence into a list of characters
    for char in sentence_array:
        yield char
        time.sleep(interval)

st.title("TMDb Streamlit App")

def sort_by_widget(key_suffix):
    sort_by_map = {
    "popularity.desc": "🔥 Most Popular",
    "vote_average.desc": "⭐ Top Rated"
}
    sort_by = st.segmented_control(
        "Sort By",
        options=sort_by_map.keys(), # takes keys from the sort_by_map dict as options
        format_func=lambda x: sort_by_map[x], # formats the display value using the dict values
        default="popularity.desc",  # Default to Most Popular
        selection_mode="single",
        key=f"sort_by_{key_suffix}{st.session_state["run_id"]}"  # Unique key for each tab (movie or tv)
    )
    return sort_by

def genre_selection_widget(key_suffix):
    genre_selection = st.multiselect(
        "Select Genres",
        options=list(genre_name_to_id.keys()),
        # default=['Action', 'Drama'],  # Default genres
        key=f"genre_selection_{key_suffix}{st.session_state["run_id"]}"
    )
    return genre_selection

def release_year_widget(key_suffix, current_year=date.today().year):
    release_year = st.slider(
        "Release Year",
        min_value=1990,
        max_value=current_year,
        value=(2000, current_year),  # Default range
        step=1,
        key=f"release_year_{key_suffix}{st.session_state["run_id"]}"  
    )
    return release_year

def advanced_options_widget(key_suffix, where_to_watch_checkbox=False):
    with st.expander("Advanced Options", expanded=False):
        # keyword_search = st.text_input(
        #     "Keyword search",
        #     help="Enter keywords separated by commas (e.g. Christmas, British, Comedy)",
        #     key=f"keyword_search_{key_suffix}{st.session_state["run_id"]}"
        # )
        # people_search = st.text_input(
        #     "Cast and Crew",
        #     help="Enter the names of cast and crew separated by commas (e.g. Steven Spielberg, Leonardo DiCaprio)",
        #     key=f"people_search_{key_suffix}{st.session_state["run_id"]}"
        # ).split(", "),
        min_vote_count = st.number_input(
            "Minimum Vote Count",
            min_value=0,
            value=5000,  # Default value
            step=1000,
            key=f"min_vote_count_{key_suffix}{st.session_state["run_id"]},",
            help=f"The minimum number of votes required on TMDB to be included in the table. Reduce this number to see less popular TV shows or movies."
        )
        if where_to_watch_checkbox:
            with st.container(horizontal=True):
                show_watch_providers = st.checkbox(
                    "Show watch providers", 
                    value=False,
                    key=f"show_watch_providers_{key_suffix}{st.session_state["run_id"]}",
                    help="Include where to watch column - this takes about 30 seconds to load."
                )
                st.badge("⚠️ Experimental", color="orange")
            return {
                # "keyword" : keyword_search,
                # "people" : people_search,
                "min_vote_count" : min_vote_count,
                "show_watch_providers" : show_watch_providers
            }
        else:
            return {
                # "keyword" : keyword_search,
                # "people" : people_search,
                "min_vote_count" : min_vote_count
            }

movies_tab, tv_shows_tab, cast_and_crew_tab = st.tabs(['🎬 Movies', '📺 TV Shows', '👥 Cast and Crew Search'])

with movies_tab:

    # checks if sort by has been chosen, if it has, then writes the relevant title in a stream/typewriter fashion
    if "m_sort_by" not in st.session_state:
        st.session_state.m_sort_by =  "vote_average.desc" # initialises sort by selection if not already in session state
    elif st.session_state["m_sort_by"] == "vote_average.desc":
        st.write(stream_sentence(f"#### Most Popular Movies by Genre"))
    elif st.session_state["m_sort_by"] == "popularity.desc":
        st.write(stream_sentence(f"#### Top Rated Movies by Genre"))
    else:
        st.write(stream_sentence(f"#### Top Movies by Genre")) # fall back to generic title if one not chosen

    col1, col2 = st.columns([0.6, 0.4])

    with col1:

        # loads reusable widget components defined in functions earlier, passes 'm' for movie to key parameter, to differentiate from tv shows filters
        m_genre_selection = genre_selection_widget(key_suffix="m")
        m_sort_by = sort_by_widget("m")
        st.session_state.m_sort_by = m_sort_by
        m_release_year = release_year_widget("m")

        col1a, col1b = st.columns([0.75, 0.25])
        with col1a:
            m_advanced_options = advanced_options_widget("m", where_to_watch_checkbox=True) # returns dict of options, which are then assigned below
            # m_keyword = m_advanced_options["keyword"]
            # m_people = m_advanced_options["people"]
            m_min_vote_count = m_advanced_options["min_vote_count"]
            m_show_watch_providers = m_advanced_options["show_watch_providers"]
        with col1b:
            st.button("Clear All Filters", icon=':material/filter_alt_off:', key="clear_movie_filters", on_click=clear_widgets)
    
    with col2:
        st.space()

    # loads dataframe using data from top_movies_by_genre function, which queries TMDB API using the given filters from the widgets above
    st.dataframe(top_movies_by_genre(genre=m_genre_selection,
                                    sort_by=m_sort_by,
                                    vote_count__gte=m_min_vote_count,
                                    primary_release_date__gte=f"{m_release_year[0]}-01-01",
                                    primary_release_date__lte=f"{m_release_year[1]}-12-31",
                                    # keyword=m_keyword,
                                    # people=m_people,
                                    get_watch_providers=m_show_watch_providers),
                hide_index=True,
                height=565,
                column_config = {
                    "Poster" : st.column_config.ImageColumn("Movie", help = "Double-click images to enlarge.", width=53), # strict measurements to accomodate downsized movie poster (1/32 original size)
                    "Title" : st.column_config.TextColumn(width=125),
                    "Overview" : st.column_config.TextColumn(width=370),
                    "Genres" : st.column_config.ListColumn(width=150),
                    "Release Date" : st.column_config.DateColumn(width=100, format="D MMM Y"),
                    "Popularity" : st.column_config.NumberColumn(width=85, format="%.1f", help="Popularity according to https://developer.themoviedb.org/docs/popularity-and-trending"),
                    "Vote Average" : st.column_config.NumberColumn(label="Vote Avg.", width=85, format="%.1f"),
                    "Vote Count" : st.column_config.NumberColumn(width=85, format="localized"),
                    "Trailer" : st.column_config.LinkColumn(width=60, display_text="Trailer"),
                    "Where to Watch" : st.column_config.ListColumn(help="Double click a cell to see its full contents.") if m_show_watch_providers else None
                },
                column_order=("Poster", "Title", "Overview", "Genres", "Release Date", "Popularity", "Vote Average", "Vote Count", "Trailer", "Where to Watch"),
                row_height=85
    ) 
with tv_shows_tab:

    # checks if sort by has been chosen, if it has, then writes the relevant title in a stream/typewriter fashion
    if "t_sort_by" not in st.session_state:
        st.session_state.t_sort_by =  "vote_average.desc" # initialises sort by selection if not already in session state
    elif st.session_state["t_sort_by"] == "vote_average.desc":
        st.write(stream_sentence(f"#### Most Popular TV Shows by Genre"))
    elif st.session_state["t_sort_by"] == "popularity.desc":
        st.write(stream_sentence(f"#### Top Rated TV Shows by Genre"))
    else:
        st.write(stream_sentence(f"#### Top TV Shows by Genre")) # fall back to generic title if one not chosen

    col1, col2 = st.columns([0.6, 0.4])

    with col1:

        # loads reusable widget components defined in functions earlier, passes 'm' for tv_show to key parameter, to differentiate from tv shows filters
        t_genre_selection = genre_selection_widget(key_suffix="t")
        t_sort_by = sort_by_widget("t")
        t_release_year = release_year_widget("t")

        col1a, col1b = st.columns([0.75, 0.25])
        with col1a:
            t_advanced_options = advanced_options_widget("t")
            # t_keyword = t_advanced_options["keyword"]
            t_min_vote_count = t_advanced_options["min_vote_count"]
        with col1b:
            st.button("Clear All Filters", icon=':material/filter_alt_off:', key="clear_tv_filters", on_click=clear_widgets)
    
    with col2:
        st.space()


    # loads dataframe using data from top_tv_shows_by_genre function, which queries TMDB API using the given filters from the widgets above
    st.dataframe(top_tv_shows_by_genre(genre=t_genre_selection,
                                    sort_by=t_sort_by,
                                    # keyword=t_keyword,
                                    vote_count__gte=t_min_vote_count,
                                    primary_release_date__gte=f"{t_release_year[0]}-01-01",
                                    primary_release_date__lte=f"{t_release_year[1]}-12-31"),
                hide_index=True,
                height=565,
                column_config = {
                    "Poster" : st.column_config.ImageColumn(
                        "Show", help = "Double-click images to enlarge.", 
                        width=53 # strict measurements to accomodate downsized movie poster (1/32 original size)
                    ),
                    "Title" : st.column_config.TextColumn(width=150),
                    "Overview" : st.column_config.TextColumn(width=400),
                    "Genres" : st.column_config.ListColumn(width=180),
                    "First Aired" : st.column_config.DateColumn(width=100, format="D MMM Y"),
                    "Popularity" : st.column_config.NumberColumn(width=100, format="%.1f"),
                    "Vote Average" : st.column_config.NumberColumn(width=100, format="%.1f"),
                    "Vote Count" : st.column_config.NumberColumn(width=100, format="localized") 
                },
                column_order=("Poster", "Title", "Overview", "Genres", "Release Date", "Popularity", "Vote Average", "Vote Count"),
                row_height=85
    ) 

with cast_and_crew_tab:
    st.warning("⚠️ Work in progress...")
    with st.expander(label="More info:"):
        st.text("This plan will allow users to search a given actor or director and return all of the films they they have featured in order of popularity or rating.")

st.space()

st.divider()

st.caption("Film and TV series related meta used in this app are supplied by The Movie Database (TMDB). This product uses the TMDB API but is not endorsed or certified by TMDB. Please find more information about TMDB here: https://www.themoviedb.org/")

st.image("https://www.themoviedb.org/assets/2/v4/logos/v2/blue_long_2-9665a76b1ae401a510ec1e0ca40ddcb3b0cfe45f1d51b77a308fea0845885648.svg", width=150)

st.caption("The lists of streaming services for each film and TV series are supplied by JustWatch. This product uses the JustWatch API but is not endorsed or certified by JustWatch. JustWatch makes it easy to find out where you can legally watch your favourite movies & TV shows online. Visit https://www.justwatch.com/ for more information.")

st.image("https://www.justwatch.com/appassets/img/logo/JustWatch-logo-small.webp", width=120)