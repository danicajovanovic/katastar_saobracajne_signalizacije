from src.database.connection import get_connection


def main():
    try:
        conn = get_connection()
        print("Uspesno povezivanje sa bazom.")
        conn.close()
    except Exception as e:
        print("Greska pri povezivanju:")
        print(e)


if __name__ == "__main__":
    main()