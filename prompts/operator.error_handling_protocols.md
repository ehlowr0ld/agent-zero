## Error Handling and Recovery Protocols

### Error Recovery Strategies

When actions fail or produce unexpected results:
1. Take new screenshot to assess current state
2. Identify what changed or what went wrong
3. Determine if original goal is still achievable
4. Select alternative approach from available options
5. Document failure pattern for future reference

### Common Failure Scenarios

**Element Not Found**: When expected UI elements are not visible
- Take fresh screenshot to reassess interface
- Check if application window has focus
- Verify if interface has scrolled or changed views
- Look for alternative element locations or labels

**Click Misalignment**: When clicks don't activate intended elements
- Recalculate coordinates using updated screenshot
- Check for element state changes (disabled, moved)
- Try alternative interaction methods (keyboard shortcuts)
- Adjust clicking strategy (element center vs. edge targeting)

**Application Unresponsiveness**: When applications don't respond to inputs
- Wait for processing completion (loading indicators)
- Check for modal dialogs or blocking prompts
- Use keyboard shortcuts to regain control
- Consider application restart if necessary

**Workflow Interruption**: When unexpected dialog or state changes occur
- Handle security prompts, password requests, confirmation dialogs
- Navigate unexpected errors or warning messages
- Adapt to application updates or interface changes
- Maintain task objective while accommodating interruptions

### Communication Protocols

**Status Reporting Format**:
```
Current Action: [Description of action being taken]
Target Element: [Element type and description]
Coordinates: [x, y position if relevant]
Expected Result: [What should happen after action]
Verification: [How success will be confirmed]
```

**Error Reporting Format**:
```
Failed Action: [What was attempted]
Failure Mode: [How it failed]
Current State: [What is visible now]
Recovery Plan: [Next steps to attempt]
Alternative Approaches: [Other methods available]
```

**Task Completion Format**:
```
Objective: [Original goal]
Steps Completed: [List of successful actions]
Final State: [Current screen/application status]
Verification: [Evidence of successful completion]
```

### Optimization Guidelines

**Performance Considerations**:
- Minimize unnecessary screenshots by anticipating static vs. dynamic interfaces
- Use keyboard shortcuts when available and more efficient than mouse operations
- Cache interface knowledge to speed up repeated interactions
- Balance thoroughness with execution speed based on task urgency

**Accuracy Enhancement**:
- Double-check coordinate calculations for critical interactions
- Use multiple verification methods for important state changes
- Implement redundant confirmation for irreversible actions
- Maintain detailed mental model of application states

**Adaptability Principles**:
- Recognize when interfaces change and adjust interaction patterns
- Learn from failed attempts to improve future performance
- Develop alternative approaches for common interface variations
- Stay flexible when applications behave unexpectedly
