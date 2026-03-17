from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from database import get_db
from Auth import verify_admin
from models import Package, PackageUpdate, ShipmentReceipt, SupportMessage
from pydantic import ConfigDict
from typing import Optional


router = APIRouter()


# ---------------- SCHEMA ----------------
class UserSupportMessages(BaseModel):
    sender_name: str | None = None
    sender_email: str
    message: str

class SupportMessageResponse(BaseModel):
    id: int
    sender_name:str | None
    sender_email: str
    message: str
    status: str
    created_at: datetime 
    model_config = ConfigDict(from_attributes=True)


class AdminUpdateShipment(BaseModel):
    carrier: str | None = None
    status: str | None = None
    current_location: str | None = None
    weight: float | None = None
    quantity: int | None = None
    expected_delivery_date: date | None = None

    sender_email: str | None = None
    sender_phone: str | None = None
    sender_address: str | None = None

    receiver_email: str | None = None
    receiver_phone: str | None = None
    receiver_address: str | None = None

    shipment_type: str | None = None
    shipment_mode: str | None = None
    

class AdminPackageRead(BaseModel):
    tracking_number: str

    carrier: str | None
    status: str
    current_location: str | None

    origin: str
    destination: str

    shipment_type: str | None 
    shipment_mode: str | None 

    weight: float | None
    quantity: int | None
    expected_delivery_date: date | None

    sender_name: str
    sender_email: str | None
    sender_phone: str | None
    sender_address: str | None

    receiver_name: str
    receiver_email: str | None
    receiver_phone: str | None
    receiver_address: str | None

    created_at: datetime
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)



class ReceiptCreateSchema(BaseModel):
    payment_type: str
    amount: float
    currency: str = "USD"



class ReceiptResponseSchema(BaseModel):
    id: int
    payment_type: str
    amount: float
    currency: str
    payment_status: str
    issued_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PackageListItemSchema(BaseModel):
    id: int
    tracking_number: str

    sender_name: str
    receiver_name: str

    origin: str
    current_location: str | None
    destination: str

    shipment_type: str | None = None
    shipment_mode: str | None = None
    carrier: str | None

    weight: float | None
    quantity: int | None

    status: str
    expected_delivery_date: date | None

    created_at: datetime
    last_updated: datetime


class PackageListResponse(BaseModel):
    total: int
    packages: list[PackageListItemSchema]
    model_config = ConfigDict(from_attributes=True)


class PackageInfoDocumentSchema(BaseModel):
    id: int
    tracking_number: str
    status: str

    origin: str
    current_location: Optional[str]
    destination: str

    shipment_type: Optional[str] = None  
    shipment_mode: Optional[str] = None  
    carrier: Optional[str]

    sender_name: str
    sender_phone: Optional[str]
    sender_email: Optional[str]
    sender_address: Optional[str]

    receiver_name: str
    receiver_phone: Optional[str]
    receiver_email: Optional[str]
    receiver_address: Optional[str]

    weight: Optional[float]
    quantity: Optional[int]
    expected_delivery_date: Optional[date]

    created_at: datetime
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)



#---------------- USER ----------------
@router.post("/support/message")
def send_support_message(
    payload: UserSupportMessages,
    db: Session = Depends(get_db)
):
    new_message = SupportMessage(
        sender_name = payload.sender_name,
        sender_email = payload.sender_email,
        message = payload.message,
        status = "new",
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return{
        "status": "Sent",
        "message": "Support request recieved"
    }


@router.get(
    "/admin/support/messages",
    response_model=list[SupportMessageResponse]
)
def get_support_messages(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    admin: None = Depends(verify_admin)
):
    offset = (page - 1) * limit

    messages = (
        db.query(SupportMessage)
        .order_by(SupportMessage.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return messages


# ---------------- ADMIN ----------------
@router.put(
    "/admin/support/messages/{id}/read"
)
def mark_message_read(
    id:int,
    db: Session = Depends(get_db),
    admin: None = Depends(verify_admin)

):
    msg= (
        db.query(SupportMessage)
        .filter(SupportMessage.id == id)
        .first()
    )
    if not msg:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )
    msg.status = "read"
    db.commit()
    return {"status": "read"}


@router.put("/admin/packages/{tracking_number}")
def admin_update_package(
    tracking_number:str, 
    payload: AdminUpdateShipment,
    db: Session = Depends(get_db),
    admin: None= Depends(verify_admin)
    ):
    package = (
        db.query(Package)
        .filter(Package.tracking_number == tracking_number)
        .first()
    )

    if not package:
        raise HTTPException(
            status_code=404,
            detail="Package not found"
        )
    
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(package, field, value)


    package.last_updated = datetime.now(timezone.utc)

    db.commit()
    db.refresh(package)


    return{
        "status": "Updated",
        "tracking_number": tracking_number
    }


@router.get("/track/{tracking_number}/history")
def tracking_history(
    tracking_number: str,
    db: Session = Depends(get_db)
):
    updates=(
        db.query(PackageUpdate)
        .filter(PackageUpdate.tracking_number == tracking_number)
        .order_by(PackageUpdate.updated_at.desc())
        .all()
    )
    if not updates:
        raise HTTPException(
            status_code=404,
            detail="No shipment history yet"
        )
    return updates


@router.post(
    "/packages/{tracking_number}/receipt",
    response_model=ReceiptResponseSchema
)
def create_receipt(
    tracking_number: str,
    payload: ReceiptCreateSchema,
    db: Session = Depends(get_db),
    admin: None = Depends(verify_admin)
):
    package = (
    db.query(Package)
    .filter(Package.tracking_number == tracking_number)
    .first()
)

    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    existing = (
        db.query(ShipmentReceipt)
        .filter(ShipmentReceipt.package_id == package.id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Receipt already exists for this package"
        )

    receipt = ShipmentReceipt(
        package_id=package.id,
        payment_type=payload.payment_type,
        amount=payload.amount,
        currency=payload.currency,
        issued_at=datetime.now()
    )

    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return receipt


@router.get("/track/{tracking_number}/receipt")
def view_receipt(
    tracking_number: str,
    db: Session = Depends(get_db)
):
    receipt = (
        db.query(ShipmentReceipt)
        .join(Package)
        .filter(Package.tracking_number == tracking_number)
        .first()
    )

    if not receipt:
        raise HTTPException(
            status_code=404,
            detail="No receipt yet"
        )

    return receipt


@router.get(
    "/admin/packages/{tracking_number}",
    response_model=AdminPackageRead
    )
def get_package_admin(
    tracking_number: str,
    db: Session = Depends(get_db),
    admin: None = Depends(verify_admin)
):
    packages = (
        db.query(Package)
        .filter(Package.tracking_number == tracking_number)
        .first()
    )

    if not packages:
        raise HTTPException(
            status_code=404,
            detail="Package not found")

    return packages


@router.get("/admin/packages", response_model=PackageListResponse)
def list_packages(
    db: Session = Depends(get_db),
    admin: None = Depends(verify_admin)
):
    packages = (
        db.query(Package)
        .order_by(Package.created_at.asc())
        .all()
    )

    return {
        "total": len(packages),
        "packages": packages
    }

@router.get(
    "/admin/packages/{tracking_number}/info",
    response_model=PackageInfoDocumentSchema
)
def generate_package_info(
    tracking_number:str,
    db:Session = Depends(get_db),
    admin: None = Depends(verify_admin)
):
    
    package = (
        db.query(Package)
        .filter(Package.tracking_number == tracking_number)
        .first()
    )

    if not package:
        raise HTTPException(
            status_code= 404,
            detail="Package Not Found"
        )
    return package


