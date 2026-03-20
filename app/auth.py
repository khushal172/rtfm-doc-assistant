import httpx
from jose import jwt
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.logging_config import logger

security = HTTPBearer()

# Cache for JWKS to avoid frequent network calls
_jwks_cache = None

async def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            # Clerk JWKS endpoint: https://[your-instance-url]/.well-known/jwks.json
            jwks_url = f"{settings.clerk_instance_url}/.well-known/jwks.json"
            logger.info(f"Fetching JWKS from {jwks_url}")
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifies the Clerk JWT token and returns the user ID."""
    token = credentials.credentials
    try:
        jwks = await get_jwks()
        
        # In a production environment, we should verify the 'aud' and 'iss'
        # For simplicity in this demo, we'll verify the signature using the JWKS
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if rsa_key:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=None, # In production, set to your Clerk Frontend API URL
                options={"verify_aud": False}
            )
            # Clerk user_id is in the 'sub' claim
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: missing subject")
            return user_id
            
    except Exception as e:
        logger.error(f"JWT Verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {str(e)}")

    raise HTTPException(status_code=401, detail="Unable to verify authentication")
