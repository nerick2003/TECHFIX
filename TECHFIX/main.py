from techfix.gui import TechFixApp
import logging


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = TechFixApp()
    # Let the app decide its initial window state (restored from settings, F11/menu toggle).
    app.mainloop()


if __name__ == "__main__":
    main()


