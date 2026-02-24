import os

from dotenv import load_dotenv

from modules.mongo_core import MongoDB

load_dotenv()

DB_NAME = os.getenv("MONGO_DB_NAME", "cargo-emissions")
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")

# Collection to Store user data
user_db = MongoDB(db_name=DB_NAME, collection_name="users", connection_str=MONGO_CONNECTION_STRING)


# Collection to sture search history
search_history_db = MongoDB(
    db_name=DB_NAME,
    collection_name="search_history",
    connection_str=MONGO_CONNECTION_STRING,
)
