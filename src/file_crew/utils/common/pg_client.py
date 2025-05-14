import psycopg2

postgres_config = {
    "user": "blockuser",
    "password": "vinciluser",
    "host": "18.206.131.186",
    "port": 5452,
    "database": "blockreconsit"
}

pg_client = psycopg2.connect(**postgres_config)
print("-------------->pgclient:",pg_client)