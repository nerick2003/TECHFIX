from techfix.gui import TechFixApp
import logging


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = TechFixApp()
    app.mainloop()


if __name__ == "__main__":
    main()


