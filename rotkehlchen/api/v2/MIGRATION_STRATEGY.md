# Flask to FastAPI Migration Strategy

## Overview
This document outlines the strategy for migrating Rotki from Flask to FastAPI while addressing the architectural issues identified in the codebase.

## Key Architectural Improvements

### 1. Eliminating God Objects
The monolithic `RestAPI` class (5700+ lines with 268 methods) has been broken down into focused service classes:

- **AuthService**: Authentication and API key management
- **DatabaseService**: Database operations using SQLModel
- **AssetsService**: Asset management and pricing
- **BalancesService**: Balance queries and manual tracking
- **BlockchainService**: Blockchain account and transaction management
- **ExchangeService**: Exchange connections and data
- **HistoryService**: Transaction history and events
- **StatisticsService**: Portfolio analytics

### 2. Proper Layer Separation
The new architecture follows a clean separation of concerns:

```
┌─────────────────┐
│   FastAPI       │  ← API Layer (Routers)
│   Routers       │     - Request/Response handling
│                 │     - Input validation with Pydantic
└────────┬────────┘
         │
┌────────▼────────┐
│   Services      │  ← Business Logic Layer
│                 │     - Core business logic
│                 │     - Data transformation
└────────┬────────┘
         │
┌────────▼────────┐
│   SQLModel      │  ← Data Access Layer
│   Models        │     - Database operations
│                 │     - ORM mappings
└─────────────────┘
```

### 3. Stateless Validation
Unlike the current Marshmallow schemas that perform I/O operations, the new Pydantic models are purely for validation:

- No database queries in validators
- No network calls (e.g., ENS lookups) during validation
- All I/O operations moved to service layer

### 4. Modern Python Features
- Type hints throughout for better IDE support
- Async/await for better performance
- Dependency injection with FastAPI's `Depends`
- Pydantic v2 for faster validation

## Migration Plan

### Phase 1: Parallel Development (Current)
1. ✅ Create FastAPI app structure under `/api/v2`
2. ✅ Implement service layer for business logic
3. ✅ Create routers for main endpoints
4. ✅ Use SQLModel with existing database

### Phase 2: Feature Parity
1. Complete all endpoint migrations
2. Implement middleware (CORS, authentication, etc.)
3. Add WebSocket support for real-time updates
4. Comprehensive testing

### Phase 3: Gradual Rollout
1. Run both Flask and FastAPI in parallel
2. Route new features to FastAPI
3. Gradually migrate existing features
4. Monitor performance and stability

### Phase 4: Complete Migration
1. Remove Flask dependencies
2. Clean up old code
3. Update documentation
4. Performance optimization

## API Compatibility

The new API maintains backward compatibility where possible:
- Same endpoint paths under `/api/v2` prefix
- Similar request/response structures
- Gradual deprecation of v1 endpoints

## Benefits of Migration

1. **Performance**: FastAPI is significantly faster than Flask
2. **Developer Experience**: Auto-generated OpenAPI docs, better type hints
3. **Maintainability**: Smaller, focused modules instead of god objects
4. **Testing**: Easier to unit test individual services
5. **Modern Stack**: Async support, WebSockets, Pydantic validation

## Next Steps

1. Complete remaining routers (reports, accounting, etc.)
2. Implement authentication middleware
3. Add comprehensive tests
4. Create migration scripts for database changes
5. Set up CI/CD for the new API