# Task Scheduler Validation Rules

## Overview
This document outlines the validation rules for the task scheduler system. These rules ensure data integrity, security, and proper functionality of the task scheduling system.

## Core Validation Rules

### Task Name
- **Required**: Yes
- **Uniqueness**: Must be unique across all tasks
- **Length**: 3-50 characters
- **Pattern**: `^[a-zA-Z0-9][a-zA-Z0-9\s_-]{1,48}[a-zA-Z0-9]$`
- **Rules**:
  - Must start and end with alphanumeric character
  - Can contain letters, numbers, spaces, hyphens, underscores
  - No leading/trailing whitespace
  - Cannot be empty or only whitespace

### Task Type
- **Required**: Yes
- **Allowed Values**: ["scheduled", "adhoc"]
- **Immutable**: Cannot be changed after creation
- **Rules**:
  - Must be specified during creation
  - Determines which additional fields are required

### Schedule (Scheduled Tasks)
- **Required**: Yes (for scheduled tasks only)
- **Format**: Cron expression (5 components)
- **Pattern**: `^(\*|([0-9]|[1-5][0-9])\s(\*|([0-9]|1[0-9]|2[0-3]))\s(\*|([1-9]|[12][0-9]|3[01]))\s(\*|([1-9]|1[0-2]))\s(\*|([0-6])))$`
- **Components**:
  - Minute: 0-59 or *
  - Hour: 0-23 or *
  - Day: 1-31 or *
  - Month: 1-12 or *
  - Weekday: 0-6 or * (0=Sunday)
- **Rules**:
  - Must be a valid cron expression
  - Cannot schedule more frequently than once per minute
  - All components must be present
  - Ranges and values must be valid for each component
  - Special characters allowed: *, -, /

### Token (Ad-hoc Tasks)
- **Required**: Yes (for ad-hoc tasks only)
- **Uniqueness**: Must be unique across all ad-hoc tasks
- **Length**: 8-32 characters
- **Pattern**: `^[a-zA-Z0-9][a-zA-Z0-9_-]{6,30}[a-zA-Z0-9]$`
- **Rules**:
  - Must contain at least one uppercase letter
  - Must contain at least one lowercase letter
  - Must contain at least one number
  - Only hyphens and underscores allowed as special characters
  - Must start and end with alphanumeric character

### Prompts
#### System Prompt
- **Required**: No
- **Length**: 0-2000 characters
- **Rules**:
  - If provided, cannot be only whitespace
  - Must be valid string if provided

#### User Prompt
- **Required**: Yes
- **Length**: 10-2000 characters
- **Rules**:
  - Cannot be empty or only whitespace
  - Must contain meaningful content

### Task State
- **Required**: Yes
- **Allowed Values**: ["idle", "running", "disabled", "error"]
- **Default**: "idle"
- **Valid Transitions**:
  - idle → running, disabled
  - running → idle, error
  - disabled → idle
  - error → idle, disabled
- **Rules**:
  - Must be one of allowed values
  - Can only transition according to valid transitions
  - Cannot manually set to "running" state

### Attachments
- **Required**: No
- **Rules Per Attachment**:
  - Must exist in workspace
  - Must be readable
  - Size limit: 10MB per file
  - Must have allowed file extension
- **Overall Rules**:
  - Maximum 10 attachments
  - Total size limit: 50MB
  - All paths must be absolute within container

### UUID (for updates)
- **Required**: Yes (for updates only)
- **Format**: UUID v4
- **Pattern**: `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`
- **Rules**:
  - Must be valid UUID v4 format
  - Must exist in database for updates

## Error Handling

### Display Rules
1. **Field-Level Errors**:
   - Show directly below invalid field
   - Clear when field value changes
   - Use error state styling on invalid field

2. **Form-Level Errors**:
   - Show at top of form
   - Clear when form is reset or submitted successfully
   - Use toast notifications for submission errors

3. **Error Messages**:
   - Must be clear and actionable
   - Should indicate how to fix the error
   - Should be user-friendly

## Validation Process

1. **Client-Side Validation**:
   - Validate on form submission
   - Validate on field blur for immediate feedback
   - Prevent submission if validation fails
   - Show all relevant errors at once

2. **Server-Side Validation**:
   - Validate all rules again on server
   - Return specific error messages
   - Maintain data integrity
   - Prevent invalid state transitions

## Implementation Notes

1. **Performance Considerations**:
   - Validate on blur for better UX
   - Debounce validation for fields like name uniqueness
   - Cache validation results where appropriate

2. **Security Considerations**:
   - Sanitize all inputs
   - Validate file paths carefully
   - Prevent command injection via inputs
   - Validate state transitions server-side

3. **UX Considerations**:
   - Show validation errors immediately
   - Clear errors when fixed
   - Provide helpful error messages
   - Guide users to valid inputs
