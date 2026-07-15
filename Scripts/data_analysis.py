import pandas as pd
import os

# Excel file location
file_path = r"C:\Users\imadk\Downloads\Qadri_Group\Data\Raw\Purchases List Report.xls"

# Check if file exists
if os.path.exists(file_path):
    print("File found successfully")
else:
    print("File not found")
    exit()


# Read Excel file
excel = pd.ExcelFile(file_path)

print("\nAvailable Sheets:")
print(excel.sheet_names)


# Read required sheet
sheet_name = "Sheet1"

df = pd.read_excel(
    file_path,
    sheet_name=sheet_name
)


print("\n==========================")
print("Sheet Name:", sheet_name)

print("\nNumber of Rows:")
print(df.shape[0])

print("\nNumber of Columns:")
print(df.shape[1])


print("\nColumn Names:")
for col in df.columns:
    print("-", col)


print("\nData Types:")
print(df.dtypes)


print("\nMissing Values:")
print(df.isnull().sum())


print("\nFirst 10 Records:")
print(df.head(10))