# models.py

from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Initialize the Base for model classes
Base = declarative_base()

# Association table for many-to-many relationships between authors and articles
authors_articles = Table(
    'authors_articles', Base.metadata,
    Column('author_id', String(50), ForeignKey('authors.author_id'), primary_key=True),
    Column('citation_id', String(50), ForeignKey('articles.citation_id'), primary_key=True)
)
def get_author_data(faculty, program_studi):
    # Example: Static data, replace with database query or scraped data
    all_authors = [
        (1, "Author A", "https://example.com", "Teknik", "Teknologi Informasi"),
        (2, "Author B", "https://example.com", "Ilmu Sosial dan Ilmu Politik", "Ilmu Komunikasi"),
        # Add more authors as needed
    ]
    filtered_authors = [
        author for author in all_authors 
        if (not faculty or author[3] == faculty) and (not program_studi or author[4] == program_studi)
    ]
    
    total_authors = len(filtered_authors)
    total_articles = sum(len(a) for a in filtered_authors)  # Simplified for demo

    return filtered_authors, total_authors, total_articles

def get_citation_data():
    # Mock data for chart
    return {
        "years": [2018, 2019, 2020, 2021, 2022],
        "totals": [50, 60, 70, 90, 120]
    }

class Author(Base):
    __tablename__ = 'authors'
    
    author_id = Column(String(50), primary_key=True)
    author_name = Column(String(255), nullable=False)
    author_url = Column(String(255))
    faculty = Column(String(255))
    program_studi = Column(String(255))
    
    # Relationship with articles
    articles = relationship("Article", secondary=authors_articles, back_populates="authors")

class Article(Base):
    __tablename__ = 'articles'
    
    citation_id = Column(String(50), primary_key=True)
    title = Column(String(255), nullable=False)
    authors_article = Column(String(255))
    year = Column(Integer)
    citations = Column(Integer)
    url_article = Column(String(255))
    author_id = Column(String(50), ForeignKey('authors.author_id'))
    
    # Relationship with authors
    authors = relationship("Author", secondary=authors_articles, back_populates="articles")

# Database setup
DATABASE_URL = 'mysql+mysqlconnector://root@localhost/db_scholar'
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
Base.metadata.create_all(engine)
