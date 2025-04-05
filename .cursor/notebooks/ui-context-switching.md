# UI Context Switching Insights

## The Problem
The application had an issue with context switching between chats and tasks in the sidebar UI. When switching away from an active chat/task and then back, the content would disappear and realtime updates would stop working, even though the backend context still existed and was functioning.

## Root Cause Analysis
The root cause was identified in how the frontend handled context switching:

1. When switching contexts, the frontend would reset tracking variables (`lastLogGuid` and `lastLogVersion`)
2. It would also clear the chat history element's innerHTML
3. In `selectChat`, an additional `resetChat(true)` call was being made which caused even more state clearing

This aggressive clearing meant the frontend lost track of which messages it had already received, making it unable to properly handle context switching.

## Key Insights

### UI-Backend State Coupling
- The UI relies on two tracking variables (`lastLogGuid` and `lastLogVersion`) to maintain synchronization with the backend
- These variables act as "sync points" that tell the frontend which messages it has already processed
- When these get reset, the UI loses its "memory" of past chat state

### Two Approaches to State Management
We explored two fundamentally different approaches:

1. **Frontend caching approach**:
   - Use `sessionStorage` to cache chat content and restore it when switching contexts
   - Maintain tracking variables across context switches
   - Pros: Can work without backend requests
   - Cons: Can get out of sync and show stale data

2. **Backend source-of-truth approach**:
   - Always clear UI state when switching contexts
   - Let polling from backend restore the correct state
   - Pros: Always shows accurate data
   - Cons: Brief visual flash during context switch

The second approach was ultimately better for this application since:
- It's primarily a local app where network latency is negligible
- Real-time accuracy is more important than offline caching
- It's simpler and less error-prone

### Debugging Techniques
- Following the full lifecycle of context switching through UI events → API calls → backend code
- Identifying where state was being inappropriately reset
- Testing different contexts to see patterns in behavior

## Applicable Design Patterns
- **Source of Truth Pattern**: Relying on backend as the definitive source of state
- **Event Tracking**: Using unique identifiers (GUIDs) to track state changes across systems
- **Versioning**: Using version numbers to efficiently sync only changed data

## Future Considerations
For any UI/frontend changes involving state management:
1. Be careful with clearing state variables during navigation
2. Consider where the "source of truth" for state should live
3. Test thoroughly with multiple open contexts to verify correct behavior
4. When context switching, ensure no orphaned contexts are created
