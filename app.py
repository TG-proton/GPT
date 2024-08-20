from flask import Flask, request, render_template, redirect, url_for, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
import re
import csv
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://admindeb:Stella@localhost/mydatabase'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max filstorlek
db = SQLAlchemy(app)

# Databasmodell
class Article(db.Model):
    description = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    shelf = db.Column(db.String(100), nullable=True)
    shelf_row = db.Column(db.String(100), nullable=True)
    shelf_position = db.Column(db.String(100), nullable=True)
    hyllplats = db.Column(db.String(100), nullable=True)
    pall = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, primary_key=True)
    file_path = db.Column(db.String(200), nullable=False)

# Skapa databasen inom applikationskontext
with app.app_context():
    db.create_all()

# Konfigurera uppladdningsmappen
BASE_UPLOAD_FOLDER = 'uploads'
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)

def is_valid_input(value):
    """Kontrollera att inmatningen endast innehåller bokstäver, siffror, mellanslag och understreck."""
    return all(c.isalnum() or c in [' ', '_'] for c in value)

@app.route('/')
def index():
    # Hämta unika värden från databasen för rullgardinsmenyer
    types = db.session.query(Article.type).distinct().all()
    locations = db.session.query(Article.location).distinct().all()
    shelves = db.session.query(Article.shelf).distinct().all()
    shelf_rows = db.session.query(Article.shelf_row).distinct().all()
    shelf_positions = db.session.query(Article.shelf_position).distinct().all()
    hyllplats = db.session.query(Article.hyllplats).distinct().all()
    palls = db.session.query(Article.pall).distinct().all()

    # Omvandla till listor med strängar och sortera dem
    types = sorted([t[0] for t in types if t[0]]) + ['custom']
    locations = sorted([l[0] for l in locations if l[0]]) + ['custom']
    shelves = sorted([s[0] for s in shelves if s[0]]) + ['custom']
    shelf_rows = sorted([r[0] for r in shelf_rows if r[0]]) + ['custom']
    shelf_positions = sorted([p[0] for p in shelf_positions if p[0]]) + ['custom']
    hyllplats = sorted([h[0] for h in hyllplats if h[0]]) + ['custom']
    palls = sorted([p[0] for p in palls if p[0]]) + ['custom']

    return render_template('index.html',
                           types=types,
                           locations=locations,
                           shelves=shelves,
                           shelf_rows=shelf_rows,
                           shelf_positions=shelf_positions,
                           hyllplats=hyllplats,
                           palls=palls)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Kontrollera om filen finns i begäran
    if 'file' not in request.files:
        return 'Ingen fil vald', 400

    file = request.files['file']
    
    # Kontrollera om filnamnet är tomt
    if file.filename == '':
        return 'Ingen fil vald', 400

    description = request.form['description']
    typ = request.form.get('type', '')
    location = request.form.get('location', '')
    shelf = request.form.get('shelf', '')
    shelf_row = request.form.get('shelfRow', '')
    shelf_position = request.form.get('shelfPosition', '')
    hyllplats = request.form.get('hyllplats', '')
    pall = request.form.get('pall', '')

    # Kontrollera att endast description och typ är obligatoriska
    if not description or not typ:
        return 'Beskrivning och typ måste fyllas i.', 400

    # Hantera "custom" inmatningar
    if typ == 'custom':
        typ = request.form.get('customType', '')
    if location == 'custom':
        location = request.form.get('customLocation', '')
    if shelf == 'custom':
        shelf = request.form.get('customShelf', '')
    if shelf_row == 'custom':
        shelf_row = request.form.get('customShelfRow', '')
    if shelf_position == 'custom':
        shelf_position = request.form.get('customShelfPosition', '')
    if hyllplats == 'custom':
        hyllplats = request.form.get('customHyllplats', '')
    if pall == 'custom':
        pall = request.form.get('customPall', '')

    # Skapa en mapp för den valda typen om den inte finns
    type_folder = os.path.join(BASE_UPLOAD_FOLDER, typ)
    os.makedirs(type_folder, exist_ok=True)

    # Generera filnamn
    first_word = re.sub(r'[^a-zA-Z0-9åäöÅÄÖ]', '_', description.split(' ')[0])
    file_name = f"{first_word}.jpg"
    file_path = os.path.join(type_folder, file_name)

    # Om filnamnet redan finns, lägg till ett nummer
    counter = 1
    while os.path.exists(file_path):
        file_name = f"{first_word}_{counter}.jpg"
        file_path = os.path.join(type_folder, file_name)
        counter += 1

    # Spara filen
    try:
        file.save(file_path)
    except Exception as e:
        return f'Fel vid uppladdning av fil: {str(e)}', 500

    # Hämta tidsstämpel
    timestamp = datetime.now()

    # Spara uppgifterna i databasen
    new_article = Article(
        description=description,
        type=typ,
        location=location,
        shelf=shelf,
        shelf_row=shelf_row,
        shelf_position=shelf_position,
        hyllplats=hyllplats,
        pall=pall,
        timestamp=timestamp,
        file_path=file_path
    )
    db.session.add(new_article)
    db.session.commit()

    return 'Fil uppladdad framgångsrikt', 200

@app.route('/search', methods=['GET'])
def search():
    search_term = request.args.get('search')
    articles = Article.query.filter(Article.description.contains(search_term)).all()
    
    # Hämta unika värden från databasen för rullgardinsmenyer
    types = db.session.query(Article.type).distinct().all()
    locations = db.session.query(Article.location).distinct().all()
    shelves = db.session.query(Article.shelf).distinct().all()
    shelf_rows = db.session.query(Article.shelf_row).distinct().all()
    shelf_positions = db.session.query(Article.shelf_position).distinct().all()
    hyllplats = db.session.query(Article.hyllplats).distinct().all()
    palls = db.session.query(Article.pall).distinct().all()

    # Omvandla till listor med strängar och sortera dem
    types = sorted([t[0] for t in types if t[0]]) + ['custom']
    locations = sorted([l[0] for l in locations if l[0]]) + ['custom']
    shelves = sorted([s[0] for s in shelves if s[0]]) + ['custom']
    shelf_rows = sorted([r[0] for r in shelf_rows if r[0]]) + ['custom']
    shelf_positions = sorted([p[0] for p in shelf_positions if p[0]]) + ['custom']
    hyllplats = sorted([h[0] for h in hyllplats if h[0]]) + ['custom']
    palls = sorted([p[0] for p in palls if p[0]]) + ['custom']

    return render_template('search.html',
                           articles=articles,
                           types=types,
                           locations=locations,
                           shelves=shelves,
                           shelf_rows=shelf_rows,
                           shelf_positions=shelf_positions,
                           hyllplats=hyllplats,
                           palls=palls)

@app.route('/edit/<string:timestamp>', methods=['GET', 'POST'])
def edit_article(timestamp):
    article = Article.query.get_or_404(timestamp)

    if request.method == 'POST':
        # Uppdatera artikeldata från formuläret
        article.description = request.form['description']
        
        typ = request.form.get('type', '')
        if typ == 'custom':
            typ = request.form.get('customType', '')
        article.type = typ

        location = request.form.get('location', '')
        if location == 'custom':
            location = request.form.get('customLocation', '')
        article.location = location

        shelf = request.form.get('shelf', '')
        if shelf == 'custom':
            shelf = request.form.get('customShelf', '')
        article.shelf = shelf

        shelf_row = request.form.get('shelfRow', '')
        if shelf_row == 'custom':
            shelf_row = request.form.get('customShelfRow', '')
        article.shelf_row = shelf_row

        shelf_position = request.form.get('shelfPosition', '')
        if shelf_position == 'custom':
            shelf_position = request.form.get('customShelfPosition', '')
        article.shelf_position = shelf_position

        hyllplats = request.form.get('hyllplats', '')
        if hyllplats == 'custom':
            hyllplats = request.form.get('customHyllplats', '')
        article.hyllplats = hyllplats

        pall = request.form.get('pall', '')
        if pall == 'custom':
            pall = request.form.get('customPall', '')
        article.pall = pall

        db.session.commit()
        return redirect(url_for('list_articles'))

    # Hämta unika värden för rullgardinsmenyer
    types = sorted([t[0] for t in db.session.query(Article.type).distinct().all() if t[0]]) + ['custom']
    locations = sorted([l[0] for l in db.session.query(Article.location).distinct().all() if l[0]]) + ['custom']
    shelves = sorted([s[0] for s in db.session.query(Article.shelf).distinct().all() if s[0]]) + ['custom']
    shelf_rows = sorted([r[0] for r in db.session.query(Article.shelf_row).distinct().all() if r[0]]) + ['custom']
    shelf_positions = sorted([p[0] for p in db.session.query(Article.shelf_position).distinct().all() if p[0]]) + ['custom']
    hyllplats = sorted([h[0] for h in db.session.query(Article.hyllplats).distinct().all() if h[0]]) + ['custom']
    palls = sorted([p[0] for p in db.session.query(Article.pall).distinct().all() if p[0]]) + ['custom']

    return render_template('edit.html', article=article,
                           types=types,
                           locations=locations,
                           shelves=shelves,
                           shelf_rows=shelf_rows,
                           shelf_positions=shelf_positions,
                           hyllplats=hyllplats,
                           palls=palls)

@app.route('/list')
def list_articles():
    articles = Article.query.all()
    return render_template('list.html', articles=articles)

@app.route('/export_csv')
def export_csv():
    # Hämta alla artiklar från databasen
    articles = Article.query.all()

    # Skapa en in-memory fil för CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Skriv rubriker
    writer.writerow(['Beskrivning', 'Typ', 'Lokal', 'Grupp', 'Hyllrad', 'Hyllplan', 'Hyllplats', 'Pall', 'Tid', 'Link'])

    # Skriv data
    for article in articles:
        # Skapa en absolut URL för filen
        absolute_link = f"http://lager1/{article.file_path}"
        writer.writerow([
            article.description,
            article.type,
            article.location,
            article.shelf,
            article.shelf_row,
            article.shelf_position,
            article.hyllplats,
            article.pall,
            article.timestamp.strftime('%Y-%m-%d %H:%M:%S'),  # Formatera tidsstämpeln
            absolute_link  # Använd den absoluta länken
        ])

    # Skapa en respons med CSV-data
    response = make_response(output.getvalue().encode('utf-8-sig'))  # Använd utf-8-sig
    response.headers["Content-Disposition"] = "attachment; filename=articles.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response

@app.route('/delete/<string:timestamp>')
def delete_article(timestamp):
    article = Article.query.get_or_404(timestamp)
    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('list_articles'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(BASE_UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
