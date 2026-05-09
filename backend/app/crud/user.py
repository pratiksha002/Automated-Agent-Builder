import uuid
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.security import hash_password


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Fetch a user by email address.
    Used during login to look up the user before verifying their password.
    Returns None if no user with that email exists.
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """
    Fetch a user by their UUID.
    Used by the get_current_user dependency after decoding the JWT.
    Returns None if the user doesn't exist or has been deleted.
    """
    return db.query(User).filter(User.id == user_id, User.is_active == True).first()


def create_user(db: Session, email: str, password: str, full_name: str) -> User:
    """
    Creates a new user.
    Hashes the password before storing — plain text never touches the DB.
    Raises no error if email is duplicate; caller is responsible for checking
    get_user_by_email first and returning a 400 if the email is already taken.
    """
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user