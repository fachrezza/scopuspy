from flask import Flask, jsonify
from serpapi import GoogleSearch
from datetime import datetime
import mysql.connector
import logging
import os
import pytz
# Konfigurasi Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
api_key = '372866610a37a1d503ab9ed7f66eea5a3a009f643c9c9cbaff8174f9dc02deb1'

dir_path = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(dir_path, 'test_log.log')

#logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(filename)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


# Koneksi ke database
try:
    mydb = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='scopusumy'
    )
    mycursor = mydb.cursor()
except mysql.connector.Error as err:
    logging.error(f"Error connecting to database: {err}")
    raise

def fetch_and_store_author_data(author_id):
    """Ambil artikel dan sitasi berdasarkan author_id dan simpan ke database."""
    start = 0
    while True:
        # Ambil data dari SerpApi
        params = {
            "engine": "google_scholar_author",
            "author_id": author_id,
            "api_key": api_key,
            "start": start,
            "num": "100"
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        # Ambil author, artikel dan sitasi
        author = results.get("author", {})
        search_data = results.get("search_metadata", {})
        cited_by_data = results.get("cited_by", {})
        articles = results.get("articles", [])
        all_citations = cited_by_data.get("table", [{}])[0].get("citations", {}).get("all", 0)
        citation_after = None
        citation_total = None
        
        # Ambil author_name dan author_url
        author_name = author.get("name", "")
        author_url = search_data.get("google_scholar_author_url", "")

        if not articles:
            break


        # Memasukkan artikel dan citasi
        for article in articles:
            try:
                citation_id = article.get("citation_id", "")
                title = article.get("title", "")
                authors = ", ".join(article.get("authors", []))
                year = article.get("year", None)  # Jika kosong, tetap None
                year = null_to_zero(None if not year else int(year))  # Pastikan `year` integer atau None
                cited_by_value = article.get("cited_by", {}).get("value") #mengambil data value sitasi pada article
                cited_by_value = cited_by_value if cited_by_value is not None else 0 #jika value null maka akan menjadi 0
                url_article = article.get("link", "")

                # Masukkan artikel jika belum ada
                if not article_exists(citation_id):
                    sql = """
                    INSERT INTO articles (citation_id, title, authors_article, year, citations, url_article, author_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE title=VALUES(title), citations=VALUES(citations)
                    """
                    val = (citation_id, title, authors, year, cited_by_value, url_article, author_id)
                    mycursor.execute(sql, val)
                    mydb.commit()

                if not journal_exists(citation_id, title):
                    sql = """
                    INSERT INTO journal (id_ct, title, authors_article, year, citations, url_article, author_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    val = (citation_id, title, authors, year, cited_by_value, url_article, author_id)
                    mycursor.execute(sql, val)
                    mydb.commit()
                    print("Journal inserted successfully.")
                else:
                    print("Duplicate entry found. Journal not inserted.")
                
                current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if not citation_exists(citation_id):
                    # Jika citation_id belum ada, tambahkan baris baru
                    citation_total = null_to_zero(cited_by_value)
                    citation_after = 0  # Karena ini pertama kali, tidak ada perubahan

                    sql = """
                    INSERT INTO citations (citation_id, year, citation_after, citation_total, date_crawling) 
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    val = (citation_id, year, citation_after, citation_total, current_date)
                    mycursor.execute(sql, val)
                    mydb.commit()
                else:
                    # Ambil data citation_total dari database
                    sql = """
                    SELECT citation_total FROM citations WHERE citation_id = %s
                    ORDER BY year DESC LIMIT 1
                    """
                    mycursor.execute(sql, (citation_id,))
                    result = mycursor.fetchone()
                    if result:
                        db_citation_total = null_to_zero(result[0]) # Nilai citation_total dari database
                        current_citation_total = null_to_zero(cited_by_value)  # Nilai terbaru dari SerpAPI

                        # Periksa apakah nilai baru berbeda
                        if current_citation_total != db_citation_total:
                            citation_after = current_citation_total - db_citation_total
                            citation_total = current_citation_total  # Total terbaru

                            # Masukkan perubahan sebagai baris baru
                            sql = """
                            INSERT INTO citations (citation_id, year, citation_after, citation_total, date_crawling)
                            VALUES (%s, %s, %s, %s, %s)
                            """
                            val = (citation_id, year, citation_after, citation_total, current_date)
                            mycursor.execute(sql, val)
                            mydb.commit()
                            
                            # Update baris pertama citation_total
                            sql_update = """
                            UPDATE citations
                            SET citation_total = %s
                            WHERE citation_id = %s AND year = (
                                SELECT MIN(year) FROM citations WHERE citation_id = %s
                            )
                            """
                            val_update = (current_citation_total, citation_id, citation_id)
                            mycursor.execute(sql_update, val_update)
                            mydb.commit()


                
                if add_author_article_relation:
                    logging.info(f"Found articles with the same title '{title}'.")

                    # Cek apakah relasi sudah ada di authors_articles
                    if not authors_articles_exists(author_id, citation_id):
                        # Masukkan data ke dalam tabel authors_articles jika relasi belum ada
                        sql_insert = """
                        INSERT INTO authors_articles (author_id, citation_id, ct_ori)
                        VALUES (%s, %s, %s)
                        """
                        val = (author_id, citation_id, citation_id)  # ct_ori diisi dengan citation_id asli
                        mycursor.execute(sql_insert, val)
                        mydb.commit()
                        logging.info(f"Successfully added relation for author {author_id} and article {citation_id}.")

                        # Sekarang perbarui semua author yang memiliki title yang sama
                        # Ambil semua citation_id dan author_id yang memiliki artikel dengan title yang sama
                        sql_select_articles = """
                        SELECT DISTINCT a.citation_id, aa.author_id
                        FROM articles a
                        LEFT JOIN authors_articles aa ON a.citation_id = aa.citation_id
                        WHERE LOWER(a.title) = LOWER(%s)
                        """
                        mycursor.execute(sql_select_articles, (title,))
                        articles_with_same_title = mycursor.fetchall()

                        if articles_with_same_title:
                            # Ambil satu citation_id acuan (misalnya yang pertama)
                            reference_citation_id = articles_with_same_title[0][0]

                            for article in articles_with_same_title:
                               
                                # Jika author_id belum ada di tabel, tambahkan relasi baru
                                if not authors_articles_exists(author_id, reference_citation_id):
                                    sql_update = """
                                    INSERT INTO authors_articles (author_id, citation_id, ct_ori)
                                    VALUES (%s, %s, %s)
                                    """
                                    val = (author_id, reference_citation_id, citation_id)
                                    mycursor.execute(sql_update, val)

                            mydb.commit()
                            logging.info(f"Successfully updated authors with citation_id {reference_citation_id} and original citations for title '{title}'.")
                        else:
                            logging.info(f"No additional authors found with the same title '{title}'.")
                    else:
                        logging.info(f"Relation for author {author_id} and article {citation_id} already exists.")
                else:
                    logging.info(f"No articles found with title '{title}'.")


            except mysql.connector.Error as db_err:
                logging.error(f"Database error: {db_err}")
                continue
            except ValueError as ve:
                logging.error(f"Value error in data: {ve}")
                continue
        # Masukkan data citasi
        timezone = pytz.timezone('Asia/Jakarta')
        current_date = datetime.now(timezone)

        if not ct_author_exists(author_id):
            try:
                # Jika author_id belum ada, masukkan data baru
                sql = "INSERT INTO ct_authors (cited_by, author_id, date_crawling) VALUES (%s, %s, %s)"
                val = (all_citations, author_id, current_date)
                mycursor.execute(sql, val)
                mydb.commit()
                logging.info(f"Inserted author_id {author_id} with date_crawling {current_date}")
            except mysql.connector.Error as db_err:
                logging.error(f"Error inserting into ct_authors: {db_err}")
        else:
            try:
                # Jika author_id sudah ada, perbarui date_crawling
                sql = "UPDATE ct_authors SET date_crawling = %s WHERE author_id = %s"
                val = (current_date, author_id)
                mycursor.execute(sql, val)
                mydb.commit()
                logging.info(f"Updated date_crawling for author_id {author_id} to {current_date}")
            except mysql.connector.Error as db_err:
                logging.error(f"Error updating date_crawling in ct_authors: {db_err}")


        start += 100

@app.route('/initialize', methods=['GET'])
def initialize():
    """Ambil semua author_id dan populasi data."""
    try:
        mycursor.execute("SELECT author_id FROM authors")
        author_ids = mycursor.fetchall()
    except mysql.connector.Error as db_err:
        logging.error(f"Error fetching author IDs: {db_err}")
        return jsonify({"error": "Database error"}), 500

    for (author_id,) in author_ids:
        fetch_and_store_author_data(author_id)

    return jsonify({"message": "Data initialized successfully."})

# Fungsi pengecekan keberadaan data

def article_exists(citation_id):
    sql = "SELECT 1 FROM articles WHERE title = %s"
    mycursor.execute(sql, (citation_id,))
    return mycursor.fetchall()

def journal_exists(citation_id, title):
    sql = "SELECT 1 FROM journal WHERE id_ct = %s OR title = %s"
    mycursor.execute(sql, (citation_id, title))
    return mycursor.fetchall()

def citation_exists(citation_id):
    sql = "SELECT 1 FROM citations WHERE citation_id = %s"
    mycursor.execute(sql, (citation_id,))
    return mycursor.fetchall()

def ct_author_exists(author_id):
    sql = "SELECT 1 FROM ct_authors WHERE author_id = %s"
    mycursor.execute(sql, (author_id,))
    return mycursor.fetchone() is not None

def add_author_article_relation(author_id, citation_id, title):
    # Cek apakah ada artikel dengan title yang sama
    logging.info(f"Checking for articles with title '{title}' and citation_id '{citation_id}'")

    # Query untuk mencari artikel dengan title yang sama
    sql_select = """
    SELECT citation_id
    FROM articles
    WHERE LOWER(title) = LOWER(%s)
    """
    mycursor.execute(sql_select, (title,))
    return mycursor.fetchall()

def authors_articles_exists(author_id, citation_id):
    """Cek apakah relasi antara author_id dan citation_id sudah ada di tabel authors_articles."""
    sql = "SELECT 1 FROM authors_articles WHERE author_id = %s AND citation_id = %s"
    mycursor.execute(sql, (author_id, citation_id))
    return mycursor.fetchone() is not None

def null_to_zero(value):
    return value if value is not None else 0

#fungsi pengambilan data sukses
def do_logging():
    logger.info("crontab")

if __name__ == '__main__':
    # Panggil fungsi initialize sebelum menjalankan app
    do_logging()
    initialize()


