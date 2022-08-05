"""
A simple REST API to serve as an example for the tests in this repository.
"""

import asyncio

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from random import random
import os

app = FastAPI()

# Endpoints will return a dummy response up to this ID number, and raise 404 error beyond it.
ID_LIMIT = max(0, int(os.environ.get("ID_LIMIT", "100")))

# Use to simulate actual work being done, e.g. DB query, a delay up to this value will be randomly introduced.
MAX_DELAY = max(0.0, float(os.environ.get("MAX_DELAY", "0")))

# Set so that the swagger / OpenAPI doc will be more precise.
EXPECTED_RESPONSES = {
    404: {"description": "Item was not found"},
    503: {"description": "Server overloaded"}
}


class ItemResponse(BaseModel):
    item_id: int


async def make_response(item_id: int) -> Dict[str, int]:
    """Shared response function, all the test endpoints are the same except their names."""
    if item_id > ID_LIMIT:
        raise HTTPException(status_code=404, detail=f"Item {item_id} was not found.")
    if MAX_DELAY:
        try:
            await asyncio.sleep(random() * MAX_DELAY)
        except asyncio.exceptions.CancelledError:
            raise HTTPException(status_code=503, detail="Server overloaded")
    return {"item_id": item_id}


@app.get(
    "/people/{item_id}",
    response_model=ItemResponse,
    responses=EXPECTED_RESPONSES,
)
async def people(item_id: int):
    return await make_response(item_id)


@app.get(
    "/planets/{item_id}",
    response_model=ItemResponse,
    responses=EXPECTED_RESPONSES,
)
async def planets(item_id: int):
    return await make_response(item_id)


@app.get(
    "/starships/{item_id}",
    response_model=ItemResponse,
    responses=EXPECTED_RESPONSES,
)
async def starships(item_id: int):
    return await make_response(item_id)
