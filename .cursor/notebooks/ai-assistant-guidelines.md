# Guidelines for Effective AI Assistance

## Core Principles for Better Collaboration

### Do:
1. **Listen to the user's technical suggestions first**
   - The user often has valuable context and intuition about their codebase
   - When they suggest checking backend data or looking in specific areas, prioritize those directions

2. **Start with the simplest possible explanation**
   - Bugs are usually caused by simple issues (e.g., property name mismatches, typos)
   - Verify data structures and API contracts before assuming complex styling/rendering issues

3. **Be methodical and systematic**
   - Start debugging with a clear hypothesis and test it
   - Use a step-by-step elimination process rather than trying several approaches simultaneously

4. **Acknowledge knowledge gaps**
   - If uncertain about the root cause, say so rather than guessing
   - Request necessary information instead of making assumptions

5. **Preserve existing conventions**
   - Study the codebase to understand patterns and naming conventions
   - Maintain consistency with the project's established patterns
   - Follow camelCase for localStorage keys and JavaScript identifiers
   - Use proper component prefixes for CSS classes

6. **ALWAYS maintain your scratchpad**
   - This is a MANDATORY REQUIREMENT, not optional
   - Update your scratchpad with ALL findings and changes as you work
   - Record decisions, approaches, and outcomes to maintain context
   - Refer to your scratchpad regularly to prevent repeating failed approaches
   - Use the scratchpad as a memory aid to compensate for context limitations
   - Always update the scratchpad BEFORE making significant changes to code
   - The scratchpad has 3 files: .cursor/notebooks/ai_assistant_scratchpad.md, .context.md and .warning-flags
   - You must maintain the scratchpad with its structure in these 3 files

7. **Transparently communicate potential regressions**
   - ALWAYS warn the user when a fix might temporarily break functionality
   - Clearly explain multi-step fixes that won't work until all steps are in place
   - Provide context for high-risk changes to core components
   - Set proper expectations about potential instability during complex fixes
   - Use phrases like "This might temporarily cause X before being fully fixed"
   - Be upfront about changes that might expose other underlying issues
   - Explain the complete plan so users can anticipate and plan around temporary issues
   - Give specific details about what might break and for how long

8. **Handle Alpine.js Store Properly**
   - Always initialize store during `alpine:init`
   - Check for store existence before access
   - Follow established property naming patterns
   - Use proper error handling for store operations

9. **VERIFY BEFORE SUGGESTING NEW CODE OR ENDPOINTS**
   - Before suggesting a new endpoint or component, ALWAYS verify it doesn't already exist
   - Check the actual API files to confirm endpoint names, not just guessing based on conventions
   - Search the codebase thoroughly to verify your understanding before making changes

10. **REUSE EXISTING CODE AND ABSTRACTIONS**
    - Always look for opportunities to reuse existing code rather than duplicating functionality
    - Create proper abstractions that can be shared between components when similar functionality is needed
    - Avoid copy-pasting large blocks of code between files

11. **VERIFY MODULE IMPORTS AND PATHS**
    - Always ensure module paths are correct before creating new imports
    - Check for proper __init__.py files in Python packages
    - Verify import paths work in the project's specific structure

12. **TEST CHANGES INCREMENTALLY**
    - Make small, targeted changes and verify they work before proceeding
    - Don't commit to large architectural changes without testing smaller components first

### Don't:
1. **Don't overcomplicate solutions**
   - Avoid excessive CSS overrides, !important flags, and complex browser-specific hacks
   - Simpler solutions are almost always better and less likely to cause new issues

2. **Don't waste time with premature optimizations**
   - Focus on fixing the core issue before worrying about edge cases
   - Avoid styling tweaks before ensuring the fundamental functionality works

3. **Don't ignore direct user guidance**
   - When the user suggests checking a specific area, do that first
   - Their domain knowledge is invaluable and should not be disregarded

4. **Don't make sweeping changes without validation**
   - Test small, targeted changes before implementing broad solutions
   - Avoid rewriting large code sections when a small fix might suffice

5. **Don't persevere with failed approaches**
   - Know when to abandon a path that isn't working
   - Pivoting to a new approach is better than persisting with a flawed one

6. **Don't rely solely on your memory without scratchpad reference**
   - Never assume you'll remember critical details between interactions
   - Not updating the scratchpad leads to repetition of errors and wasted time
   - Failing to maintain your scratchpad means failing the user

7. **Don't surprise the user with unexpected behavior**
   - Never implement complex fixes without warning about potential temporary regressions
   - Don't hide the risk of intermediate broken states during multi-step fixes
   - Don't assume the user will understand that things might get worse before they get better
   - Always be explicit about potential side effects of your changes
   - Don't proceed with high-risk changes without setting proper expectations

8. **Don't violate naming conventions**
   - Never use kebab-case for localStorage keys (use camelCase)
   - Don't mix naming patterns in component code
   - Don't create new patterns without documentation

9. **NEVER ASSUME ENDPOINT OR FILE EXISTENCE**
   - Never assume an endpoint exists just because it would follow a pattern
   - Always verify files and endpoints before referencing them in code
   - Don't create code that calls non-existent endpoints without creating them first

10. **NEVER DUPLICATE CODE UNNECESSARILY**
    - Don't copy-paste large blocks of code between files
    - Don't recreate functionality that already exists in the codebase
    - Don't implement different versions of the same thing across components

11. **DON'T IGNORE VERIFICATION STEPS**
    - Never skip verifying the existence of endpoints, files, or components
    - Don't assume the codebase follows a specific pattern without checking
    - Don't make changes based on assumptions rather than evidence

12. **YOU CAN NOT ACCESS THE APPLICATION DIRECTLY**
    - the application is running in a airgapped environment  in a docker container
    - you must ask user for assistance if you want to test uding generated data or if you want insight into data present in the running system.

## Communication Guidelines

1. **Clarity over verbosity**
   - Be direct and concise about what you're doing and why
   - Avoid unnecessary elaboration that obscures the main point

2. **Acknowledge mistakes quickly**
   - When taking a wrong approach, admit it and pivot immediately
   - Don't try to justify flawed reasoning

3. **Update progress genuinely**
   - Provide honest assessments of progress, not optimistic ones
   - Clearly state when an approach has failed

4. **Ask targeted questions**
   - When more information is needed, ask specific questions
   - Avoid vague requests that put cognitive burden on the user

5. **Be transparent about risks**
   - Clearly communicate when changes might temporarily break functionality
   - Explain the entire process so the user can anticipate issues
   - Give specific details about what might not work during implementation
   - Set proper expectations about the complete fix timeline

## Time Management

1. **Value the user's time above all**
   - Every minute spent debugging is valuable development time lost
   - Use the most efficient debugging techniques first

2. **Establish reasonable timeboxes**
   - If an approach isn't yielding results within a reasonable time, abandon it
   - Set mental time limits for each debugging strategy

3. **Prioritize development tasks over perfectionism**
   - Focus on enabling the user to continue development
   - Complete critical functionality before addressing minor issues

4. **Plan for multi-step implementations**
   - Inform users when fixes will require multiple steps
   - Help them plan around temporary instability
   - Provide clear indications of completion percentage

## Scratchpad Maintenance Protocol (MANDATORY)

1. **Always update the scratchpad during EVERY working session**
   - This is not optional - it's a fundamental responsibility
   - Document all changes, findings, and key information
   - Record successful and failed approaches to avoid repetition
   - Note new patterns discovered in the codebase
   - Document API endpoints discovered and validated
   - Record code structure and reuse opportunities

2. **The scratchpad should contain**:
   - Current state of the project/task
   - Key architectural decisions
   - Component structure notes
   - Critical warnings and flags
   - Context about the current work
   - Issues encountered and their solutions
   - Environment-specific notes (e.g., containerization details)
   - Naming conventions and patterns
   - Store initialization requirements
   - State management approaches
   - API endpoint patterns and validation status

3. **Update frequency**:
   - After each significant code change
   - When discovering important information
   - Before switching focus to a different component
   - When making architectural decisions
   - Before and after testing changes
   - When establishing new patterns
   - After store-related changes

4. **Cross-reference with other documentation**:
   - Ensure scratchpad notes are consistent with .context.md and .warning-flags
   - The three-file system is critical for maintaining context
   - Add date stamps to entries for chronological reference
   - Document naming conventions across all files
   - Track store-related decisions

## Transparent Implementation Protocol

### When to Provide Implementation Warnings

1. **Multi-Step Fixes**
   - When a solution requires multiple changes that won't work until all are in place
   - When intermediate states may break functionality temporarily
   - When refactoring critical components that may cause temporary instability

2. **High-Risk Changes**
   - When modifying core initialization code
   - When fixing recursive loops or timing-dependent code
   - When changing event handlers that might affect multiple components
   - When altering the sequence of operations in critical sections

3. **Uncertain Outcomes**
   - When implementing solutions with unpredictable edge cases
   - When the fix might work in testing but could behave differently in production
   - When fixing one issue might expose or trigger other underlying problems

### How to Communicate Implementation Risks

1. **Before Implementing**
   - "This fix involves changes to [critical component] which might temporarily cause [specific issue] while we implement the complete solution"
   - "We'll need to implement this in multiple steps. During this process, [feature] might not work correctly until all steps are complete"
   - "This is a complex issue that might require multiple iterations to fully resolve"

2. **During Implementation**
   - Provide clear status updates on what's working/not working
   - Explain which issues are expected vs. unexpected
   - Communicate timeline for completing remaining steps

3. **After Implementation**
   - Confirm which issues have been resolved
   - Note any remaining issues or limitations
   - Explain any necessary follow-up changes

### Specific Scenarios Requiring Warnings

- **Initialization Code Changes**: Always warn before modifying how components initialize
- **Event Handler Modifications**: Explain potential temporary issues when changing event flow
- **Core Component Refactoring**: Set clear expectations about instability during refactoring
- **API Integration Changes**: Warn about possible temporary service disruptions
- **State Management Alterations**: Explain potential UI inconsistencies during changes
- **Timing-Dependent Fixes**: Be explicit about the risk of race conditions during implementation
- **WebUI file layout**: Do not confuse the index.* compponents which are in the webui folder directly with other components in the UI reding in webui/ subfolders, the folder layout is:
   ```bash
   $ tree webui
   webui
   ├── css
   │   ├── file_browser.css
   │   ├── history.css
   │   ├── modals.css
   │   ├── settings.css
   │   ├── speech.css
   │   └── toast.css
   ├── index.css
   ├── index.html
   ├── index.js
   ├── js
   │   ├── file_browser.js
   │   ├── history.js
   │   ├── image_modal.js
   │   ├── messages.js
   │   ├── modal.js
   │   ├── scheduler.js
   │   ├── settings.js
   │   ├── speech_browser.js
   │   ├── speech.js
   │   └── transformers@3.0.2.js
   └── public
      ├── agent.svg
      ├── api_keys.svg
      ├── archive.svg
      ├── auth.svg
      ├── browser_model.svg
      ├── chat_model.svg
      ├── code.svg
      ├── darkSymbol.svg
      ├── deletefile.svg
      ├── dev.svg
      ├── document.svg
      ├── downloadfile.svg
      ├── dragndrop.svg
      ├── embed_model.svg
      ├── favicon_round.svg
      ├── favicon.svg
      ├── file.svg
      ├── folder.svg
      ├── image.svg
      ├── memory.svg
      ├── schedule.svg
      ├── settings.svg
      ├── splash.jpg
      ├── stt.svg
      ├── task_scheduler.svg
      └── util_model.svg

   3 directories, 45 files
   ```

## Alpine.js Best Practices

1. **Store Initialization**
   ```javascript
   document.addEventListener('alpine:init', () => {
       if (!Alpine.store('root')) {
           Alpine.store('root', {
               reasoning: "auto",
               planning: "auto",
               deep_search: false,
               selectedTab: 'chats'
           });
       }
   });
   ```

2. **Store Access**
   ```javascript
   // Always check store existence
   if (window.Alpine && Alpine.store('root')) {
       // Safe to access store
   }
   ```

3. **Component Integration**
   ```javascript
   // Use proper naming conventions
   const settingsActiveTab = localStorage.getItem('settingsActiveTab');
   ```

## API Endpoint Verification Protocol

1. **Verify Existing Endpoints First**
   - Check the API folder for existing endpoints before creating new ones
   - Use `ls -la /path/to/api/folder` to list all available endpoints
   - Match endpoint names with their file names (endpoints are named after their files)

2. **Creating New Endpoints**
   - Follow the existing naming pattern in the API folder
   - Create proper Python files in the correct location
   - Ensure all imports are valid and modules exist
   - Test new endpoints thoroughly before referencing them in frontend code

3. **Endpoint Reference Safety**
   ```javascript
   // Only after verifying endpoint existence
   fetch('/verified_endpoint_name')
   ```

These guidelines aim to create a more productive, focused, and frustration-free collaboration experience.
