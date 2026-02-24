import os

from modules.mongo_core import MongoDB
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("MONGO_DB_NAME", "cargo-emissions")
# Use cloud MongoDB connection string if available, otherwise fallback to local
MONGO_CONNECTION_STRING = os.getenv("LOCAL_MONGO_CONNECTION_STRING")

# Initialize database instances
user_db = MongoDB(
    db_name=DB_NAME, collection_name="users", connection_str=MONGO_CONNECTION_STRING
)

search_history_db = MongoDB(
    db_name=DB_NAME,
    collection_name="search_history",
    connection_str=MONGO_CONNECTION_STRING,
)
