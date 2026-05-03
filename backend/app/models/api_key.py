import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .model import Model


class APIKey(Base):
    """
    Platform-owned Groq API keys, one (or more) per model.
    Never exposed to users. Loaded by the backend at inference time.

    encrypted_key stores the AES-encrypted key value.
    Decryption happens in-memory at runtime using a master secret
    stored in environment variables — never logged, never returned in any response.

    NOTE: For v1, you can skip this table entirely and use .env vars per model.
    Migrate to this table when you need key rotation or multiple keys per model.
    """

    __tablename__ = "api_keys"

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    encrypted_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AES-encrypted Groq API key — decrypted in-memory at runtime only",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Set False to rotate a key without downtime",
    )

    # Relationship
    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="api_keys",
    )

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} model_id={self.model_id} active={self.is_active}>"