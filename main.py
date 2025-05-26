from src.database.init_db import init_db
from src.ui.start_ui import start_ui


def main():
    init_db()
    start_ui()


if __name__ == "__main__":
    main()
