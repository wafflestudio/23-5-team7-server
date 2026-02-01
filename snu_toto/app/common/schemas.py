from pydantic import BaseModel

class PaginationInfo(BaseModel):
    total: int
    current_page: int
    limit: int
    total_pages: int