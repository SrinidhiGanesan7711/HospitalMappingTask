# 🏥 Tamil Nadu Maternity Hospital Mapper with LocationIQ

This Python script processes a list of **maternity hospitals in Tamil Nadu**,  
extracts structured information, retrieves **pincodes using India Post API**,  
and fetches **latitude and longitude coordinates using LocationIQ**.  
The final dataset is ready for **map visualization** or **geospatial analysis**.

---

## 📌 Objective

Many hospital records have incomplete or unstructured addresses without geographic coordinates. This tool helps:

- Standardize and clean hospital data.
- Enrich the data with **pincodes** and **geo-coordinates**.
- Prepare datasets suitable for **map-based dashboards or analysis**.

---

## 🚀 Features

✅ Clean hospital name and address  
✅ Extract phone numbers and existing pincodes  
✅ Lookup missing pincodes using [India Post API](https://api.postalpincode.in)  
✅ Fetch lat-long using [LocationIQ Geocoding API](https://locationiq.com/)  
✅ Export to Excel for reporting or map visualization  

---

## 🧭 Workflow

graph TD
    A[User Uploads Excel File (with or without Pincode)] --> B[Script Cleans & Enriches Data]
    B --> C{Is Pincode Present?}
    C -- Yes --> D[Use Provided Pincode]
    C -- No --> E[Extract Place Name & Lookup Pincode via India Post API]
    D --> F[Fetch Lat/Long using LocationIQ]
    E --> F
    F --> G[Return JSON Response of Cleaned Hospital Data]
    G --> H[Store Hospital Data in Database]
    H --> I[User Opens Map Interface]
    I --> J[Visualize Uploaded Hospital Locations on Map]


▶️ Execution Steps
✅ Step 1: Extract Pincode and Clean Data from Excel
Run the script manually to process the hospital data and save a cleaned Excel file:

```bash
python pincode.py

This will generate Madurai.xlsx(sample) with cleaned hospital name, address, pincode, and phone number.

✅ Step 2: Start the FastAPI Application
Use the following command to launch your FastAPI backend:

```bash
uvicorn main:app --reload

Replace main with your actual Python file name 

✅ Step 3: Upload Excel via API
Use an API endpoint or web interface to upload the generated Madurai.xlsx file.

The backend will parse the file, convert it into JSON format, and store it in the database.

✅ Step 4: View Hospital Locations on Map
Navigate to your frontend map interface.

The uploaded hospital locations will be displayed on the map using the latitude and longitude resolved via LocationIQ.