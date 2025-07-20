from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.rate_limiters import InMemoryRateLimiter

from dotenv import load_dotenv, find_dotenv
from os import getenv

load_dotenv(find_dotenv())
VERTEX_API_KEY = getenv("VERTEX_API_KEY")

rate_limiter = InMemoryRateLimiter(
    requests_per_second=1,  # <-- Super slow! We can only make a request once every 10 seconds!!
    check_every_n_seconds=0.1,  # Wake up every 100 ms to check whether allowed to make a request,
    max_bucket_size=20000,  # Controls the maximum burst size.
)


def get_llm(temperature=0.5):
    llm_model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=VERTEX_API_KEY,
        rate_limiter=rate_limiter,
        max_output_tokens=10000,
        temperature=temperature
    )
    
    return llm_model