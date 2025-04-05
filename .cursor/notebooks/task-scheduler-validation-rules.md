# Task Scheduler Validation Rules

## Overview
This document outlines the validation rules for the task scheduler system based on actual code examination. These rules ensure data integrity, security, and proper functionality of the task scheduling system.

## Core Validation Rules (Implemented in Code)

### Task Name
- **Required**: Yes (Enforced in `scheduler_task_create.py` and `scheduler_task_update.py`)
- **Uniqueness**: Must be unique across all tasks (Checked in `TaskScheduler.add_task`)
- **Rules**:
  - Cannot be empty or only whitespace
  - Frontend form validation present
  - Backend validation in API handlers

### Task Type
- **Required**: Yes (Enforced in task models)
- **Allowed Values**: ["scheduled", "adhoc", "planned"]
- **Immutable**: Cannot be changed after creation (Enforced in UI and API)
- **Rules**:
  - Must be specified during creation
  - Determines which additional fields are required
  - Type-specific validation in API handlers

### Schedule (Scheduled Tasks)
- **Required**: Yes (for scheduled tasks only)
- **Components** (Enforced in `TaskSchedule` model):
  - Minute: 0-59 or *
  - Hour: 0-23 or *
  - Day: 1-31 or *
  - Month: 1-12 or *
  - Weekday: 0-6 or * (0=Sunday)
- **Rules**:
  - Must be a valid cron expression
  - All components must be present
  - Timezone handling through `Localization` class

### Token (Ad-hoc Tasks)
- **Required**: Yes (for ad-hoc tasks only)
- **Uniqueness**: Must be unique across all ad-hoc tasks
- **Rules**:
  - Generated automatically if not provided
  - Must be unique
  - Frontend provides generation button

### Task State
- **Required**: Yes
- **Allowed Values**: ["idle", "running", "disabled", "error"] (Defined in `TaskState` enum)
- **Default**: "idle"
- **Valid Transitions** (Enforced in code):
  - idle → running, disabled
  - running → idle, error
  - disabled → idle
  - error → idle, disabled
- **Rules**:
  - Must be one of allowed values
  - State transitions validated in `TaskScheduler`
  - Cannot manually set to "running" state

### Attachments
- **Required**: No
- **Rules Per Attachment**:
  - Path validation in container context
  - URL validation for web resources
  - Basic path existence check
- **Overall Rules**:
  - Stored as string array
  - Basic validation in place

## Error Handling (Implemented)

### Display Rules
1. **Field-Level Errors**:
   - Form validation in place
   - Basic error state styling
   - Error message display

2. **Form-Level Errors**:
   - Basic form validation
   - Error state handling
   - Toast notifications for errors

3. **Error Messages**:
   - Basic error messaging
   - API error propagation
   - UI error display

## Validation Process (Current Implementation)

1. **Client-Side Validation**:
   - Basic form validation
   - Type-specific field validation
   - State transition validation

2. **Server-Side Validation**:
   - Model validation through Pydantic
   - State transition validation
   - Atomic updates with validation

## Implementation Notes

1. **Performance Considerations**:
   - Basic validation on blur
   - Simple state checks
   - Atomic updates for state changes

2. **Security Considerations**:
   - Basic input sanitization
   - Path validation in container context
   - State transition validation

3. **UX Considerations**:
   - Immediate validation feedback
   - Error state display
   - Basic guidance for inputs

## Needed Improvements

### Validation Enhancements
1. **Schedule Validation**:
   - Add visual schedule builder
   - Enhance cron expression validation
   - Add schedule preview

2. **Attachment Validation**:
   - Enhance file path validation
   - Add file browser integration
   - Improve URL validation

3. **State Validation**:
   - Add transition history
   - Enhance error reporting
   - Add state change notifications

### UI Enhancements
1. **Form Validation**:
   - Add real-time validation
   - Enhance error messages
   - Add validation visualization

2. **Error Handling**:
   - Improve error message clarity
   - Add error recovery suggestions
   - Enhance error state display

This document will be updated as validation rules are enhanced.
