from jose import JWTError, jwt #json token generation
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer
from fastapi import HTTPException, Depends, Body, status
from sqlalchemy.orm import Session
from models.table_data import Person
from database import get_database


# Secret key for encoding and decoding JWT
token_secret = "03a0e04db6ee628b8ffb53fe4bc30e12d553f621ac7a083029bbe74e4def5620"
token_algorithm = "HS256"
token_expiry_minutes = 1440

# setup authentication scheme
oauth2_scheme = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=token_expiry_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, token_secret, algorithm=token_algorithm)


def get_users(token: str = Depends(oauth2_scheme), db: Session = Depends(get_database)):
    try:
        payload = jwt.decode(token.credentials, token_secret, algorithms=[token_algorithm])
        email: str = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        user = db.query(Person).filter(Person.email == email).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid/Expired token")


def admin_required(user: Person=Depends(get_users)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin access required")
    return user



  