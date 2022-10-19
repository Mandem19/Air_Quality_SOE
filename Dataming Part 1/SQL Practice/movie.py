import psycopg2  #import of the psycopg2 python library
import pandas as pd #import of the pandas python library
import pandas.io.sql as psql

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


#DB_name variable    
name_Database   = "Movie";

# Create DB statement
sqlCreateDatabase = "CREATE DATABASE "+name_Database+";"
cursor = con.cursor();
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