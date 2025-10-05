from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

# Raw Plotly JSON structure - accepts any valid Plotly JSON
class PlotlyFigure(BaseModel):
    """Complete Plotly figure - accepts exact Plotly JSON format"""
    data: List[Dict[str, Any]] = Field(..., description="List of Plotly traces")
    layout: Optional[Dict[str, Any]] = Field(None, description="Plotly layout configuration")
    
    model_config = ConfigDict(
        extra="allow",  # Allow any additional Plotly properties
        validate_assignment=True
    )

# Main data models for Plotly charts

class PlotlyDataCreate(BaseModel):
    """Model for creating new Plotly charts - accepts raw Plotly JSON exactly as you provided"""
    title: Optional[str] = Field(None, max_length=200, description="Chart title")
    description: Optional[str] = Field(None, max_length=1000, description="Chart description")
    chart_type: Optional[str] = Field("line", max_length=50, description="Type of chart")
    # Accept your exact Plotly JSON structure: {"data": [...], "layout": {...}}
    data: List[Dict[str, Any]] = Field(
        ..., 
        max_length=100,  # Max 100 traces
        description="Plotly traces array - your exact format"
    )
    layout: Optional[Dict[str, Any]] = Field(None, description="Plotly layout object - your exact format")
    
    model_config = ConfigDict(
        extra="allow",  # Allow additional Plotly properties for flexibility
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    @field_validator('title', 'description')
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Basic XSS prevention - strip dangerous characters
            dangerous_chars = ['<', '>', '"', "'", '&']
            for char in dangerous_chars:
                if char in v:
                    raise ValueError(f"Invalid character '{char}' in text field")
        return v
    
    @field_validator('data')
    @classmethod
    def validate_data_size(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Check total size of data (prevent memory exhaustion)
        import json
        data_size = len(json.dumps(v))
        if data_size > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError("Data payload too large (max 10MB)")
        return v

class PlotlyDataUpdate(BaseModel):
    """Model for updating Plotly charts"""
    title: Optional[str] = None
    description: Optional[str] = None
    chart_type: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    layout: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )

class PlotlyDataInDB(BaseModel):
    """Model for Plotly data as stored in database"""
    item_id: int = Field(..., description="Unique identifier for the chart")
    title: Optional[str] = Field(None, description="Chart title")
    description: Optional[str] = Field(None, description="Chart description")
    chart_type: Optional[str] = Field("line", description="Type of chart")
    data: List[Dict[str, Any]] = Field(..., description="Plotly traces array")
    layout: Optional[Dict[str, Any]] = Field(None, description="Plotly layout object")
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="allow"
    )

class PlotlyDataResponse(BaseModel):
    """Model for API responses"""
    item_id: int = Field(..., description="Unique identifier for the chart")
    title: Optional[str] = Field(None, description="Chart title")
    description: Optional[str] = Field(None, description="Chart description")
    chart_type: Optional[str] = Field("line", description="Type of chart")
    data: List[Dict[str, Any]] = Field(..., description="Plotly traces array")
    layout: Optional[Dict[str, Any]] = Field(None, description="Plotly layout object")
    id: str = Field(..., description="Database document ID")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        extra="allow",
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

# Simplified models for basic data operations
class SimpleDataBase(BaseModel):
    """Simplified base model for generic data storage"""
    item_id: int = Field(..., description="Unique identifier for the data item")
    data: Dict[str, Any] = Field(..., description="Flexible data object")
    title: Optional[str] = Field(None, description="Optional title for the data")
    description: Optional[str] = Field(None, description="Optional description")
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )

class SimpleDataCreate(BaseModel):
    """Model for creating simple data entries"""
    data: Dict[str, Any] = Field(..., description="Flexible data object")
    title: Optional[str] = Field(None, description="Optional title for the data")
    description: Optional[str] = Field(None, description="Optional description")
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )

class SimpleDataUpdate(BaseModel):
    """Model for updating simple data entries"""
    data: Optional[Dict[str, Any]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )

class SimpleDataInDB(SimpleDataBase):
    """Model for simple data as stored in database"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

class SimpleDataResponse(SimpleDataBase):
    """Model for simple data API responses"""
    id: str = Field(..., description="Database document ID")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True
    )

# Standard response models
class ErrorResponse(BaseModel):
    """Standard error response model"""
    detail: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SuccessResponse(BaseModel):
    """Standard success response model"""
    message: str = Field(..., description="Success message")
    item_id: Optional[int] = Field(None, description="Related item ID")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional response data")