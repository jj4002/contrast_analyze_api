import httpx
from fastapi import Header, HTTPException
from config import SUPABASE_URL, SUPABASE_SECRET_KEY, logger


async def get_current_user_id(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_SECRET_KEY},
            )
    except httpx.HTTPError as e:
        logger.error(f"Supabase auth check failed: {e}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user = res.json()
    return user["id"]
