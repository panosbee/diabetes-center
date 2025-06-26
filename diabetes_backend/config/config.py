import os
from dotenv import load_dotenv

# Φόρτωση μεταβλητών περιβάλλοντος από .env
load_dotenv()

# Βασικές παράμετροι
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'csv'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# Κλειδιά και API tokens
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL")

# PubMed API configuration
PUBMED_API_KEY = os.environ.get("PUBMED_API_KEY")
PUBMED_API_URL = os.environ.get("PUBMED_API_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils")

# MongoDB ρυθμίσεις
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = 'diabetes_db'

# Ρυθμίσεις Tesseract
TESSERACT_CMD = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'

# Validate required API keys
if not DEEPSEEK_API_KEY:
    raise ValueError("DeepSeek API key is missing. Set DEEPSEEK_API_KEY in .env file")

if not PUBMED_API_KEY:
    raise ValueError("PubMed API key is missing. Set PUBMED_API_KEY in .env file")