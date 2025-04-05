# Datetime Handling in API

## JSON Serialization/Deserialization

### Problem
JSON doesn't natively support datetime objects, which causes serialization errors when returning datetime objects in API responses.

### Solution
1. **Serialization (Python → JSON)**:
   - Convert datetime objects to ISO format strings using `datetime_obj.isoformat()`
   - This pattern is implemented in all task-related API endpoints

2. **Deserialization (JSON → Python)**:
   - When receiving data from the UI, check for string fields that are likely datetime values (ending with `_at`)
   - Use `datetime.fromisoformat()` to convert ISO strings back to datetime objects
   - Implemented in update and create handlers

### Implementation Notes
- Added date serialization in all scheduler API handlers that return task objects
- Added date deserialization in handlers that receive task data (create, update)
- Used consistent pattern to identify datetime fields (naming convention with `_at` suffix)
- Used try/except blocks to handle invalid format gracefully

### AsyncIO Patterns
- The `add_task` method in `SchedulerTaskList` is async and requires awaiting
- Fixed linter errors in API handlers that weren't awaiting this async call

### Lessons
1. When working with APIs that handle datetime objects:
   - Always handle serialization of datetime objects when sending data to the frontend
   - Always handle deserialization of datetime strings when receiving data from the frontend
   - Use consistent datetime string formats (ISO 8601 is the standard for JSON)

2. When fixing linter errors:
   - Some "not iterable" errors might be false positives - check the actual code before making changes
   - Always ensure async calls are properly awaited, especially when using third-party libraries
