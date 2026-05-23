from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Admin(Base):
    """
    Platform administrator. Completely separate from User.
    Admins are created manually (seeded or via CLI) — there is no
    public registration endpoint for admins.
    """

    __tablename__ = "admins"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Admin id={self.id} email={self.email}>"
