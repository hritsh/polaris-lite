import os
from dotenv import load_dotenv

load_dotenv()

# gemini setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# cors stuff
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# model config - using gemini 2.0 flash for efficiency
MODEL_NAME = "gemini-2.0-flash"
