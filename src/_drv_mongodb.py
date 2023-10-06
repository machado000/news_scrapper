"""
This driver module is part of an ETL project (extract, transform, load).
It's meant to be imported by main.py script and used to manipulate Mongodb databases
v.2023-07-29
"""
import os
import pendulum
from bson.regex import Regex
from datetime import datetime, date
from dotenv import load_dotenv
from pymongo.errors import PyMongoError
from pymongo.mongo_client import MongoClient


class MongoCnx():

    def __init__(self, database="news_db"):

        load_dotenv()
        username = os.getenv('MONGODB_USER')
        password = os.getenv('MONGODB_PASSWORD')
        hostname = "10.109.222.5"
        # port = "27017"
        self.database_name = database

        uri = f"mongodb://{username}:{password}@{hostname}/{database}"

        self.client = MongoClient(uri)
        self.db = self.client[database]  # Get the database here

    def insert_documents(self, collection_name, document_list):
        """
        Insert new documents into MongoDB collection. Do not update existing documents.

        Args:
        - collection_name (str): The MongoDB collection name.
        - document_list (list): List of dict objects to be inserted as new documents in the collection.

        Returns:
        - None.
        """
        try:
            # Access the collection in MongoDB
            collection = self.db[collection_name]
            new_document_list = document_list[:]

            inserted_doc_count = 0
            duplicate_doc_count = 0

            for document in new_document_list:

                # Check if the document with the same _id already exists
                existing_document = collection.find_one({"_id": document["_id"]})

                if existing_document is None:
                    # Document with the same _id doesn't exist, insert the new document
                    if 'publish_date' in document and not isinstance(document['publish_date'], datetime):
                        # Convert the 'publish_date' string to a Python datetime object
                        parsed_date = pendulum.parse(document['publish_date'])
                        document['publish_date'] = parsed_date

                    document['last_modified'] = datetime.now()

                    collection.insert_one(document)
                    inserted_doc_count += 1
                else:
                    duplicate_doc_count += 1

            print(
                f"INFO  - Found {duplicate_doc_count} duplicates, inserted {inserted_doc_count} new documents \
into '{self.db.name}' collection '{collection.name}'")
            return None

        except PyMongoError as e:
            print("ERROR - Failure querying MongoDB: ", e)
            raise PyMongoError

    def update_collection(self, collection_name, document_list):
        """
        Upsert documents into Mongodb collection. Overwrite existing documents with same `id`

        Args:
        - collection_name (str): The Mongodb collection name.
        - document_list (list): List of dict objects to be updated as documents on collection

        Returns:
        - None.
        """
        try:
            # Access the collection in MongoDB
            collection = self.db[collection_name]
            new_document_list = document_list[:]

            new_documents_count = 0
            updated_documents_count = 0

            for document in new_document_list:
                filter_condition = {"_id": document["_id"]}
                if 'publish_date' in document and not isinstance(document['publish_date'], datetime):
                    # Convert the 'publish_date' string to a Python datetime object
                    parsed_date = pendulum.parse(document['publish_date'])
                    document['publish_date'] = parsed_date

                update_data = {
                    "$set": document,
                    "$currentDate": {'lastmodified': {"$type": 'date'}}
                }
                update_result = collection.update_one(filter_condition, update_data, upsert=True)

                # Check if the document was updated or inserted
                if update_result.matched_count > 0:
                    updated_documents_count += 1
                else:
                    new_documents_count += 1

            print(
                f"INFO  - Inserted {new_documents_count}, updated {updated_documents_count} documents \
into '{self.db.name}' collection '{collection.name}'")
            return None

        except PyMongoError as e:
            print("ERROR - Failure querying MongoDB: ", e)
            raise PyMongoError

    def get_doc_list(self, collection_name, domain=None, start_publish_date=None, status=None):
        """
        Retrieve document list from given domain and publish date.

        Args:
            collection_name (str): The name of the collection to query.
            domain (str): The domain to filter articles by.
            start_datetime (datetime object): The minimum publish date as datetime object or string in ISO-8601 format.
            status (str): Document status like 'fetched', 'content_parsed', 'summarized', 'matched', 'email_sent'.

        Returns:
            list: A list of matching articles as dictionaries.
        """
        try:
            # Define the query
            query = {}
            if domain is not None:
                query["domain"] = domain

            if start_publish_date is not None:
                parsed_date = start_publish_date if isinstance(
                    start_publish_date, (date, datetime)) else pendulum.parse(start_publish_date)
                query["publish_date"] = {"$gte": parsed_date}

            if status is not None:
                query["status"] = status

            projection = {
                "_id": 1,
                "publish_date": 1,
                "domain": 1,
                "url": 1,
                "status": 1,
            }
            sort_parameter = [("publish_date", 1)]

            # Find and sort the documents
            collection = self.db[collection_name]
            query_result = collection.find(query, projection).sort(sort_parameter)

            # Convert query result to a list of dictionaries
            documents = [document for document in query_result]

            print(f"INFO  - Returned {len(documents)} urls with domain '{domain}' and status '{status}'")
            return documents

        except PyMongoError as e:
            print("ERROR - Failure querying MongoDB: ", e)
            raise PyMongoError

    def get_doc_content(self, collection_name, domain=None, start_publish_date=None, status=None):
        """
        Retrieve document content from given domain and publish date.

        Args:
            collection_name (str): The name of the collection to query.
            domain (str): The domain to filter articles by.
            start_datetime (datetime object): The minimum publish date as datetime object or string in ISO-8601 format.
            status (str): Document status like 'fetched', 'content_parsed', 'summarized', 'matched', 'email_sent'.

        Returns:
            list: A list of matching articles as dictionaries.
        """
        try:
            # Define the query
            query = {}
            if domain is not None:
                query["domain"] = domain

            if start_publish_date is not None:
                parsed_date = start_publish_date if isinstance(
                    start_publish_date, (date, datetime)) else pendulum.parse(start_publish_date)
                query["publish_date"] = {"$gte": parsed_date}

            if status is not None:
                query["status"] = status

            projection = {
                "_id": 1,
                "publish_date": 1,
                "content": 1,
                "status": 1,
            }
            sort_parameter = [("publish_date", 1)]

            # Find and sort the documents
            collection = self.db[collection_name]
            query_result = collection.find(query, projection).sort(sort_parameter)

            # Convert query result to a list of dictionaries
            documents = [document for document in query_result]

            print(f"INFO  - Returned {len(documents)} documents with domain '{domain}' and status '{status}'")
            return documents

        except PyMongoError as e:
            print("ERROR - Failure querying MongoDB: ", e)
            raise PyMongoError

    def get_doc_summary(self, collection_name, domain=None, start_publish_date=None, status=None):
        """
        Retrieve document summaries from given domain and publish date.

        Args:
            collection_name (str): The name of the collection to query.
            domain (str): The domain to filter articles by.
            start_datetime (datetime object): The minimum publish date as datetime object or string in ISO-8601 format.
            status (str): Document status like 'fetched', 'content_parsed', 'summarized', 'matched', 'email_sent'.

        Returns:
            list: A list of matching articles as dictionaries.
        """
        try:
            # Define the query
            query = {}
            if domain is not None:
                query["domain"] = domain

            if start_publish_date is not None:
                parsed_date = start_publish_date if isinstance(
                    start_publish_date, (date, datetime)) else pendulum.parse(start_publish_date)
                query["publish_date"] = {"$gte": parsed_date}

            if status is not None:
                query["status"] = status

            projection = {
                "_id": 1,
                "publish_date": 1,
                "domain": 1,
                "url": 1,
                "title": 1,
                "summary": 1,
                "status": 1,
            }
            sort_parameter = [("publish_date", 1)]

            # Find and sort the documents
            collection = self.db[collection_name]
            query_result = collection.find(query, projection).sort(sort_parameter)

            # Convert query result to a list of dictionaries
            documents = [document for document in query_result]

            print(f"INFO  - Returned {len(documents)} documents with status '{status}'")
            return documents

        except PyMongoError as e:
            print("ERROR - Failure querying MongoDB: ", e)
            raise PyMongoError

    def match_doc_with_keywords(self, collection_name, start_publish_date=None, status="summarized", keyword_list=None):

        if keyword_list is None:
            print("ERROR - No keywords were passed to match document contents!!!")
            return None

        documents = []
        all_matches = []

        for keyword in keyword_list:
            try:
                # Define the query
                query = {}

                if start_publish_date is not None:
                    parsed_date = start_publish_date if isinstance(
                        start_publish_date, (date, datetime)) else pendulum.parse(start_publish_date)
                    query["publish_date"] = {"$gte": parsed_date}

                if status is not None:
                    query["status"] = status

                query["$or"] = [
                    {"content": Regex(f".*{keyword}.*", "i")},
                    {"title": Regex(f".*{keyword}.*", "i")}
                ]
                # print("DEBUG - query:", query)
                projection = {
                    "_id": 1,
                    "status": 1,
                }
                sort_parameter = [("_id", 1)]

                # Find and sort the documents
                collection = self.db[collection_name]
                query_result = collection.find(query, projection).sort(sort_parameter)

                # Convert query result to a list of dictionaries
                documents = [document for document in query_result]
                documents = [{"keyword_match": keyword, **item} for item in documents]
                documents = [{**item, "status": "matched"} for item in documents]

                all_matches.extend(documents)

            except PyMongoError as e:
                print("ERROR - Failure querying MongoDB: ", e)
                raise PyMongoError

        print(f"INFO  - Returned {len(all_matches)} documents with matching keywords'")
        return all_matches


if __name__ == "__main__":

    mongo_cnx = MongoCnx("news_db")
    client = mongo_cnx.client

    # List databases and collections
    database_list = client.list_database_names()
    print(database_list)

    db = client.get_database(database_list[0])
    collection_list = db.list_collection_names()
    print(collection_list)

    # Test get_doc_list() and get_doc_content()
    collection_name = "news"
    domain = "www.wsj.com"
    start_publish_date = datetime(2023, 10, 1, 12, 00)

    documents = mongo_cnx.get_doc_list(
        collection_name=collection_name, domain=None, start_publish_date=start_publish_date, status="summarized")
    print(documents[-1])

    documents = mongo_cnx.get_doc_content(
        collection_name=collection_name, domain=None, start_publish_date=start_publish_date, status="summarized")
    print("INFO  - id:", documents[-1]["_id"], "content:", documents[-1]["content"][0:100], "...")

    # Test match_doc_content()
    collection = mongo_cnx.db["keywords"]
    keywords = collection.distinct("keyword", {"active": True})
    keywords = [item.strip('"') for item in keywords]
    # print("DEBUG - ", keywords)

    collection_name = "news"

    matches = mongo_cnx.match_doc_with_keywords(collection_name, start_publish_date=None, keyword_list=keywords)
    print(matches)

    # Close the client connection when you're done
    client.close()
