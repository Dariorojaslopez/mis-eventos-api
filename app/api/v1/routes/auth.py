from fastapi import APIRouter, status

from app.api.v1.dependencies.auth import CurrentUser, UserServiceDep
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserRead

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar usuario",
    description="Crea una cuenta nueva. El rol por defecto es `attendee`.",
)
async def register(data: UserCreate, service: UserServiceDep) -> UserRead:
    return await service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description="Autentica credenciales y devuelve un JWT de acceso.",
)
async def login(credentials: UserLogin, service: UserServiceDep) -> TokenResponse:
    return await service.authenticate(credentials)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Usuario actual",
    description="Devuelve el perfil del usuario autenticado vía Bearer token.",
)
async def get_me(current_user: CurrentUser) -> UserRead:
    return current_user
