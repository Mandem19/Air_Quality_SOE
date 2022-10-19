


import psycopg2  #import of the psycopg2 python library
import pandas as pd #import of the pandas python library
import pandas.io.sql as psql

##No transaction is started when commands are executed and no commit() or rollback() is required. 
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# get a new connection but this time point to the created "tartupurchases" DB.
con = psycopg2.connect(user = "postgres",
                       password = "sora", 
                       host = "localhost", #Using Docker we can refer to containers by name
                       port = "5433",
                       database = "videogames")


try:
    # Obtain a new DB Cursor (to "videogames" DB )
    cursor = con.cursor();
    print("connected again to the server and cusor now on videogames DB !!")
except (Exception, psycopg2.Error) as error:
    print("Error in Connection",error)



# [information_schema.tables] keep listing of every table being managed by Postgres for a particular database.
# specifying the tabel_schema to 'public' to only list tables that you create.
cursor.execute("""SELECT table_name 
                  FROM information_schema.tables 
                  WHERE table_schema = 'public'  
               """)

for table in cursor.fetchall():
    print(table)






sql_insert_genre = "INSERT INTO genre (id,genre_name) VALUES(%s,%s)"

#list of games (With Their attributes values)
#None here means value will be missing in the table
genre_List=[
(1,'Action'),
(2,'Adventure'),
(3,'Fighting'),
(4,'Misc'),
(5,'Platform'),
(6,'Puzzle'),
(7,'Racing'),
(8,'Role-Playing'),
(9,'Shooter'),
(10,'Simulation'),
(11,'Sports'),
(12,'Strategy')]



try:
    # execute the INSERT statement
    cursor.executemany(sql_insert_genre,genre_List)
    # commit the changes to the database
    con.commit()
    #the number of inserted rows/tuples
    count = cursor.rowcount
    print (count, "Record inserted successfully into genre table")

except (Exception, psycopg2.Error) as error :
    con.rollback()
    print ("Error while Inserting the data to the table, Details: ",error)

    sql_select_query = """ SELECT * FROM genre  """

try:
    
    cursor.execute(sql_select_query, (1,))
    person_records = cursor.fetchall() 
    print("Print each row and it's columns values:\n")
    for row in person_records:
        print("id = ", row[0], )
        print("genre_name= ", row[1], "\n")
except(Exception, psycopg2.Error) as error :
    con.rollback()
    print("Error:", error)