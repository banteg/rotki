# Rotki2 - Architectural Rewrite

This package contains the new architectural rewrite of Rotkehlchen, separated from the original codebase for easier development and reference.

## Structure

- `api/v2/` - New FastAPI-based REST API implementation
- `db/models/` - SQLModel-based database models replacing raw SQL
- `db/migrations/` - Alembic-based database migrations
- `tasks/` - AnyIO-based asynchronous task management
- `utils/` - New utility modules including async networking
- `tests/` - Comprehensive test suite for v2 components

## Key Improvements

1. **Modern API Framework**: FastAPI replacing Flask for better performance and type safety
2. **ORM-based Database**: SQLModel replacing raw SQL for better maintainability
3. **Async Architecture**: AnyIO for true asynchronous operations
4. **Repository Pattern**: Clean separation of data access logic
5. **Service Layer**: Business logic separated from API endpoints
6. **Type Safety**: Full Pydantic models for request/response validation

## Development

The original Rotkehlchen code remains untouched in the `rotkehlchen` package, allowing easy reference while developing the new architecture.

All imports within rotki2 have been updated to use the new package structure.
