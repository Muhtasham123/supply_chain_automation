from pathlib import Path

directory = Path(r"C:\Users\hp\Desktop\internship\project\data\logistics")

files = list(directory.iterdir())

EXCEL_FILE = files[0]
print(EXCEL_FILE)