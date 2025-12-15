import os
from dotenv import load_dotenv

load_dotenv()

# gemini setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# cors stuff
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# model config - override with MODEL_NAME in .env
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
