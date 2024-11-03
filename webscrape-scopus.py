from flask import Flask, render_template, request, jsonify
from serpapi import GoogleSearch
import mysql.connector
from mysql.connector import Error

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
api_key = 'e78b48857b1889d41ead1b7acecd713a5551d6aaaa05091f3d65e3df79a6e288'

# Koneksi ke database
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="db_scholar"
)
mycursor = mydb.cursor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    author_id = request.form.get('author_id', request.args.get('author_id', ''))
    faculty = request.form.get('faculty', request.args.get('faculty', ''))
    program_studi = request.form.get('program_studi', request.args.get('program_studi', ''))
    page = int(request.args.get('page', '0'))  # Get page number from URL query parameters

    # Inisialisasi variabel untuk menyimpan semua hasil pencarian
    all_articles = []

    #total yang dicari
    total_searches = 0

    start = 0  # Mulai pencarian dari halaman pertama

    while True:
        # Panggil SerpApi untuk mencari author berdasarkan author_id
        params = {
            "engine": "google_scholar_author",
            "author_id": author_id,
            "api_key": api_key,
            "start": start,
            "num": "100"  # Display 10 results per page
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        author = results.get("author", {})
        cited_by_data = results.get("cited_by", {})
        # Mengambil artikel dari hasil pencarian
        articles = results.get("articles", [])
        all_citations = cited_by_data.get("table", [{}])[0].get("citations", {}).get("all", 0) 

        # Jika tidak ada artikel lagi, keluar dari loop
        if not articles:
            break

        # Menambahkan artikel ke dalam list all_articles
        all_articles.extend(articles)

        #menghitung total pencarian
        total_searches += len(articles) 

        # Insert articles data into database
        for article in articles:
            citation_id = article.get("citation_id", "")
            title = article.get("title", "")
            authors = ", ".join(article.get("authors", []))
            year = article.get("year", "")
            if year == "":
                year = None  # Replace empty string with None
            cited_by_value = article.get("cited_by", {}).get("value", "")  # Mengambil nilai "value" dari "cited_by" jika ada
            url_article = article.get("link", "")
            
            # Memeriksa apakah author_id sudah ada dalam tabel authors
            if not author_exists(author_id):
                # Jika tidak ada, tambahkan author ke dalam tabel authors
                author_name = author.get("name", "")
                author_url = author.get("url", "")
                
                # Memeriksa dan menangani nilai yang hilang untuk cited_by
                sql = "INSERT INTO authors (author_id, author_name, author_url, faculty, program_studi) VALUES (%s, %s, %s, %s, %s)"
                val = (author_id, author_name, author_url, faculty, program_studi)
                mycursor.execute(sql, val)
                mydb.commit()
            else:
                print(f"Author dengan author_id {author_id} sudah ada dalam tabel authors.")

            # Setelah memastikan author ada, masukkan artikel
            if not article_exists(citation_id):
                sql = "INSERT INTO articles (citation_id, title, authors_article, year, citations, url_article, author_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                val = (citation_id, title, authors, year, cited_by_value, url_article, author_id)
                mycursor.execute(sql, val)
                mydb.commit()
            else:
                print(f"Artikel dengan citation_id {citation_id} sudah ada dalam tabel articles.")

            if not citation_exists(citation_id):
                citation_id = article.get("citation_id", "")
                sql = "INSERT INTO citations (citation_id, year, author_id) VALUES (%s, %s, %s)"
                val = (citation_id, year, author_id)
                mycursor.execute(sql, val)
                mydb.commit()
            else:
                print(f"Sitasi dengan ID {citation_id} sudah ada dalam tabel citations.")

            if not ct_author_exists(author_id):
                sql = "INSERT INTO ct_authors (cited_by, author_id) VALUES (%s, %s)"
                val = (all_citations, author_id)
                mycursor.execute(sql, val)
                mydb.commit()
            else:
                print(f"sitasi author dengan ID {author_id} sudah ada dalam tabel ct_authors.")


        # Tambahkan nilai start untuk pencarian selanjutnya
        start += 100  
       

    return render_template('search_results.html',citation_id=citation_id, articles=all_articles, author=author, cited_by=cited_by_data, author_id=author_id, current_page=page, total_searches=total_searches)

def author_exists(author_id):
    sql = "SELECT * FROM authors WHERE author_id = %s"
    val = (author_id,)
    mycursor.execute(sql, val)
    result = mycursor.fetchone()
    return True if result else False

def article_exists(citation_id):
    sql = "SELECT * FROM articles WHERE citation_id = %s"
    val = (citation_id),
    mycursor.execute(sql, val)
    result = mycursor.fetchall()  # Baca dan kosongkan hasil query sebelumnya
    return True if result else False

def citation_exists(citation_id):
    sql = "SELECT * FROM citations WHERE citation_id = %s"
    val = (citation_id,)
    mycursor.execute(sql,val)
    result = mycursor.fetchall()
    return True if result else False

def ct_author_exists(author_id):
    sql = "SELECT * FROM ct_authors WHERE author_id = %s"
    val = (author_id,)
    mycursor.execute(sql,val)
    result = mycursor.fetchall()
    return True if result else False


@app.route('/citation_data', methods=['GET'])
def citation_data():
    # Mengambil total citation_id berdasarkan tahun
    sql = "SELECT year, COUNT(citation_id) as total FROM citations GROUP BY year ORDER BY year"
    mycursor.execute(sql)
    result = mycursor.fetchall()

    # Mengonversi hasil ke dalam format JSON yang sesuai
    years = [row[0] for row in result]
    totals = [row[1] for row in result]

    return jsonify({"years": years, "totals": totals})


@app.route('/dashboard', methods=['GET'])
def dashboard():
    faculty = request.args.get('faculty', '')
    program_studi = request.args.get('program_studi', '')
    if faculty and program_studi:
        sql = "SELECT * FROM authors WHERE faculty = %s AND program_studi = %s"
        val = (faculty, program_studi)
    elif faculty:
        sql = "SELECT * FROM authors WHERE faculty = %s"
        val = (faculty,)
    else:
        sql = "SELECT * FROM authors"
        val = ()

    mycursor.execute(sql, val)
    authors = mycursor.fetchall()

    faculty_names = ["Teknik", "Ilmu Sosial dan Ilmu Politik", "Kedokteran dan Ilmu Kesehatan", "Pertanian", "Agama Islam", "Hukum", "Pendidikan Bahasa", "Ekonomi dan Bisnis"]
    faculty_counts = []
    for name in faculty_names:
        mycursor.execute("SELECT COUNT(*) FROM authors WHERE faculty = %s", (name,))
        faculty_counts.append(mycursor.fetchone()[0])

        # Retrieve the total counts for Authors, Articles, and Citations
    mycursor.execute("SELECT COUNT(*) FROM authors")
    total_authors = mycursor.fetchone()[0]
    
    mycursor.execute("SELECT COUNT(*) FROM articles")
    total_articles = mycursor.fetchone()[0]

    return render_template('dashboard.html', total_authors=total_authors, total_articles=total_articles, authors=authors, faculty_names=faculty_names, faculty_counts=faculty_counts, selected_faculty=faculty, selected_program_studi=program_studi)

ARTICLES_PER_PAGE = 10

@app.template_filter('min')
def jinja2_min(val1, val2):
    return min(val1, val2)

@app.template_filter('max')
def jinja2_max(val1, val2):
    return max(val1, val2)

@app.route('/articles', methods=['GET'])

def articles():
    faculty = request.args.get('faculty', '')
    author_id = request.args.get('author_id', '')
    page = int(request.args.get('page', '1'))  # Default to page 1 if not specified

    authors = get_authors()
    total_articles, articles = get_filtered_articles(faculty, author_id, page)

    # Calculate pagination information
    total_pages = (total_articles + ARTICLES_PER_PAGE - 1) // ARTICLES_PER_PAGE
    prev_page = max(1, page - 1)
    next_page = min(total_pages, page + 1)

    return render_template('articles.html', authors=authors, articles=articles, selected_faculty=faculty, selected_author=author_id,
                           total_pages=total_pages, current_page=page, prev_page=prev_page, next_page=next_page)

def get_authors():
    mycursor.execute("SELECT author_id, author_name FROM authors")
    return mycursor.fetchall()

def get_filtered_articles(faculty, author_id, page):
    offset = (page - 1) * ARTICLES_PER_PAGE
    sql = "SELECT COUNT(*) FROM articles WHERE 1=1"
    params = []

    if faculty:
        sql += " AND author_id IN (SELECT author_id FROM authors WHERE faculty = %s)"
        params.append(faculty)
    if author_id:
        sql += " AND author_id = %s"
        params.append(author_id)

    mycursor.execute(sql, params)
    total_articles = mycursor.fetchone()[0]

    sql = "SELECT title, url_article FROM articles WHERE 1=1"
    if faculty:
        sql += " AND author_id IN (SELECT author_id FROM authors WHERE faculty = %s)"
    if author_id:
        sql += " AND author_id = %s"

    sql += " LIMIT %s OFFSET %s"
    params.extend([ARTICLES_PER_PAGE, offset])

    mycursor.execute(sql, params)
    articles = mycursor.fetchall()

    return total_articles, articles

@app.route('/get_articles', methods=['GET'])
def get_articles():
    author_id = request.args.get('author_id')
    sql = "SELECT title, url_article FROM articles WHERE author_id = %s"
    val = (author_id,)
    mycursor.execute(sql, val)
    articles = mycursor.fetchall()
    articles_list = [{"title": article[0], "url": article[1]} for article in articles]
    return jsonify({"articles": articles_list})



if __name__ == '__main__':
    app.run(debug=True)
