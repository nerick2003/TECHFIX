import os
from pathlib import Path
from techfix.gui import TechFixApp, filedialog

def main():
    out = Path(os.path.dirname(__file__)).parent / "export_all_test.xlsx"
    filedialog.asksaveasfilename = lambda **kwargs: str(out.resolve())
    app = TechFixApp()
    try:
        app._export_all_to_excel()
    finally:
        app.destroy()
    print(str(out.resolve()))

if __name__ == '__main__':
    main()
