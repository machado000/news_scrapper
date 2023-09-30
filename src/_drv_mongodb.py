"""
This driver module is part of an ETL project (extract, transform, load).
It's meant to be imported by main.py script and used to manipulate Mongodb databases
v.2023-07-29
"""
import os

from datetime import datetime
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi


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

    def update_collection(self, collection, document_list):
        """
        Upsert documents into Mongodb collection. Overwrite existing documents with same `id`

        Args:
        - database (str): The Mongodb database name. Credentials are hard coded into .env variables.
        - collection (str): The Mongodb collection name.
        - document_list (list): List of dict objects to be updated as documents on collection

        Returns:
        - HTML page content.
        """
        # Upload results to Mongodb, overwrite duplicates
        collection = self.db[collection]

        new_documents_count = 0
        updated_documents_count = 0

        for document in document_list:
            filter_condition = {"_id": document["_id"]}
            update_data = {"$set": document}
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

    def get_urls_by_source_and_date(self, collection_name, source, start_date):
        """
        Get a list of URLs from a specific source with a publish date after the given date.

        Args:
        - collection_name (str): The name of the collection to query.
        - source (str): The source to filter documents by.
        - start_date (str): The start date in YYYY-MM-DD format.

        Returns:
        - list: A list of URLs that meet the criteria.
        """
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            collection = self.db[collection_name]
            query = {
                "source": source,
                "publish_date": {"$gte": start_datetime.strftime("%a, %d %b %Y %H:%M:%S %z")}
            }
            # print("DEBUG - Query:", query)
            cursor = collection.find(query)
            urls = [doc.get("url") for doc in cursor]

            print(f"INFO  - Returned {len(urls)} urls from '{source}' after '{start_datetime}'")
            return urls

        except Exception as e:
            print("ERROR - ", e)
            return []


if __name__ == "__main__":

    client = MongoCnx("news_db").client

    database_list = client.list_database_names()
    print(database_list)

    db = client.get_database(database_list[0])

    collection_list = db.list_collection_names()
    print(collection_list)

    # Close the client connection when you're done
    client.close()
