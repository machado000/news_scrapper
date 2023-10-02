"""
This driver module is part of an ETL project (extract, transform, load).
It's meant to be imported by main.py script and used to manipulate Mongodb databases
v.2023-07-29
"""
import os

import pendulum
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

    def update_collection(self, collection_name, document_list):
        """
        Upsert documents into Mongodb collection. Overwrite existing documents with same `id`

        Args:
        - database (str): The Mongodb database name. Credentials are hard coded into .env variables.
        - collection_name (str): The Mongodb collection name.
        - document_list (list): List of dict objects to be updated as documents on collection

        Returns:
        - HTML page content.
        """
        try:
            # Upload results to Mongodb, overwrite duplicates
            collection = self.db[collection_name]

            new_documents_count = 0
            updated_documents_count = 0

            for document in document_list:
                filter_condition = {"_id": document["_id"]}
                if 'publish_date' in document:
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

    def get_docs_by_domain_and_date(self, collection_name, domain, start_datetime, summarized=False):
        """
        Retrieve documents from given domain with a publish date after the given date.

        Args:
            collection_name (str): The name of the collection to query.
            domain (str): The domain to filter articles by.
            start_datetime (str): The minimum publish date for articles in ISO 8601 format.
            summarized (boolean): Document status.

        Returns:
            list: A list of matching articles as dictionaries.
        """
        try:
            summarized_filter_value = True if summarized else {"$in": [False, None]}

            # Define the query
            query = {
                "domain": domain,
                "publish_date": {"$gte": start_datetime},
                "summarized": summarized_filter_value,
            }
            projection = {
                "_id": 1,
                "publish_date": 1,
                "domain": 1,
                "url": 1,
                "summarized": 1,
            }
            sort_parameter = [("publish_date", 1)]

            # Find and sort the documents
            collection = self.db[collection_name]
            query_result = collection.find(query, projection).sort(sort_parameter)

            # Convert query result to a list of dictionaries
            documents = [document for document in query_result]

            print(f"INFO  - Returned {len(documents)} urls from '{domain}' after '{start_datetime}'")
            return documents

        except PyMongoError as e:
            print("ERROR - Failure querying MongoDB: ", e)
            raise PyMongoError


if __name__ == "__main__":

    mongo_cnx = MongoCnx("news_db")
    client = mongo_cnx.client

    database_list = client.list_database_names()
    print(database_list)

    db = client.get_database(database_list[0])

    collection_list = db.list_collection_names()
    print(collection_list)

    collection = "news"
    domain = "www.wsj.com"
    publish_date = "2023-09-28T12:00"

    documents = mongo_cnx.get_docs_by_domain_and_date(collection, domain, publish_date)

    for document in documents[0:2]:
        print(document)

    # Close the client connection when you're done
    client.close()
