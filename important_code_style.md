# Code Style Guidelines

## Python Style
- Use Black formatter with line length 88
- Type hints for all function parameters and returns
- Docstrings for all public functions (Google style)
- Private methods start with underscore
- Use dataclasses for data structures

## JavaScript/TypeScript Style
- Use Prettier with 2-space indentation
- Prefer const over let, never use var
- Use arrow functions for callbacks
- Async/await over promises chains
- Interfaces for all API contracts

## Error Handling
- Always catch specific exceptions, not bare except
- Log errors with context
- Return meaningful error messages to users
- Use custom error classes for domain errors

## Testing Requirements
- Minimum 80% code coverage
- Unit tests for all business logic
- Integration tests for API endpoints
- Mock external dependencies
- Test both success and failure cases