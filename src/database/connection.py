import psycopg2


def get_connection():
    return psycopg2.connect(
        dbname="katastar_saobracajne_signalizacije",
        user="postgres",
        password="Danica987",
        host="localhost",
        port="5432"
    )