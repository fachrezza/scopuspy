from flask import Flask, render_template, request
from serpapi import GoogleSearch
import mysql.connector
import json

app = Flask(__name__, template_folder='view')
api_key = '372866610a37a1d503ab9ed7f66eea5a3a009f643c9c9cbaff8174f9dc02deb1'

# Koneksi ke database
mydb = mysql.connector.connect(
    host="localhost",
    user="root",  # Ganti dengan username Anda
    password="",  # Ganti dengan password Anda
    database="db_scholar"
)
mycursor = mydb.cursor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        author_id = request.form.get('author_id')
        page = 0  # default page number is 0
        start = page * 10  # Calculate start value based on page number

        # Panggil SerpApi untuk mencari author berdasarkan author_id
        params = {
            "engine": "google_scholar_author",
            "author_id": author_id,
            "api_key": api_key,
            "start": start,
            "num": "10"  # Display 10 results per page
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        author = results.get("author", {})
        cited_by = results.get("cited_by", {})
        all_citations = cited_by.get("table", [{}])[0].get("citations", {}).get("all", 0)                                   
        articles = results.get("articles", [])

        # Insert author data into database if not exists
        if not author_exists(author_id):
            sql = "INSERT INTO authors (author_id, author_name, cited_by) VALUES (%s, %s, %s)"
            val = (author_id, author.get("name", ""), (all_citations))
            mycursor.execute(sql, val)
            mydb.commit()

        # Insert articles data into database
        for article in articles:
            if not article_exists(author_id, article.get("title", ""), article.get("year", "")):
                sql = "INSERT INTO articles (title, authors_article, year, citations, url_article, author_id) VALUES (%s, %s, %s, %s, %s, %s)"
                val = (article.get("title", ""), ", ".join(article.get("authors", [])), article.get("year", ""), (article.get("cited_by", "")), article.get("link", ""), author_id)
                mycursor.execute(sql, val)
                mydb.commit()

        return render_template('search_results.html', articles=articles, author=author, cited_by=cited_by, all_citations=all_citations, author_id=author_id)

def author_exists(author_id):
    sql = "SELECT * FROM authors WHERE author_id = %s"
    val = (author_id,)
    mycursor.execute(sql, val)
    result = mycursor.fetchone()
    return True if result else False

def article_exists(author_id, title, year):
    sql = "SELECT * FROM articles WHERE author_id = %s AND title = %s AND year = %s"
    val = (author_id, title, year)
    mycursor.execute(sql, val)
    result = mycursor.fetchone()
    return True if result else False


if __name__ == '__main__':
    app.run(debug=True)
