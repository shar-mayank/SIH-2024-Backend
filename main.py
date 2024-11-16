from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, String, Date
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date
import bcrypt
import logging
from logging.handlers import RotatingFileHandler
import os

# Set up logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, "payment_api.log")

logger = logging.getLogger("payment_api")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Database setup
SQLALCHEMY_DATABASE_URL = "postgresql://sharmayank:12345678@localhost/sih_backend"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class CardPayment(Base):
    __tablename__ = "card_payments"
    name = Column(String, nullable=False)
    card_number = Column(String, primary_key=True, index=True)
    expires = Column(Date, nullable=False)
    cvv = Column(String, nullable=False)

class ApplePayPayment(Base):
    __tablename__ = "apple_pay_payments"
    email = Column(String, primary_key=True, index=True)
    phone_number = Column(String)
    password_hash = Column(String, nullable=False)

class PayPalPayment(Base):
    __tablename__ = "paypal_payments"
    email = Column(String, primary_key=True, index=True)
    password_hash = Column(String, nullable=False)
    phone_number = Column(String)

Base.metadata.create_all(bind=engine)

# Pydantic models for request validation
class CardPaymentRequest(BaseModel):
    name: str
    card_number: str
    expires_month: int
    expires_year: int
    cvv: str

class ApplePayPaymentRequest(BaseModel):
    email: EmailStr
    phone_number: str = None
    password: str

class PayPalPaymentRequest(BaseModel):
    email: EmailStr
    password: str
    phone_number: str = None

# FastAPI app
app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to hash passwords
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# API endpoints
@app.post("/payment/card")
async def card_payment(payment: CardPaymentRequest, db: SessionLocal = Depends(get_db)):
    try:
        hashed_card_number = hash_password(payment.card_number)
        hashed_cvv = hash_password(payment.cvv)
        expires_date = date(payment.expires_year, payment.expires_month, 1)

        db_payment = CardPayment(
            name=payment.name,
            card_number=hashed_card_number,
            expires=expires_date,
            cvv=hashed_cvv
        )
        db.add(db_payment)
        db.commit()
        logger.info(f"Card payment processed for {payment.name}")
        return {"message": "Card payment processed successfully"}
    except Exception as e:
        logger.error(f"Error processing card payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing card payment")

@app.post("/payment/applepay")
async def apple_pay_payment(payment: ApplePayPaymentRequest, db: SessionLocal = Depends(get_db)):
    try:
        hashed_password = hash_password(payment.password)
        db_payment = ApplePayPayment(
            email=payment.email,
            phone_number=payment.phone_number,
            password_hash=hashed_password
        )
        db.add(db_payment)
        db.commit()
        logger.info(f"Apple Pay payment processed for {payment.email}")
        return {"message": "Apple Pay payment processed successfully"}
    except Exception as e:
        logger.error(f"Error processing Apple Pay payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing Apple Pay payment")

@app.post("/payment/paypal")
async def paypal_payment(payment: PayPalPaymentRequest, db: SessionLocal = Depends(get_db)):
    try:
        hashed_password = hash_password(payment.password)
        db_payment = PayPalPayment(
            email=payment.email,
            password_hash=hashed_password,
            phone_number=payment.phone_number
        )
        db.add(db_payment)
        db.commit()
        logger.info(f"PayPal payment processed for {payment.email}")
        return {"message": "PayPal payment processed successfully"}
    except Exception as e:
        logger.error(f"Error processing PayPal payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing PayPal payment")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)