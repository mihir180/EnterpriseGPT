import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class Department(str, enum.Enum):
    """
    Drives two things in Phase 4:
      1. Document ACL — a document tagged with a department is only visible
         to users in that department (plus admins, plus explicit grants).
      2. Multi-agent routing — the router agent classifies a question into
         one of these, and the matching specialist agent answers it.

    GENERAL is the default for both: a user with no specific department,
    and documents with no department restriction (i.e. visible org-wide).
    """
    HR = "hr"
    LEGAL = "legal"
    TECHNICAL = "technical"
    GENERAL = "general"


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda x: [e.value for e in x]),
        default=UserRole.EMPLOYEE,
        nullable=False,
    )
    department: Mapped[Department] = mapped_column(
        Enum(Department, name="department", values_callable=lambda x: [e.value for e in x]),
        default=Department.GENERAL,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    documents = relationship("Document", back_populates="uploader")
    permissions = relationship(
        "DocumentPermission", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role}/{self.department})>"
