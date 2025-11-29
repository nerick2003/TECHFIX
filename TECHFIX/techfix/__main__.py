from techfix.gui import TechFixApp


def main() -> None:
    app = TechFixApp()
    app.attributes('-fullscreen', True)
    app.mainloop()


if __name__ == "__main__":
    main()
