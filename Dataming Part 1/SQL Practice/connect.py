import psycopg2  #import of the psycopg2 python library
import pandas as pd #import of the pandas python library
import pandas.io.sql as psql

##No transaction is started when commands are executed and no commit() or rollback() is required. 
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    # Connect to the postgreSQL server with username, and password credentials
    con = psycopg2.connect(user = "postgres",
                                  password = "sora",
                                  host = "localhost",
                                  port = "5433")
    
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT);
    print("Connected Successfully to PostgreSQL server!!")
    
    # Obtain a DB Cursor to perform database operations
    cursor = con.cursor();
except (Exception, psycopg2.Error) as error :
     print ("Error while connecting to PostgreSQL", error)

#DB_name variable    
name_Database   = "Movie";

# Create DB statement
sqlCreateDatabase = "CREATE DATABASE "+name_Database+";"

try:
    # Execute a SQL command: this creates a new DB
    cursor.execute(sqlCreateDatabase);
    print("Database '"+name_Database+"' Created Successfully!")
except (Exception, psycopg2.Error) as error :
    print("Error While Creating the DB: ",error)
    
finally:
    # Close communication with the database
    cursor.close() #to close the cusrsor
    con.close() #to close the connection/ we will open a new connection to the created DB


#Create "Movie" Table

try:
    #table_name variable
    customerTable="movies"
    create_customerTablee_query = '''CREATE TABLE '''+ customerTable+''' 
              (id INT  PRIMARY KEY     NOT NULL,
               name           TEXT    NOT NULL,
               country        TEXT    NOT NULL,
               email          TEXT   
               ); '''

    #Execute this command (SQL Query)
    cursor.execute(create_customerTablee_query)
    
    # Make the changes to the database persistent
    con.commit()
    print("Table ("+ customerTable +") created successfully in PostgreSQL ")
except (Exception, psycopg2.Error) as error:
    # if it exits with an exception the transaction is rolled back.
    con.rollback()
    print("Error While Creating the DB: ",error)