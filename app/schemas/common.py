from pydantic import BaseModel, Field


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    pages: int = Field(ge=0)

    @classmethod
    def build(cls, *, items: list[T], total: int, page: int, limit: int) -> "PaginatedResponse[T]":
        pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(items=items, total=total, page=page, limit=limit, pages=pages)
