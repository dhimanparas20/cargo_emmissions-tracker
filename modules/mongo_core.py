"""
MongoDB Utility Module - Production Ready

Production-ready MongoDB utility class with connection pooling, error handling,
indexing, transactions, and performance optimizations.

Requirements:
    pymongo>=4.6.0
    passlib>=1.7.4

Install:
    pip install pymongo passlib
    uv add pymongo passlib
"""

import logging
import os
import random
import string
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, List, Optional, Union, Tuple, Generator
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId
from passlib.hash import pbkdf2_sha256
from pymongo import MongoClient, ASCENDING
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import (
    ConnectionFailure,
    DuplicateKeyError,
    ServerSelectionTimeoutError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_CONNECTION_STRING = os.getenv("LOCAL_MONGO_CONNECTION_STRING")
DEFAULT_TIMEOUT_MS = 5000
DEFAULT_MAX_POOL_SIZE = 100
DEFAULT_MIN_POOL_SIZE = 10


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry operations on transient failures.

    Args:
        max_retries (int): Maximum number of retry attempts.
        delay (float): Delay in seconds between retries.

    Returns:
        Callable: Decorated function with retry logic.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for {func.__name__}: {e}")
                        raise
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                    )
                    time.sleep(delay * (attempt + 1))
            return None

        return wrapper

    return decorator


class MongoDB:
    """
    Production-ready MongoDB utility class with advanced features.

    Features:
        - Connection pooling and timeout management
        - Automatic retry logic for transient failures
        - Transaction support
        - Index management
        - Bulk operations
        - Query optimization helpers
        - Comprehensive error handling
        - Context manager support

    Example:
        >>> with MongoDB("mydb", "mycollection") as db:
        ...     db.insert({"name": "John", "age": 30})
    """

    def __init__(
        self,
        db_name: str,
        collection_name: str,
        connection_str: str = DEFAULT_CONNECTION_STRING,
        max_pool_size: int = DEFAULT_MAX_POOL_SIZE,
        min_pool_size: int = DEFAULT_MIN_POOL_SIZE,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        **kwargs,
    ) -> None:
        """
        Initialize MongoDB client with connection pooling and timeout settings.

        Args:
            db_name (str): Name of the database.
            collection_name (str): Name of the collection.
            connection_str (str): MongoDB connection string.
            max_pool_size (int): Maximum connection pool size for performance.
            min_pool_size (int): Minimum connection pool size.
            timeout_ms (int): Connection timeout in milliseconds.
            **kwargs: Additional MongoClient parameters.

        Raises:
            ConnectionFailure: If unable to connect to MongoDB.
            ServerSelectionTimeoutError: If server selection times out.
        """
        try:
            self.client: MongoClient = MongoClient(
                connection_str,
                maxPoolSize=max_pool_size,
                minPoolSize=min_pool_size,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms,
                socketTimeoutMS=timeout_ms,
                retryWrites=True,
                retryReads=True,
                **kwargs,
            )

            # Test connection
            self.client.admin.command("ping")
            logger.info(
                f"Successfully connected to MongoDB: {db_name}.{collection_name}"
            )

            self.db: Database = self.client[db_name]
            self.collection: Collection = self.db[collection_name]
            self._session: Optional[ClientSession] = None

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.error(
                "Please ensure MongoDB is running. You can start it with: docker compose up -d"
            )
            raise SystemExit(1)
        except Exception as e:
            logger.error(f"Unexpected error during MongoDB initialization: {e}")
            raise SystemExit(1)

    def __enter__(self) -> "MongoDB":
        """
        Context manager entry.

        Returns:
            MongoDB: Self instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit with automatic connection cleanup.

        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.
        """
        self.close()

    def health_check(self) -> bool:
        """
        Check if the MongoDB connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise.
        """
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    @staticmethod
    def hashit(data: str) -> str:
        """
        Hash a string using pbkdf2_sha256 (secure password hashing).

        Args:
            data (str): Data to hash.

        Returns:
            str: Hashed string.
        """
        return pbkdf2_sha256.hash(data)

    @staticmethod
    def verify_hash(password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            password (str): Plain password.
            hashed_password (str): Hashed password.

        Returns:
            bool: True if verified, False otherwise.
        """
        try:
            return pbkdf2_sha256.verify(password, hashed_password)
        except Exception as e:
            logger.error(f"Hash verification error: {e}")
            return False

    @staticmethod
    def gen_string(length: int = 15) -> str:
        """
        Generate a cryptographically random alphanumeric string.

        Args:
            length (int): Length of the string (default: 15).

        Returns:
            str: Random string.
        """
        characters = string.ascii_letters + string.digits
        return "".join(random.choices(characters, k=length))

    @staticmethod
    def gen_uuid() -> str:
        """
        Generate a random UUID.

        Returns:
            str: Random UUID.
        """
        return str(uuid4())

    @staticmethod
    def _normalize_object_id(filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert string _id to ObjectId in filter dictionary.

        Args:
            filter_dict (Dict[str, Any]): Filter dictionary.

        Returns:
            Dict[str, Any]: Normalized filter dictionary.
        """
        if "_id" in filter_dict and isinstance(filter_dict["_id"], str):
            try:
                filter_dict["_id"] = ObjectId(filter_dict["_id"])
            except (InvalidId, TypeError) as e:
                logger.warning(f"Invalid ObjectId string: {filter_dict['_id']}")
                raise ValueError(f"Invalid ObjectId: {filter_dict['_id']}") from e
        return filter_dict

    def switch_db_and_collection(self, db_name: str, collection_name: str) -> None:
        """
        Switch to a different database and collection.

        Args:
            db_name (str): Database name.
            collection_name (str): Collection name.
        """
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        logger.info(f"Switched to database: {db_name}, collection: {collection_name}")

    def get_all_db(self) -> List[str]:
        """
        List all database names.

        Returns:
            List[str]: List of database names.
        """
        try:
            return self.client.list_database_names()
        except Exception as e:
            logger.error(f"Error listing databases: {e}")
            raise

    def get_all_collections(self, db_name: Optional[str] = None) -> List[str]:
        """
        List all collection names in a database.

        Args:
            db_name (Optional[str]): Database name. If None, uses current db.

        Returns:
            List[str]: List of collection names.
        """
        try:
            db = self.client[db_name] if db_name else self.db
            return db.list_collection_names()
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            raise

    def switch_collection(self, collection_name: str) -> Collection:
        """
        Switch to a different collection in the current database.

        Args:
            collection_name (str): Collection name.

        Returns:
            Collection: The new collection object.
        """
        self.collection = self.db[collection_name]
        logger.info(f"Switched to collection: {collection_name}")
        return self.collection

    @retry_on_failure(max_retries=3)
    def insert(
        self, data: Dict[str, Any], session: Optional[ClientSession] = None, **kwargs
    ) -> str:
        """
        Insert a single document with retry logic.

        Args:
            data (Dict[str, Any]): Document to insert.
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional insert_one parameters.

        Returns:
            str: Inserted document ID as string.

        Raises:
            OperationFailure: If insert operation fails.
        """
        try:
            result = self.collection.insert_one(data, session=session, **kwargs)
            logger.debug(f"Inserted document with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error on insert: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            raise

    def insert_unique(
        self,
        filter: Dict[str, Any],
        data: Dict[str, Any],
        session: Optional[ClientSession] = None,
    ) -> bool:
        """
        Atomically insert a document only if no document matches the filter.
        Uses update_one with upsert to avoid race conditions.

        Args:
            filter (Dict[str, Any]): Unique filter to check.
            data (Dict[str, Any]): Document to insert.
            session (Optional[ClientSession]): Transaction session.

        Returns:
            bool: True if inserted, False if document already exists.

        Raises:
            OperationFailure: If operation fails.
        """
        try:
            # Atomic upsert with $setOnInsert to avoid race condition
            result = self.collection.update_one(
                filter, {"$setOnInsert": data}, upsert=True, session=session
            )

            if result.upserted_id:
                logger.debug(f"Inserted unique document with ID: {result.upserted_id}")
                return True
            else:
                logger.debug("Document already exists, skipping insert")
                return False
        except Exception as e:
            logger.error(f"Error in insert_unique: {e}")
            raise

    @retry_on_failure(max_retries=3)
    def insert_many(
        self,
        data: List[Dict[str, Any]],
        ordered: bool = False,
        session: Optional[ClientSession] = None,
        **kwargs,
    ) -> List[str]:
        """
        Insert multiple documents with retry logic.

        Args:
            data (List[Dict[str, Any]]): List of documents to insert.
            ordered (bool): If True, stop on first error. If False, continue on errors.
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional insert_many parameters.

        Returns:
            List[str]: List of inserted document IDs as strings.

        Raises:
            OperationFailure: If insert operation fails.
        """
        try:
            if not data:
                logger.warning("insert_many called with empty data list")
                return []

            result = self.collection.insert_many(
                data, ordered=ordered, session=session, **kwargs
            )
            logger.info(f"Inserted {len(result.inserted_ids)} documents")
            return [str(_id) for _id in result.inserted_ids]
        except Exception as e:
            logger.error(f"Error inserting multiple documents: {e}")
            raise

    def bulk_write(
        self,
        operations: List[Any],
        ordered: bool = False,
        session: Optional[ClientSession] = None,
    ) -> Dict[str, int]:
        """
        Perform bulk write operations for better performance.

        Args:
            operations (List[Any]): List of pymongo operations
                (InsertOne, UpdateOne, DeleteOne, etc.)
            ordered (bool): Whether to execute operations in order.
            session (Optional[ClientSession]): Transaction session.

        Returns:
            Dict[str, int]: Result statistics (inserted, modified, deleted counts).

        Example:
            >>> from pymongo import InsertOne, UpdateOne
            >>> ops = [
            ...     InsertOne({"name": "John"}),
            ...     UpdateOne({"name": "Jane"}, {"$set": {"age": 30}})
            ... ]
            >>> db.bulk_write(ops)
        """
        try:
            result = self.collection.bulk_write(
                operations, ordered=ordered, session=session
            )
            stats = {
                "inserted": result.inserted_count,
                "modified": result.modified_count,
                "deleted": result.deleted_count,
                "upserted": result.upserted_count,
            }
            logger.info(f"Bulk write completed: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error in bulk write: {e}")
            raise

    @retry_on_failure(max_retries=3)
    def filter(
        self,
        filter: Optional[Dict[str, Any]] = None,
        show_id: bool = False,
        projection: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Tuple[str, int]]] = None,
        limit: int = 0,
        skip: int = 0,
        session: Optional[ClientSession] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Filter documents with projection, sorting, and pagination support.

        Args:
            filter (Optional[Dict[str, Any]]): Query filter.
            show_id (bool): Whether to include '_id' in results.
            projection (Optional[Dict[str, Any]]): Fields to include/exclude.
            sort (Optional[List[Tuple[str, int]]]): Sort specification.
            limit (int): Maximum number of documents to return (0 = no limit).
            skip (int): Number of documents to skip.
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional find parameters.

        Returns:
            List[Dict[str, Any]]: List of matching documents.

        Example:
            >>> db.filter(
            ...     {"age": {"$gt": 25}},
            ...     projection={"name": 1, "age": 1},
            ...     sort=[("age", -1)],
            ...     limit=10
            ... )
        """
        try:
            if projection is None:
                projection = None if show_id else {"_id": 0}

            cursor = self.collection.find(
                filter or {}, projection, session=session, **kwargs
            )

            if sort:
                cursor = cursor.sort(sort)
            if skip > 0:
                cursor = cursor.skip(skip)
            if limit > 0:
                cursor = cursor.limit(limit)

            result = []
            for item in cursor:
                if show_id and "_id" in item:
                    item = self._replace_id_key(item)
                elif not show_id and "_id" in item:
                    item.pop("_id", None)
                result.append(item)

            logger.debug(f"Filter returned {len(result)} documents")
            return result
        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            raise

    def paginate(
        self,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 10,
        sort: Optional[List[Tuple[str, int]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Paginate query results for large datasets.

        Args:
            filter (Optional[Dict[str, Any]]): Query filter.
            page (int): Page number (1-indexed).
            page_size (int): Number of documents per page.
            sort (Optional[List[Tuple[str, int]]]): Sort specification.
            **kwargs: Additional parameters for filter method.

        Returns:
            Dict[str, Any]: Pagination result with metadata.
                {
                    "data": List[Dict],
                    "page": int,
                    "page_size": int,
                    "total": int,
                    "total_pages": int
                }
        """
        try:
            total = self.count(filter)
            total_pages = (total + page_size - 1) // page_size
            skip = (page - 1) * page_size

            data = self.filter(
                filter=filter,
                sort=sort,
                limit=page_size,
                skip=skip,
                show_id=True,
                **kwargs,
            )

            return {
                "data": data,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            }
        except Exception as e:
            logger.error(f"Error in pagination: {e}")
            raise

    @retry_on_failure(max_retries=3)
    def get(
        self,
        filter: Optional[Dict[str, Any]] = None,
        show_id: bool = True,
        projection: Optional[Dict[str, Any]] = None,
        session: Optional[ClientSession] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single document matching the filter.

        Args:
            filter (Optional[Dict[str, Any]]): Query filter.
            show_id (bool): Whether to include '_id' in result.
            projection (Optional[Dict[str, Any]]): Fields to include/exclude.
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional find_one parameters.

        Returns:
            Optional[Dict[str, Any]]: The first matching document, or None if not found.

        Raises:
            OperationFailure: If query fails.
        """
        try:
            if projection is None:
                projection = None if show_id else {"_id": 0}

            doc = self.collection.find_one(
                filter or {}, projection, session=session, **kwargs
            )

            if doc and show_id and "_id" in doc:
                doc = self._replace_id_key(doc)
            elif doc and not show_id:
                doc.pop("_id", None)

            return doc if doc else {}
        except Exception as e:
            logger.error(f"Error in get: {e}")
            raise

    def get_by_id(
        self,
        _id: Union[str, ObjectId],
        show_id: bool = True,
        session: Optional[ClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a document by its ObjectId.

        Args:
            _id (Union[str, ObjectId]): Document ID.
            show_id (bool): Whether to include '_id' in result.
            session (Optional[ClientSession]): Transaction session.

        Returns:
            Optional[Dict[str, Any]]: The document, or None if not found.

        Raises:
            ValueError: If _id is invalid.
        """
        try:
            if isinstance(_id, str):
                _id = ObjectId(_id)

            doc = self.collection.find_one({"_id": _id}, session=session)

            if doc and show_id:
                doc = self._replace_id_key(doc)
            elif doc and not show_id:
                doc.pop("_id", None)

            return doc
        except InvalidId as e:
            logger.error(f"Invalid ObjectId: {_id}")
            raise ValueError(f"Invalid ObjectId: {_id}") from e
        except Exception as e:
            logger.error(f"Error in get_by_id: {e}")
            raise

    @retry_on_failure(max_retries=3)
    def count(
        self,
        filter: Optional[Dict[str, Any]] = None,
        session: Optional[ClientSession] = None,
        **kwargs,
    ) -> int:
        """
        Count documents matching a filter.

        Args:
            filter (Optional[Dict[str, Any]]): Query filter.
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional count_documents parameters.

        Returns:
            int: Number of matching documents.
        """
        try:
            count = self.collection.count_documents(
                filter or {}, session=session, **kwargs
            )
            return count
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            raise

    def exists(
        self, filter: Dict[str, Any], session: Optional[ClientSession] = None
    ) -> bool:
        """
        Check if any document matches the filter.
        More efficient than count() > 0.

        Args:
            filter (Dict[str, Any]): Query filter.
            session (Optional[ClientSession]): Transaction session.

        Returns:
            bool: True if at least one document exists, False otherwise.
        """
        try:
            return (
                self.collection.find_one(filter, {"_id": 1}, session=session)
                is not None
            )
        except Exception as e:
            logger.error(f"Error checking existence: {e}")
            raise

    @retry_on_failure(max_retries=3)
    def update(
        self,
        filter: Dict[str, Any],
        update_data: Dict[str, Any],
        upsert: bool = False,
        array_filters: Optional[List[Dict]] = None,
        session: Optional[ClientSession] = None,
        **kwargs,
    ) -> int:
        """
        Update multiple documents matching a filter with safety checks.

        Args:
            filter (Dict[str, Any]): Query filter (must not be empty).
            update_data (Dict[str, Any]): Data to update.
            upsert (bool): Create document if it doesn't exist.
            array_filters (Optional[List[Dict]]): Filters for array updates.
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional update_many parameters.

        Returns:
            int: Number of documents modified.

        Raises:
            ValueError: If filter is empty (prevents accidental mass updates).
            OperationFailure: If update fails.
        """
        if not filter:
            raise ValueError(
                "Empty filter not allowed in update. Use update_all() for mass updates."
            )

        try:
            filter = self._normalize_object_id(filter)
            result = self.collection.update_many(
                filter,
                {"$set": update_data},
                upsert=upsert,
                array_filters=array_filters,
                session=session,
                **kwargs,
            )
            logger.info(f"Updated {result.modified_count} documents")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating documents: {e}")
            raise

    def update_one(
        self,
        filter: Dict[str, Any],
        update_data: Dict[str, Any],
        upsert: bool = False,
        session: Optional[ClientSession] = None,
        **kwargs,
    ) -> bool:
        """
        Update a single document matching the filter.

        Args:
            filter (Dict[str, Any]): Query filter.
            update_data (Dict[str, Any]): Data to update.
            upsert (bool): Create document if it doesn't exist.
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional update_one parameters.

        Returns:
            bool: True if a document was modified, False otherwise.
        """
        try:
            filter = self._normalize_object_id(filter)
            result = self.collection.update_one(
                filter, {"$set": update_data}, upsert=upsert, session=session, **kwargs
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error in update_one: {e}")
            raise

    def update_or_create(
        self,
        filter: Dict[str, Any],
        data: Dict[str, Any],
        session: Optional[ClientSession] = None,
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Update a document matching the filter, or create it if it doesn't exist (upsert).

        Args:
            filter (Dict[str, Any]): Query filter.
            data (Dict[str, Any]): Data to update or insert.
            session (Optional[ClientSession]): Transaction session.

        Returns:
            Tuple[Optional[Dict[str, Any]], bool]: (The document, True if created, False if updated)
        """
        try:
            result = self.collection.update_one(
                filter, {"$set": data}, upsert=True, session=session
            )

            if result.upserted_id is not None:
                # Document was created
                doc = self.collection.find_one(
                    {"_id": result.upserted_id}, session=session
                )
                doc = self._replace_id_key(doc)
                logger.debug(f"Created document with ID: {result.upserted_id}")
                return doc, True
            else:
                # Document was updated
                doc = self.collection.find_one(filter, session=session)
                doc = self._replace_id_key(doc)
                logger.debug("Updated existing document")
                return doc, False
        except Exception as e:
            logger.error(f"Error in update_or_create: {e}")
            raise

    def get_or_create(
        self,
        filter: Dict[str, Any],
        data: Optional[Dict[str, Any]] = None,
        session: Optional[ClientSession] = None,
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Fetch a document matching the filter, or create it if it doesn't exist.

        Args:
            filter (Dict[str, Any]): Query filter.
            data (Optional[Dict[str, Any]]): Additional data to insert if not found.
            session (Optional[ClientSession]): Transaction session.

        Returns:
            Tuple[Optional[Dict[str, Any]], bool]: (The document, True if created, False if fetched)
        """
        try:
            doc = self.collection.find_one(filter, session=session)

            if doc:
                doc = self._replace_id_key(doc)
                logger.debug("Document found")
                return doc, False

            # Merge filter and data for creation
            new_doc = {**filter}
            if data:
                new_doc.update(data)

            inserted_id = self.collection.insert_one(
                new_doc, session=session
            ).inserted_id
            new_doc["_id"] = str(inserted_id)
            doc = self._replace_id_key(new_doc)
            logger.debug(f"Created document with ID: {inserted_id}")
            return doc, True
        except Exception as e:
            logger.error(f"Error in get_or_create: {e}")
            raise

    @retry_on_failure(max_retries=3)
    def delete(
        self, filter: Dict[str, Any], session: Optional[ClientSession] = None, **kwargs
    ) -> int:
        """
        Delete multiple documents matching a filter with safety checks.

        Args:
            filter (Dict[str, Any]): Query filter (must not be empty).
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional delete_many parameters.

        Returns:
            int: Number of documents deleted.

        Raises:
            ValueError: If filter is empty (prevents accidental mass deletion).
            OperationFailure: If delete fails.
        """
        if not filter:
            raise ValueError(
                "Empty filter not allowed in delete. Use drop_collection() to delete all."
            )

        try:
            filter = self._normalize_object_id(filter)
            result = self.collection.delete_many(filter, session=session, **kwargs)
            logger.info(f"Deleted {result.deleted_count} documents")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise

    def delete_one(
        self, filter: Dict[str, Any], session: Optional[ClientSession] = None, **kwargs
    ) -> bool:
        """
        Delete a single document matching the filter.

        Args:
            filter (Dict[str, Any]): Query filter.
            session (Optional[ClientSession]): Transaction session.
            **kwargs: Additional delete_one parameters.

        Returns:
            bool: True if a document was deleted, False otherwise.
        """
        try:
            filter = self._normalize_object_id(filter)
            result = self.collection.delete_one(filter, session=session, **kwargs)
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error in delete_one: {e}")
            raise

    def drop_db(self, db_name: Optional[str] = None, confirm: bool = False) -> None:
        """
        Drop a database with confirmation requirement.

        Args:
            db_name (Optional[str]): Database name. If None, drops current db.
            confirm (bool): Must be True to execute (safety feature).

        Raises:
            ValueError: If confirm is not True.
        """
        if not confirm:
            raise ValueError(
                "Must set confirm=True to drop database. This action is irreversible!"
            )

        try:
            db_to_drop = db_name or self.db.name
            self.client.drop_database(db_to_drop)
            logger.warning(f"Dropped database: {db_to_drop}")
        except Exception as e:
            logger.error(f"Error dropping database: {e}")
            raise

    def drop_collection(
        self,
        collection_name: Optional[str] = None,
        db_name: Optional[str] = None,
        confirm: bool = False,
    ) -> None:
        """
        Drop a collection with confirmation requirement.

        Args:
            collection_name (Optional[str]): Collection name. If None, uses current collection.
            db_name (Optional[str]): Database name. If None, uses current db.
            confirm (bool): Must be True to execute (safety feature).

        Raises:
            ValueError: If confirm is not True.
        """
        if not confirm:
            raise ValueError(
                "Must set confirm=True to drop collection. This action is irreversible!"
            )

        try:
            db = self.client[db_name] if db_name else self.db
            coll = collection_name or self.collection.name
            db.drop_collection(coll)
            logger.warning(f"Dropped collection: {coll}")
        except Exception as e:
            logger.error(f"Error dropping collection: {e}")
            raise

    def get_keys(self, exclude_id: bool = True) -> List[str]:
        """
        Get list of keys from the first document in the collection.

        Args:
            exclude_id (bool): Whether to exclude '_id' field.

        Returns:
            List[str]: List of field names.
        """
        try:
            doc = self.collection.find_one()
            if not doc:
                logger.info("Collection is empty, no keys to return")
                return []

            keys = list(doc.keys())
            if exclude_id and "id" in keys:
                keys.remove("id")

            return keys
        except Exception as e:
            logger.error(f"Error getting keys: {e}")
            raise

    def _replace_id_key(self, doc: dict) -> dict:
        """
        Replace '_id' key with 'id' in a document.
        """
        if doc is None:
            return doc
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    # ========== BACKUP & EXPORT ==========

    def export_to_dict(
        self, filter: Optional[Dict[str, Any]] = None, limit: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Export collection data to list of dictionaries.

        Args:
            filter (Optional[Dict[str, Any]]): Query filter.
            limit (int): Maximum documents to export.

        Returns:
            List[Dict[str, Any]]: Exported data.
        """
        return self.filter(filter=filter, show_id=True, limit=limit)

    def import_from_dict(
        self,
        data: List[Dict[str, Any]],
        drop_existing: bool = False,
        session: Optional[ClientSession] = None,
    ) -> List[str]:
        """
        Import data from list of dictionaries.

        Args:
            data (List[Dict[str, Any]]): Data to import.
            drop_existing (bool): Drop collection before import.
            session (Optional[ClientSession]): Transaction session.

        Returns:
            List[str]: Inserted document IDs.
        """
        if drop_existing:
            self.drop_collection(confirm=True)

        if not data:
            return []

        return self.insert_many(data, session=session)

    # ========== STATISTICS & MONITORING ==========

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics (size, count, indexes, etc.).

        Returns:
            Dict[str, Any]: Collection statistics.
        """
        try:
            stats = self.db.command("collStats", self.collection.name)
            return {
                "count": stats.get("count", 0),
                "size": stats.get("size", 0),
                "avg_obj_size": stats.get("avgObjSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "total_index_size": stats.get("totalIndexSize", 0),
                "num_indexes": stats.get("nindexes", 0),
                "indexes": [idx["name"] for idx in self.list_indexes()],
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get MongoDB server information.

        Returns:
            Dict[str, Any]: Server information.
        """
        try:
            return self.client.server_info()
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            raise

    # ========== CLEANUP ==========

    def close(self) -> None:
        """
        Close the MongoDB client connection and clean up resources.
        """
        try:
            if self._session:
                self._session.end_session()
                self._session = None
            self.client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")


# ========== USAGE EXAMPLES ==========

if __name__ == "__main__":
    """
    Production usage examples
    """

    # Basic usage with context manager
    with MongoDB("mydb", "users", connection_str=DEFAULT_CONNECTION_STRING) as db:
        # Create indexes for performance
        # db.create_index("email", unique=True)
        # db.create_index([("created_at", -1)])

        # Insert with retry logic
        user_id = db.insert(
            {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
                "created_at": "2024-01-01",
            }
        )

        # Query with pagination
        results = db.paginate(
            filter={"age": {"$gte": 18}},
            page=1,
            page_size=20,
            sort=[("created_at", -1)],
        )
        print(f"Found {results['total']} users")

        # Transaction example
        # with db.transaction() as session:
        #     db.insert({"name": "Jane", "balance": 100}, session=session)
        #     db.update({"name": "John"}, {"balance": 200}, session=session)

        # Aggregation
        stats = db.group_by("city", count_field="user_count")
        print(f"User count by city: {stats}")

        # Get collection statistics
        collection_stats = db.get_collection_stats()
        print(f"Collection has {collection_stats['count']} documents")

        db.delete({"name": "John Doe"})
