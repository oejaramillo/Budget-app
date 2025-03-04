import psycopg2
from pathlib import Path
import pandas as pd
import environ
import os

# Enviroment variables
BASE_DIR = Path('.env').resolve()

env = environ.Env()
environ.Env.read_env(BASE_DIR)

# Database connection
conn = psycopg2.connect(
    host = env('DB_HOST'),
    database = env('DB_NAME'),
    user = env('DB_USER'),
    password = env('DB_PASSWORD'),
    port = env('DB_PORT')
)

cursor = conn.cursor()
print(cursor)

# Datos para subir
datos_dir = os.path.expanduser("/home/edu/edu/datos")

file = 'datos.csv'

datos = pd.read_csv(os.path.join(datos_dir, file))

# Currencies
monedas = datos['moneda'].unique()

data_to_insert = [
    (monedas[0], 'USD', 1, True, True),
    (monedas[1], 'ARG', 983.73,  False, True),
    (monedas[2], 'COP', 4289.14, False, True)
]

insert_query = """
INSERT INTO "tracker_currencies" (name, code, exchange_rate, principal, is_active)
VALUES (%s, %s, %s, %s, %s)
"""

#cursor.executemany(insert_query, data_to_insert)
cursor.executemany(insert_query, data_to_insert)
conn.commit()
