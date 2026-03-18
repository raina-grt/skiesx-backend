from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo


from sqlalchemy.orm import Session
from geopy.geocoders import Nominatim


from database import get_db
from models import Package, PackageUpdate, Settings

#from storage import load_json, save_json
from utils import generate_tracking_number
from schama import router as support_router

from Auth import verify_admin



from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from typing import List


from schama import router as support_router
app.include_router(support_router)



templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.include_router(support_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow localhost for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




#app.mount("/static", StaticFiles(directory="app/static"), name="static")



class PackageCreate(BaseModel):
    sender_name: str
    sender_email: str

    receiver_name: str
    receiver_email: str

    origin: str
    destination: str

    expected_delivery_date: date | None = None

class PackageResponse(BaseModel):
    tracking_number: str
    status: str
    origin: str
    destination: str
    current_location: str
    latitude: float|None=None
    longitude: float|None=None
    expected_delivery_date: date | None = None
    created_at: datetime
    last_updated: datetime

    class Config:
        from_attributes = True        

class UpdatePackage(BaseModel):
    status: str
    current_location: str
    latitude: float|None=None
    longitude: float|None=None
    expected_delivery_date: date | None = None

class PackageUpdateResponse(BaseModel):
    id_number: int
    tracking_number: str
    status: str
    location: str
    latitude: float|None=None
    longitude: float|None=None
    note: str |None = None
    updated_at: datetime
    expected_delivery_date: date | None = None

    class Config:
        from_attributes = True

class SettingsUpdate(BaseModel):
    support_email: str
    support_phone: str

class SettingsPublicResponse(BaseModel):
    support_email: str
    support_phone: str

    class Config:
        from_attributes = True

class SettingsAdminResponse(SettingsPublicResponse):
    status: str


@app.get("/")
def root():
    return {"status": "ok", "service": "Logistics Tracking API"}

@app.post(
    "/packages",
     response_model=PackageResponse
)

def getpackages(
    payload: PackageCreate,
    db: Session = Depends(get_db)
):
    try: 
        now_utc = datetime.now(timezone.utc)

        print("UTC SENT TO FRONTEND:", now_utc, type(now_utc))

        tracking_number = generate_tracking_number()
        if not tracking_number:
            raise ValueError("Tracking number generation failed")
        
        new_package = Package(
            tracking_number=tracking_number,
            sender_name=payload.sender_name,
            sender_email=payload.sender_email,
            receiver_name=payload.receiver_name,
            receiver_email=payload. receiver_email,
            destination=payload.destination,
            origin=payload.origin,
            current_location=payload.origin,
            status="Pending",
            expected_delivery_date=payload.expected_delivery_date,
            created_at=now_utc,
            last_updated=now_utc,
    )

    
    
        db.add(new_package)
        db.commit()
        db.refresh(new_package)

        return new_package
    
    except Exception as e:
        print("🔥 ERROR:", repr(e))
        raise HTTPException(
        status_code=500,
        detail=str(e))
    

geolocator = Nominatim(user_agent="logistics_tracker")

def geocode_location(location: str):
    if not location:
        return None, None
    try:
        loc = geolocator.geocode(location)
        if loc:
            return loc.latitude, loc.longitude
        return None, None
    except Exception as e:
        print("Geocode error:", e)
        return None, None



@app.get(
    "/track/{tracking_number}", 
    response_model=PackageResponse)
def track_package(
    tracking_number: str, 
    db: Session = Depends(get_db)):
    """
    Public tracking endpoint: fetch package by tracking number.
    Does not require any request body.
    """
    package = db.query(Package).filter(Package.tracking_number == tracking_number).first()
    if not package:
        raise HTTPException(
            status_code=404, 
            detail="Package not found")

    # Optional: if latitude/longitude missing, try geocoding current_location
    if package.latitude is None or package.longitude is None:
        lat, lng = geocode_location(package.current_location)
        if lat and lng:
            package.latitude = lat
            package.longitude = lng
            db.commit()
            db.refresh(package)

    return package


@app.put("/admin/packages/{tracking_number}/status")
def update_package_admin(
    tracking_number: str,
    payload: UpdatePackage,
    db: Session = Depends(get_db),
    admin: None = Depends(verify_admin)

):

    now_utc = datetime.now(timezone.utc)
    package = (
        db.query(Package)
        .filter(Package.tracking_number == tracking_number)
        .first()
    )

    if not package:
        raise HTTPException(
            status_code=404,
            detail="package not found!"
        )
    
    lat, lng = payload.latitude, payload.longitude
    if lat is None or lng is None:
        lat, lng = geocode_location(payload.current_location)
    
    # Update package fields
    package.status = payload.status
    package.current_location = payload.current_location
    package.latitude = lat
    package.longitude = lng
    if payload.expected_delivery_date is not None:
        package.expected_delivery_date = payload.expected_delivery_date
    package.last_updated = now_utc
    
    db.commit()
    db.refresh(package)
    
    # Record in package_updates table
    update = PackageUpdate(
        tracking_number=tracking_number,
        status=payload.status,
        location=payload.current_location,
        latitude=lat,
        longitude=lng,
        note=None,
        updated_at=now_utc
    )
    db.add(update)
    db.commit()
    db.refresh(update)
    
    return PackageUpdateResponse(
        id_number=update.id,
        tracking_number=update.tracking_number,
        status=update.status,
        location=update.location,
        latitude=update.latitude,
        longitude=update.longitude,
        note=update.note,
        updated_at=update.updated_at,
        expected_delivery_date=package.expected_delivery_date
    )
@app.put(
    "/admin/settings",
    response_model=SettingsAdminResponse
)
def update_settings_admin(
    payload: SettingsUpdate, 
    db:Session = Depends(get_db),
    admin: None = Depends(verify_admin)

    ):
    
    settings = db.query(Settings).first()

    if not settings:
        settings= Settings(
            support_email=payload.support_email,
            support_phone=payload.support_phone
        )

        db.add(settings)
    else:
        settings.support_email = payload.support_email
        settings.support_phone = payload.support_phone

    db.commit()
    db.refresh(settings)

    return{
        "support_email": settings.support_email,
        "support_phone": settings.support_phone,
        "status": "updated"
    }

@app.get(
    "/settings",
    response_model=SettingsPublicResponse,
)
def get_settings(
    db: Session = Depends(get_db)
):
    settings = db.query(Settings).first()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Settings not configured yet"
        )
    return {
        "support_email": settings.support_email,
        "support_phone": settings.support_phone
    }




@app.get(
    "/track/{tracking_number}/history",
    response_model=List[PackageUpdateResponse]

)
def get_package_history(
    tracking_number: str,

    db: Session = Depends(get_db)
):
    return (
        db.query(PackageUpdate)
        .filter(PackageUpdate.tracking_number == tracking_number)
        .order_by(PackageUpdate.updated_at.desc())
        .all()
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "logistics-api",
        "time": datetime.now(timezone.utc)
    }


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(
        "admin.html",
        {"request": request}
    )

@app.get("/track-page")
def track_page(request: Request):
    return templates.TemplateResponse(
        "track.html",
        {"request": request}
    ) 

