from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, Date
from database import Base
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String
from database import Base



class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tracking_number = Column(String, unique=True, index=True)
    status = Column(String)

    # Sender details
    sender_name = Column(String)
    sender_email = Column(String)
    sender_phone = Column(String)
    sender_address = Column(String)

    # Receiver details
    receiver_name = Column(String)
    receiver_email = Column(String)
    receiver_phone = Column(String)
    receiver_address = Column(String)

    # Shipment details
    origin = Column(String)
    origin_lat = Column(Float, nullable=True)
    origin_lng = Column(Float, nullable=True)
    current_location = Column(String)
    destination = Column(String)
    destination_lat = Column(Float, nullable=True)
    destination_lng = Column(Float, nullable=True)
    carrier = Column(String)
    shipment_type = Column(String)
    shipment_mode = Column(String)
    quantity = Column(Integer)
    weight = Column(Float)
    expected_delivery_date = Column(Date, nullable=True)

    latitude = Column(Float, nullable=True)    # <-- dynamic current latitude
    longitude = Column(Float, nullable=True)   # <-- dynamic current longitude

    # Admin / receipt
    payment_mode = Column(String)
    comments = Column(String)

    # System details
    created_at = Column(DateTime(timezone=True))
    last_updated = Column(DateTime(timezone=True))


class PackageUpdate(Base):
    __tablename__ = "package_updates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tracking_number = Column(String, index=True)
    status = Column(String)
    location = Column(String)
    latitude = Column(Float, nullable=True)   # <-- dynamic update
    longitude = Column(Float, nullable=True)  # <-- dynamic update
    note = Column(String)
    updated_at = Column(DateTime(timezone=True))

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    support_email = Column(String, nullable=False)
    support_phone = Column(String, nullable=False)


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_name = Column(String, nullable=True)
    sender_email = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, default="new")
    created_at = Column(DateTime(timezone=True))


class ShipmentReceipt(Base):
    __tablename__ = "shipment_receipts"

    id = Column(Integer, primary_key=True, index=True)

    package_id = Column(
        Integer,
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True   # 🔒 one receipt per package
    )

    payment_type = Column(String, nullable=False)     # cash, transfer, card
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    payment_status = Column(String, default="paid")

    issued_at = Column(DateTime(timezone=True), server_default=func.now()) 

