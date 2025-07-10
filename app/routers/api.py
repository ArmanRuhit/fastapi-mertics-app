"""API endpoints for CRUD operations with Prometheus metrics.

This module implements RESTful API endpoints for managing user data records
with proper error handling, input validation, and Prometheus metrics.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr, validator

from app.database import fetch, fetchrow, execute, execute_returning
from app.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    db_operations_total,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class DataItemCreate(BaseModel):
    """Schema for creating a new data item."""
    name: str = Field(..., max_length=100, example="John Doe")
    email: EmailStr = Field(..., example="user@example.com")
    message: Optional[str] = Field(None, max_length=500, example="Hello, World!")

    @validator('name')
    def name_must_contain_space(cls, v):
        if ' ' not in v.strip():
            raise ValueError('Name must contain at least one space')
        return v.title()


class DataItemResponse(DataItemCreate):
    """Schema for data item responses."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


@router.post(
    "/data",
    status_code=status.HTTP_201_CREATED,
    response_model=DataItemResponse,
    responses={
        201: {"description": "Item created successfully"},
        400: {"description": "Invalid input data"},
        500: {"description": "Failed to create item"}
    },
    summary="Create a new data item"
)
async def create_data(
    item: DataItemCreate,
    background_tasks: BackgroundTasks,
    request: Request
) -> DataItemResponse:
    """Create a new data item.
    
    Args:
        item: The data item to create
        background_tasks: FastAPI background tasks
        request: The incoming request
        
    Returns:
        DataItemResponse: The created data item
    """
    try:
        # Log the start time for metrics
        start_time = datetime.now()
        
        # Log the incoming request data
        logger.info(f"Creating new data item: {item.dict()}")
        
        # Insert the new item into the database
        query = """
            INSERT INTO user_data (name, email, message, created_at)
            VALUES ($1, $2, $3, NOW())
            RETURNING id, created_at, updated_at
        """
        
        try:
            result = await fetchrow(
                query,
                item.name,
                item.email,
                item.message
            )
            logger.info(f"Database insert result: {result}")
            
            if not result:
                error_msg = "No result returned from database insert"
                logger.error(error_msg)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg
                )
            
            # Create the response object
            response_data = {
                **item.dict(),
                "id": result["id"],
                "created_at": result["created_at"],
                "updated_at": result["updated_at"]
            }
            response = DataItemResponse(**response_data)
            
            # Calculate processing time for metrics
            process_time = (datetime.now() - start_time).total_seconds()
            
            # Add background task to log the request and update metrics
            background_tasks.add_task(
                log_request,
                request=request,
                response=Response(status_code=status.HTTP_201_CREATED),
                process_time=process_time
            )
            
            # Update database operation metrics
            db_operations_total.labels(
                operation="create",
                status="success"
            ).inc()
            
            logger.info(f"Successfully created data item: {response.dict()}")
            return response
            
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(db_error)}"
            )
        
    except HTTPException as http_exc:
        logger.error(f"HTTP Exception: {str(http_exc.detail)}", exc_info=True)
        db_operations_total.labels(
            operation="create",
            status="error"
        ).inc()
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating data item: {str(e)}", exc_info=True)
        db_operations_total.labels(
            operation="create",
            status="error"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create item: {str(e)}"
        )


def log_request(request: Request, response: Response, process_time: float):
    """Log request details and update metrics."""
    http_method = request.method
    endpoint = request.url.path
    status_code = response.status_code
    
    # Update metrics
    http_requests_total.labels(
        method=http_method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=http_method,
        endpoint=endpoint
    ).observe(process_time)
    
    # Log the request
    logger.info(
        f"{http_method} {endpoint} - {status_code} - {process_time:.3f}s"
    )


@router.delete(
    "/data/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Item deleted successfully"},
        404: {"description": "Item not found"},
        500: {"description": "Failed to delete item"}
    },
    summary="Delete a data item"
)
async def delete_data(item_id: int) -> Response:
    """Delete a data item by ID.
    
    Returns:
        Response: 204 No Content on success
    """
    try:
        result = await execute(
            "DELETE FROM user_data WHERE id = $1",
            item_id
        )
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # Return a proper 204 response with no content
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting data item {item_id}: {str(e)}")
        db_operations_total.labels(
            operation="delete", 
            status="error"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item"
        )
