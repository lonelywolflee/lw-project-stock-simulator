"""인증 API — 세션 기반 로그인/로그아웃."""

from django.contrib.auth import authenticate, login, logout
from ninja import Router, Schema

router = Router()


class LoginSchema(Schema):
    username: str
    password: str


class UserSchema(Schema):
    id: int
    username: str
    is_staff: bool


class ErrorSchema(Schema):
    detail: str


@router.post("/login", response={200: UserSchema, 401: ErrorSchema})
def login_view(request, payload: LoginSchema):
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        return 401, {"detail": "아이디 또는 비밀번호가 올바르지 않습니다."}
    login(request, user)
    return {"id": user.id, "username": user.username, "is_staff": user.is_staff}


@router.post("/logout", response={200: dict})
def logout_view(request):
    logout(request)
    return {"detail": "ok"}


@router.get("/me", response={200: UserSchema, 401: ErrorSchema})
def me(request):
    if not request.user.is_authenticated:
        return 401, {"detail": "인증되지 않았습니다."}
    user = request.user
    return {"id": user.id, "username": user.username, "is_staff": user.is_staff}
