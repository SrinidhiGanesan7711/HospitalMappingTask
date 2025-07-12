from typing import Optional
from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.requests import Request
import pandas as pd   
import io
import requests
import uuid
import time
import uvicorn
from db import get_pool

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="templates"), name="static")
templates = Jinja2Templates(directory="templates")


app = FastAPI()

LOCATIONIQ_API_KEY = "pk.0ef8f41d239225231e0710926a8e63c0"

def build_location_query(*parts):
    clean_parts = [str(part).strip().strip(',') for part in parts if part and str(part).strip().lower() != "nan"]
    return ", ".join(clean_parts)

def is_valid_tamilnadu_coordinates(lat, lng):
    try:
        return 8.0 <= lat <= 13.5 and 76.0 <= lng <= 80.5
    except:
        return False

def geocode_location(*parts, max_retries=3):
    query = build_location_query(*parts)
    url = "https://us1.locationiq.com/v1/search"
    params = {
        "key": LOCATIONIQ_API_KEY,
        "q": query,
        "format": "json",
        "limit": 1
    }

    retries = 0
    while retries < max_retries:
        print(f"🔍 Geocoding: '{query}'")
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                return lat, lng
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                wait = 2 ** retries
                print(f"429 Too Many Requests — Retrying after {wait}s...")
                time.sleep(wait)
                retries += 1
            else:
                print(f"Error geocoding '{query}': {e}")
                break
        except Exception as e:
            print(f"Error geocoding '{query}': {e}")
            break
    return None, None

@app.post("/upload-hospitals/")
async def upload_hospitals(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        raw_df = pd.read_excel(io.BytesIO(contents), header=0)

        print("Raw Excel columns:", raw_df.columns.tolist())

        raw_df.columns = [str(col).strip() for col in raw_df.columns]

        print("Cleaned columns:", raw_df.columns.tolist())

        required_cols = ["Hospital Name", "Address", "Pincode", "Phone", "District"]
        missing = [col for col in required_cols if col not in raw_df.columns]

        if missing:
            print(f"Missing columns: {missing}")
            raise HTTPException(status_code=400, detail="Missing required columns in Excel file.")

        df = raw_df.copy()

        df["District"] = df["District"].ffill().fillna("Tamil Nadu")

        print("District column after filldown:", df["District"].tolist())

        user_id = str(uuid.uuid4())
        hospitals = []
        hospital_records_to_insert = []
        
        for _, row in df.iterrows():
            district = str(row["District"]).strip().replace("nan", "") or "Tamil Nadu"
            name = str(row["Hospital Name"]).strip()
            address = str(row["Address"]).strip().strip(",").replace("nan", "")
            pincode_raw = str(row["Pincode"]).strip().replace("nan", "")
            phone = str(row["Phone"]).strip().replace("nan", "")
            pincode = pincode_raw.split(".")[0] if "." in pincode_raw else pincode_raw

            lat, lng = geocode_location(address, district, pincode, "Tamil Nadu", "India")

            if not lat or not lng or not is_valid_tamilnadu_coordinates(lat, lng):
                print(f" Fallback geocoding for '{name}'...")
                lat, lng = geocode_location(name, district, "Tamil Nadu", "India")

            hospital_records_to_insert.append((name, address, pincode, phone, lat, lng))
            hospitals.append({
                "name": name,
                "address": address,
                "pincode": pincode,
                "phone": phone,
                "latitude": lat,
                "longitude": lng,
                "user_id": user_id
            })
            
        pool = await get_pool()

        async with pool.acquire() as conn:
            async with conn.transaction():
                insert_query = """
                    INSERT INTO hospitals (name, address, pincode, phone, latitude, longitude)
                    VALUES {} 
                    ON CONFLICT DO NOTHING 
                    RETURNING id, name, address, pincode, phone, latitude, longitude
                """.format(
                    ",".join(
                        f"('{name}', '{address}', '{pincode}', '{phone}', {lat or 'NULL'}, {lng or 'NULL'})"
                        for name, address, pincode, phone, lat, lng in hospital_records_to_insert
                    )
                )

                inserted_rows = await conn.fetch(insert_query)
                
                mapping_records = []
                for row in inserted_rows:
                    mapping_records.append((user_id, row["id"]))

                if mapping_records:
                    values = ",".join(f"('{uid}', {hid})" for uid, hid in mapping_records)
                    await conn.execute(f"""
                        INSERT INTO user_hospital_mapping (user_id, hospital_id)
                        VALUES {values}
                        ON CONFLICT DO NOTHING
                    """)

        return JSONResponse(content={
            "message": f"{len(hospitals)} hospitals processed and inserted.",
            "user_id": user_id,
            "hospitals": hospitals
        })

    except Exception as e:
        print(f"Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

    
@app.get("/get-hospitals/")
async def get_hospitals():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT h.name, h.address, h.pincode, h.phone, h.latitude, h.longitude
                FROM hospitals h
                WHERE h.latitude IS NOT NULL AND h.longitude IS NOT NULL
            """)

        hospitals = [{
            "name": row["name"],
            "address": row["address"],
            "pincode": row["pincode"],
            "phone": row["phone"],
            "latitude": row["latitude"],
            "longitude": row["longitude"]
        } for row in rows]

        return {"hospitals": hospitals}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/get-hospitals-without-location/")
async def get_hospitals_without_location():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT name, address, pincode, phone
                FROM hospitals
                WHERE latitude IS NULL OR longitude IS NULL
            """)

        hospitals = [dict(row) for row in rows]
        return {"hospitals": hospitals}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/missing-location-hospitals", response_class=HTMLResponse)
async def show_missing_location_hospitals(request: Request):
    return templates.TemplateResponse("missing_locations.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(app,host="0.0.0.0",port=8000)
