import sqlite3

# Connect to the database (create a new one if it doesn't exist)
conn = sqlite3.connect('database.db')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Read the SQL file
with open('DB Assistant/lk_pedidos_cstm.sql', 'r') as file:
    sql_script = file.read()

# Execute the SQL script
cursor.executescript(sql_script)

# Commit the changes and close the connection
conn.commit()
conn.close()