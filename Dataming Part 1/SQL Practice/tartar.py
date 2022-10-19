import psycopg2  #import of the psycopg2 python library
import pandas as pd #import of the pandas python library
import pandas.io.sql as psql



# get a new connection but this time point to the created "tartupurchases" DB.
con = psycopg2.connect(user = "postgres",
                       password = "sora", 
                       host = "localhost", #Using Docker we can refer to containers by name
                       port = "5433",
                       database = "tartupurchases")

try:
    # Obtain a new DB Cursor (to "tartupurchases" DB )
    cursor = con.cursor();
    print("connected again to the server and cusor now on tartupurchases DB !!")
except (Exception, psycopg2.Error) as error:
    print("Error in Connection",error)


#Create "Customer" Table

try:
    #table_name variable
    customerTable="customer"
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

    # [information_schema.tables] keep listing of every table being managed by Postgres for a particular database.
# specifying the tabel_schema to 'public' to only list tables that you create.
cursor.execute("""SELECT table_name 
                  FROM information_schema.tables 
                  WHERE table_schema = 'public'  
               """)

for table in cursor.fetchall():
    print(table)

sql_insert_customers = "INSERT INTO customer (id,name,country,email) VALUES(%s,%s,%s,%s)"

#list of customers (With Their attributes values)
#None here means value will be missing in the table
customer_List=[
            (1, "Mohamed Ragab", "Egypt", "mohamed.ragb@ut.ee"),
            (2,"John Smith", "Finland","j.smith@hotmail.com"),
            (3,"Aisha Kareem","India",None),
            (4,"Jean Lime","Canda","jeanlime@gmail.com"),
            (5,"Hassan Eldeeb","Egypt",None)]

try:
    # execute the INSERT statement
    cursor.executemany(sql_insert_customers,customer_List)
    # commit the changes to the database
    con.commit()
    #the number of inserted rows/tuples
    count = cursor.rowcount
    print (count, "Record inserted successfully into customers table")

except (Exception, psycopg2.Error) as error :
    con.rollback()
    print ("Error while Inserting the data to the table, Details: ",error)

    sql_select_query = """ SELECT * FROM customer  """

try:
    
    cursor.execute(sql_select_query, (1,))
    person_records = cursor.fetchall() 
    print("Print each row and it's columns values:\n")
    for row in person_records:
        print("Id = ", row[0], )
        print("Name = ", row[1], )
        print("Country = ", row[2], )
        print("Email = ", row[3], "\n")
except(Exception, psycopg2.Error) as error :
    con.rollback()
    print("Error:", error)