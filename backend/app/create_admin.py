from getpass import getpass

from pydantic import ValidationError

from app.core.security import hash_password
from app.db.database import Base, SessionLocal, engine, ensure_schema
from app.models.models import User
from app.schemas.user import UserCreate


def main():
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == "admin").first():
            raise SystemExit("An administrator already exists.")

        try:
            data = UserCreate(
                email=input("Admin email: ").strip(),
                full_name=input("Admin full name: ").strip(),
                password=getpass("Admin password: "),
            )
        except ValidationError as exc:
            raise SystemExit(str(exc)) from exc

        email = str(data.email).lower()
        if db.query(User).filter(User.email == email).first():
            raise SystemExit("That email already belongs to an account.")

        admin = User(
            email=email,
            full_name=data.full_name.strip(),
            hashed_password=hash_password(data.password),
            role="admin",
            preferred_language=data.preferred_language,
        )
        db.add(admin)
        db.commit()
        print(f"Administrator account created for {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
