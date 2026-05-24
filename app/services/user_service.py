from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserRead

settings = get_settings()

_INVALID_CREDENTIALS_MESSAGE = "Invalid email or password"
_REGISTRATION_FAILED_MESSAGE = "Unable to complete registration"


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = UserRepository(session)

    async def register(self, data: UserCreate) -> UserRead:
        if await self._repository.email_exists(data.email):
            # Mensaje genérico: no revelar si el email ya está registrado
            raise ConflictError(_REGISTRATION_FAILED_MESSAGE)

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.ATTENDEE,
            is_active=True,
        )
        created = await self._repository.add(user)
        return UserRead.model_validate(created)

    async def authenticate(self, credentials: UserLogin) -> TokenResponse:
        user = await self._repository.get_by_email(credentials.email)
        if user is None or not verify_password(credentials.password, user.hashed_password):
            raise UnauthorizedError(_INVALID_CREDENTIALS_MESSAGE)

        if not user.is_active:
            # Mismo mensaje que credenciales inválidas para evitar enumeración
            raise UnauthorizedError(_INVALID_CREDENTIALS_MESSAGE)

        token = create_access_token(
            user.id,
            extra_claims={"role": user.role.value},
        )
        expires_in = settings.access_token_expire_minutes * 60
        return TokenResponse(access_token=token, expires_in=expires_in)

    async def get_current_user(self, user_id: UUID) -> UserRead:
        user = await self._repository.get_active_by_id(user_id)
        if user is None:
            raise UnauthorizedError("Unauthorized")
        return UserRead.model_validate(user)
