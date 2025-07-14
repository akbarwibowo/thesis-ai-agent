from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from dotenv import load_dotenv, find_dotenv
from os import getenv

load_dotenv(find_dotenv())
VERTEX_API_KEY = getenv("VERTEX_API_KEY")

llm_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=VERTEX_API_KEY,
) 