import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    return psycopg2.connect(
        dbname=os.environ.get(
            "DB_NAME",
            "katastar_saobracajne_signalizacije",
        ),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
    )


@contextmanager
def managed_connection():
    """
    Otvara konekciju i garantuje:
    - commit ako je sve uspešno;
    - rollback ako se desi greška;
    - zatvaranje konekcije u svim slučajevima.
    """
    conn = get_connection()

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def managed_cursor():
    """
    Otvara konekciju i cursor i automatski ih zatvara.
    """
    with managed_connection() as conn:
        with conn.cursor() as cur:
            yield cur