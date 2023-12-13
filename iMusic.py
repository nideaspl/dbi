#student ID:20513273
from pathlib import Path
from flask import Flask, request, redirect, render_template, url_for, flash, abort
from helper import *
import sqlite3
import csv
from pprint import pprint

app = Flask(__name__)


####################
# Routes
####################

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/statistics/', methods=['GET'])
def statistics():
    genres = get_genres()
    return render_template('statistics.html', genres=genres)


@app.route('/statistics/<genre_id>', methods=['GET'])
def statistics_genre(genre_id):
    genres = get_genres()    
    # Check if the result of get_genre_statistics is not None
    stats_result = get_genre_statistics(genre_id)
    if stats_result is not None:
        # stats_result is already a list, no need to wrap it in a new list
        stats = stats_result
    else:
        # Handle the case when stats_result is None (e.g., no statistics available)
        stats = [{'GenreId': 'all'}]

    if not stats:
        return redirect(url_for('statistics'))

    # Extract values from the stats list
    # stats = stats[0] if stats else {}

    return render_template('statistics.html', genres=genres, selected_genre_id=genre_id, stats=stats)


@app.route('/statistics/', methods=['POST'])
def statistics_process():
    # Get the genre id from the request
    genre_id = request.form['genre'] 
    return redirect(url_for('statistics_genre', genre_id=genre_id))


@app.route('/upload/', methods=['GET'])
def upload():
    return render_template('upload.html')


@app.route('/upload/', methods=['POST'])
def upload_process():
    # Get the file from the request
    file = request.files.get('file')

    # Validate the file
    if not file or file.filename == '':
        flash('No file selected. Please upload a file.', 'danger')
        return redirect(url_for('upload'))
    
    # Check file extension for .tsv
    if not file.filename.lower().endswith('.tsv'):
        flash('Invalid file. Please upload a valid .tsv file.', 'danger')
        return redirect(url_for('upload'))

     # Save the file
    try:
        uploads_dir = Path.cwd() / 'uploads'
        uploads_dir.mkdir(exist_ok=True)
        filename = 'Artist.tsv'
        tsv_file = uploads_dir / filename
        file.save(tsv_file)

        # Update the Artist table
        if update_artist_table(tsv_file):
            flash('Successfully updated Artist table.', 'success')
        else:
            flash('Error updating Artist table. Please check the file format.', 'danger')
    except Exception as e:
        flash('An error occurred while processing the file.', 'danger')

    return redirect(url_for('index'))


@app.route('/add/', methods=['GET'])
def add():
    tracks = get_tracks_with_no_genre()
    return render_template('add.html', tracks=tracks)


@app.route('/add/', methods=['POST'])
def add_process():
    genre_name = request.form['genre_name']   # TODO: Replace with the genre name from the request
    track_ids = request.form.getlist('tracks')    # TODO: Replace with the track ids from the request
    try:
        if string_length(genre_name) < 3 or string_length(genre_name)>120:
            raise Exception('Track name is too short or too long')
    except Exception as e:
        print(f"SQLite error: {e}")
        flash('Problem with the provided genre name.','warning')
        return redirect(url_for('add'))     
    if not genre_name:
        flash('genre name is required!','warning')
        return redirect(url_for('add'))
    #if not track_ids:
        #flash('track ID is required!','warning')
        #return redirect(url_for('add'))
    return add_genre_and_tracks(genre_name, track_ids)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', messages=['404: Page not found.'])

####################
# Functions
####################

import sqlite3

def add_genre_and_tracks(genre_name, track_ids):
    conn = sqlite3.connect('iMusic.db')
    cursor = conn.cursor()
    
    try:
        # Check if genre_name already exists in the database
        cursor.execute("SELECT GenreId FROM Genre WHERE Name = ?", (genre_name,))
        existing_genre_id = cursor.fetchone()
        if existing_genre_id:
            raise Exception('Genre with this name already exists')
    except Exception as e:
        print(f"SQLite error: {e}")
        flash('Problem with the provided genre name.','warning')
        return redirect(url_for('add'))

    try:
        if string_length(genre_name) < 3 or string_length(genre_name) > 120:
            raise Exception('Genre name is too short or too long')
    except Exception as e:
        print(f"SQLite error: {e}")
        flash('Problem with the provided genre name.','warning')
        return redirect(url_for('add'))

    if not genre_name:
        flash('Genre name is required!','warning')
        return redirect(url_for('add'))
    #if not track_ids:
        #flash('Track ID is required!','warning')
        #return redirect(url_for('add'))

    
    # Insert the new genre
    try:
        cursor.execute("INSERT INTO Genre (Name) VALUES (?)", (genre_name,))
    except Exception as e:
        print(f"SQLite error: {e}")
        flash('An error occurred while processing your request', 'danger')
        return redirect(url_for('add'))
    try:
        # Validate track IDs
        for track_id in track_ids:
            cursor.execute("SELECT TrackId FROM Track WHERE TrackId = ? AND GenreId IS NULL", (track_id,))
            existing_track_id = cursor.fetchone()
            if not existing_track_id:
                raise Exception(f'Track with ID {track_id} does not exist or already has a genre assigned')
    except Exception as e:
        print(f"SQLite error: {e}")
        flash('The provided track IDs are invalid', 'warning')
        return redirect(url_for('add'))
    # Retrieve the last inserted GenreId
    genre_id = cursor.lastrowid
    try:
        # Update the tracks with the new GenreId
        for track_id in track_ids:
            cursor.execute("""
                UPDATE Track 
                SET 
                    GenreId = ?
                WHERE 
                    TrackId = ?;
            """, (genre_id, track_id))
    except Exception as e:
        # Handle exceptions if necessary
        flash('An error occurred while processing your request', 'danger')
        return redirect(url_for('add'))

    finally:
        conn.commit()
        conn.close()
    flash('The genre has been added successfully','success')
    return redirect(url_for('index'))

def update_artist_table(tsv_file: Path):
    # TODO: Not implemented
    conn = sqlite3.connect('iMusic.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    with open(tsv_file) as f:
        spamreader=csv.DictReader(f, delimiter='\t')
        for row in spamreader:
            print(', '.join(row))
            print(row['ArtistId'], row['OriginalName'])
            try:
                cursor.execute("""
                    INSERT INTO Artist (ArtistId, Name) VALUES (?, ?)
                """, (row['ArtistId'], row['OriginalName']))
            except:
                cursor.execute("""
                    UPDATE
                        Artist
                    SET
                    Name = ?
                    WHERE ArtistId=?;         
            """,(row['OriginalName'],row['ArtistId'])) 
            cursor.execute('SELECT*FROM Artist')
            rows = cursor.fetchall()
        #Print the results
        for row in rows:
            print(row['ArtistId'], row['Name'])
        print(row)        
    conn.commit()
    conn.close()
    return True


def get_genres():
    # TODO: Not implemented
    conn = sqlite3.connect('iMusic.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
                    SELECT*FROM Genre
                    ORDER BY Name ASC;
                """)
    rows = cursor.fetchall()
    conn.close()
    rows = [{'GenreId': 'all', 'Name': 'All Genres'}] + rows 
    return rows

def get_genre_statistics(genre_id):
    conn = sqlite3.connect('iMusic.db')
    cursor = conn.cursor()
    try:
    # Execute a SELECT query to check if the genre_id exists
        cursor.execute("SELECT * FROM Genre WHERE genreId = ?", (genre_id,))
        row = cursor.fetchone()
    
        if row:
        # Get the column names from the cursor description
            column_names = [desc[0] for desc in cursor.description]
        
        # Create a dictionary by zipping column names and row values
            result = dict(zip(column_names, row))
            if 'TotalValue' in result and result['TotalValue'] is not None:
                result['TotalValue'] = result['TotalValue']
            else:
                result['TotalValue'] = 0
    
        # Check if the row is not None (i.e., the genre_id exists)
            print(f"Genre with genre_id {genre_id} exists. Details: {result}")
        elif genre_id == 'all':
            result='all'
            print(f"Genre with genre_id {genre_id} exists. Details: {result}")
        else:
            print(f"Genre with genre_id {genre_id} does not exist.")
            flash('The specified genre does not exist.', 'warning')
            return False
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

    finally:
        conn.close()

    conn = sqlite3.connect('iMusic.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if genre_id == 'all':
        # If 'all' is selected, calculate statistics for all genres
        cursor.execute("""
             SELECT
                COALESCE(AVG(UnitPrice), 0) AS 'Price',
                COUNT(DISTINCT t.TrackId) AS 'Tracks',
                COUNT(DISTINCT t.AlbumId) AS 'Albums',
                COUNT(DISTINCT Artist.ArtistId) AS 'Artists',
                COALESCE(SUM(t.Milliseconds)/1000, 0) AS 'Duration',
                SUM(t.UnitPrice) AS 'TotalValue'
            FROM
                Track t
                LEFT JOIN Album a ON a.AlbumId = t.AlbumId
                LEFT JOIN Genre g ON g.GenreId = t.GenreId
                LEFT JOIN Artist ON Artist.ArtistId = a.ArtistId      
                WHERE t.GenreId IS NOT NULL
            ORDER BY g.Name ASC;        
        """)
    else:
        # If a specific genre is selected, calculate statistics for that genre
        cursor.execute("""
             SELECT
                COALESCE(AVG(UnitPrice), 0) AS 'Price',
                COUNT(DISTINCT t.TrackId) AS 'Tracks',
                COUNT(DISTINCT t.AlbumId) AS 'Albums',
                COUNT(DISTINCT Artist.ArtistId) AS 'Artists',
                COALESCE(SUM(t.Milliseconds)/1000, 0) AS 'Duration',
                SUM(t.UnitPrice) AS 'TotalValue'
            FROM
                Track t
                LEFT JOIN Album a ON a.AlbumId = t.AlbumId
                LEFT JOIN Genre g ON g.GenreId = t.GenreId
                LEFT JOIN Artist ON Artist.ArtistId = a.ArtistId
            WHERE g.GenreId = ?
            LIMIT 1
        """, (genre_id,))

    row = cursor.fetchone() 
    

    # Convert the row to a dictionary

    if row:
        result = dict(row) 
        print(result)
        if 'TotalValue' in result and result['TotalValue'] is not None:
            result['TotalValue'] = result['TotalValue']
        else:
            result['TotalValue'] = 0    
    else: 
        flash('An error occurred while processing your request', 'danger')
        return False  
    conn.close()
    return result



def get_tracks_with_no_genre():
    # TODO: Not implemented
    conn = sqlite3.connect('iMusic.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # If a specific genre is selected, calculate statistics for that genre
    cursor.execute("""
            SELECT *
        FROM Track
        WHERE GenreId IS NULL
        """)
    rows = cursor.fetchall()
    conn.close()

    # Convert the rows to a list of dictionaries
    rows = [dict(row) for row in rows]
    return rows


####################
# Main
####################
def main():
    # We need to set the secret key to use flash - there's no need to change or worry about this
    app.secret_key = 'I love dbi'
    # Run the app in debug mode, listening on port 5000
    app.run(debug=True, port=5000)

# This is the entry point for the application
if __name__ == "__main__":
    main()
