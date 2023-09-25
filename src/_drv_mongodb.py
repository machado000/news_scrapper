"""
This driver module is part of an ETL project (extract, transform, load).
It's meant to be imported by main.py script and used to manipulate Mongodb databases
v.2023-07-29
"""
import os
import socket

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()
username = os.getenv('ATLAS_USER')
password = os.getenv('ATLAS_PASSWORD')

if __name__ == "__main__":

    # Specify the domain you want to resolve
    domain = "example.com"

    try:
        # Use the gethostbyname() method to resolve the domain to an IP address
        ip_address = socket.gethostbyname(domain)
        print(f"The IP address of {domain} is {ip_address}")
    except socket.gaierror as e:
        # Handle the case where the domain cannot be resolved
        print(f"Could not resolve {domain}: {e}")

    uri = f"mongodb+srv://{username}:{password}@cluster-1.m7jgczk.mongodb.net/?retryWrites=true&w=majority&appName=AtlasApp"  # noqa
    print(uri)

    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))

    # Send a ping to confirm a successful connection
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
