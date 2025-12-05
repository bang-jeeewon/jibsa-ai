import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")

PDF_BASE_URL = os.getenv("PDF_BASE_URL")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")