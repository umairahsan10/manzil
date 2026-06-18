"""Image proxy for fetching photos from Pexels without exposing the API key."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/images", tags=["images"])

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# Small curated fallback image map in case Pexels is unavailable or returns nothing.
# These are direct Pexels photo URLs that can be hotlinked.
FALLBACK_IMAGES: Dict[str, str] = {
    "hunza": "https://images.pexels.com/photos/2923592/pexels-photo-2923592.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "skardu": "https://images.pexels.com/photos/3293148/pexels-photo-3293148.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "naran": "https://images.pexels.com/photos/3225529/pexels-photo-3225529.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "fairy-meadows": "https://images.pexels.com/photos/3408744/pexels-photo-3408744.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "murree": "https://images.pexels.com/photos/1770809/pexels-photo-1770809.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "gilgit": "https://images.pexels.com/photos/2835436/pexels-photo-2835436.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "passu": "https://images.pexels.com/photos/624015/pexels-photo-624015.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "attabad": "https://images.pexels.com/photos/1485894/pexels-photo-1485894.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "khaplu": "https://images.pexels.com/photos/2835436/pexels-photo-2835436.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "swat": "https://images.pexels.com/photos/1770809/pexels-photo-1770809.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "shogran": "https://images.pexels.com/photos/3225529/pexels-photo-3225529.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "neelum": "https://images.pexels.com/photos/1485894/pexels-photo-1485894.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "deosai": "https://images.pexels.com/photos/1624496/pexels-photo-1624496.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "chitral": "https://images.pexels.com/photos/2923592/pexels-photo-2923592.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
    "pakistan mountains": "https://images.pexels.com/photos/1624496/pexels-photo-1624496.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
}


class ImageResult(BaseModel):
    url: str
    photographer: str
    photographer_url: Optional[str] = None
    source: str = "pexels"


class ImageSearchResponse(BaseModel):
    query: str
    results: List[ImageResult]


@lru_cache(maxsize=128)
def _fetch_pexels(query: str, per_page: int) -> List[ImageResult]:
    """Fetch images from Pexels with a small in-memory cache."""
    if not PEXELS_API_KEY:
        return []

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                PEXELS_SEARCH_URL,
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": per_page, "orientation": "landscape"},
            )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
            photos = data.get("photos", [])
            return [
                ImageResult(
                    url=photo["src"]["landscape"]
                    if "src" in photo and "landscape" in photo["src"]
                    else photo["src"]["large"],
                    photographer=photo.get("photographer", "Unknown"),
                    photographer_url=photo.get("photographer_url"),
                )
                for photo in photos
                if "src" in photo
            ]
    except Exception:
        return []


def _fallback_image(query: str) -> Optional[ImageResult]:
    """Return a curated fallback image for known keywords."""
    normalized = query.lower().strip()
    for key in FALLBACK_IMAGES:
        if key in normalized:
            return ImageResult(
                url=FALLBACK_IMAGES[key],
                photographer="Pexels",
                photographer_url="https://www.pexels.com",
            )
    return None


@router.get("/search", response_model=ImageSearchResponse)
def search_images(
    query: str = Query(..., min_length=1, description="Search keyword"),
    per_page: int = Query(1, ge=1, le=15),
):
    """Search Pexels for images matching the query."""
    results = _fetch_pexels(query, per_page)

    if not results:
        fallback = _fallback_image(query)
        if fallback:
            results = [fallback]

    if not results:
        raise HTTPException(status_code=404, detail=f"No images found for '{query}'")

    return ImageSearchResponse(query=query, results=results)
