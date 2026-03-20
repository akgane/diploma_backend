from pydantic import BaseModel, Field, EmailStr

# region REQUESTS

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, example="John")
    email: EmailStr = Field(..., example="john@doe.com")
    password: str = Field(..., min_length=6, max_length=100, example="strongpassword")

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="john@doe.com")
    password: str = Field(..., example="strongpassword")

# endregion REQUESTS

# region RESPONSES

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    name: str
    email: str

# endregion RESPONSES