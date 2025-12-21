import pytest

from src.backend.bff_layer import BFFRouter
from src.core.auth import AuthContext, Role, Token, User


def _make_context(*roles: Role) -> AuthContext:
    user = User(
        id="u1",
        username="user",
        email="u1@example.com",
        password_hash="x",
        roles=list(roles),
    )
    token = Token(access_token="t")
    return AuthContext(user=user, token=token, permissions=set())


@pytest.mark.asyncio
async def test_handle_request_rejects_extra_fields() -> None:
    router = BFFRouter()

    @router.route(
        "/admin/demo",
        schema={"context": AuthContext, "value": int},
        required_roles=(Role.ADMIN,),
    )
    async def handler(context: AuthContext, value: int) -> dict:
        return {"ok": True, "value": value}

    with pytest.raises(ValueError):
        await router.handle_request(
            "/admin/demo",
            {"context": _make_context(Role.ADMIN), "value": 1, "extra": "x"},
        )


@pytest.mark.asyncio
async def test_handle_request_requires_auth_context_for_protected_route() -> None:
    router = BFFRouter()

    @router.route(
        "/admin/demo",
        schema={"context": AuthContext, "value": int},
        required_roles=(Role.ADMIN,),
    )
    async def handler(context: AuthContext, value: int) -> dict:
        return {"ok": True, "value": value}

    with pytest.raises(PermissionError):
        await router.handle_request("/admin/demo", {"context": None, "value": 1})


@pytest.mark.asyncio
async def test_handle_request_accepts_valid_payload() -> None:
    router = BFFRouter()

    @router.route(
        "/admin/demo",
        schema={"context": AuthContext, "value": int},
        required_roles=(Role.ADMIN,),
    )
    async def handler(context: AuthContext, value: int) -> dict:
        return {"ok": True, "value": value}

    result = await router.handle_request(
        "/admin/demo", {"context": _make_context(Role.ADMIN), "value": 2}
    )
    assert result == {"ok": True, "value": 2}

