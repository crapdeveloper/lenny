from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta

from database import get_db
from models import User
from esi_client import esi_security
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = [
    "esi-wallet.read_character_wallet.v1",
    "esi-markets.read_character_orders.v1",
    "esi-markets.structure_markets.v1"
]

@router.get("/login")
def login():
    """
    Redirects the user to the EVE Online SSO login page.
    """
    auth_url = esi_security.get_auth_uri(scopes=SCOPES, state="lenny_state")
    return RedirectResponse(auth_url)

@router.get("/callback")
async def callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """
    Handles the callback from EVE Online SSO.
    Exchanges the code for tokens and creates/updates the user in the DB.
    """
    try:
        # Exchange code for tokens
        tokens = esi_security.auth(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SSO Error: {str(e)}")

    # Verify the token to get character info
    api_info = esi_security.verify()
    
    character_id = api_info['sub'].split(':')[-1]
    character_name = api_info['name']
    
    # Check if user exists
    result = await db.execute(select(User).filter(User.character_id == int(character_id)))
    user = result.scalars().first()

    if not user:
        user = User(
            character_id=int(character_id),
            character_name=character_name,
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            token_expiry=datetime.utcnow() + timedelta(seconds=tokens['expires_in'])
        )
        db.add(user)
    else:
        user.access_token = tokens['access_token']
        user.refresh_token = tokens['refresh_token']
        user.token_expiry = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])
        user.character_name = character_name # Update name just in case
    
    await db.commit()
    await db.refresh(user)

    # In a real app, you would issue your own JWT here.
    # For now, we'll just redirect to the frontend with the character name
    # (Insecure for production, but good for MVP testing)
    return RedirectResponse(url=f"http://localhost:3000?character={character_name}&character_id={character_id}")
