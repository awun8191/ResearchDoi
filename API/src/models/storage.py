from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """
    Returned after a successful file upload to Firebase Storage.
    document_url is a non-expiring Firebase download token URL of the form:
      https://firebasestorage.googleapis.com/v0/b/{bucket}/o/{encoded_path}?alt=media&token={uuid}
    """

    storage_path: str = Field(..., description="Firebase Storage path: users/{uid}/projects/{pid}/{filename}")
    document_url: str = Field(..., description="Non-expiring Firebase download token URL")
    filename: str
    size_bytes: int


class StorageUrlResponse(BaseModel):
    document_url: str = Field(..., description="Non-expiring Firebase download token URL")
    storage_path: str
