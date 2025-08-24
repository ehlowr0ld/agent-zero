"""
Dynamic Context Injection Extension

This extension dynamically injects specific guidance protocols based on:
- Task requirements (error handling, specific application types)
- Current context conditions (error states, complex workflows)
- User preferences or session characteristics
"""

from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle


class DynamicContextInjection(Extension):
    """Extension for dynamically injecting context-specific guidance"""

    async def execute(self, **kwargs):
        """
        Dynamically inject context-specific guidance based on current conditions

        This extension analyzes the current context and injects relevant protocols:
        - Error handling protocols when failures are detected
        - Application-specific guidance based on active tools
        - Performance optimization tips for complex workflows
        """

        # Extract parameters from kwargs
        loop_data = kwargs.get('loop_data')

        try:
            # Only inject when there's an active VNC session
            # (VNC sessions now operate in main context, not background context)

            # Check if we have an active VNC session
            vnc_state = self.agent.get_data("_vnc_operator_state")
            if not vnc_state or not hasattr(vnc_state, 'session_id'):
                return

            # Analyze recent action history for error patterns
            recent_actions = vnc_state.get_recent_action_log(5) if hasattr(vnc_state, 'get_recent_action_log') else []

            # Check for error indicators in recent actions
            has_errors = any('error' in action.lower() or 'failed' in action.lower()
                             for action in recent_actions if isinstance(action, str))

            # Check for complex workflow indicators
            has_complex_workflow = len(recent_actions) > 10 or any('chain' in action.lower()
                                                                   for action in recent_actions if isinstance(action, str))

            # Inject error handling protocols if errors detected
            if has_errors:
                error_protocols = self.agent.parse_prompt("operator.error_handling_protocols.md")
                loop_data.system.append(error_protocols)

                # Add specific error recovery guidance
                error_recovery_guidance = """
## Enhanced Error Recovery Mode Active

Recent actions have encountered errors. Apply these enhanced recovery strategies:

**Immediate Assessment**:
- Take fresh screenshot before any recovery attempt
- Identify exact failure point and current application state
- Check for blocking dialogs, error messages, or state changes

**Recovery Prioritization**:
1. Handle any blocking UI elements (dialogs, prompts)
2. Restore application to known good state if possible
3. Attempt alternative approach to original objective
4. Document failure pattern for future avoidance

**Adaptive Strategy**:
- Use more conservative timing between actions
- Prefer keyboard shortcuts over mouse clicks when available
- Implement additional verification steps
- Consider breaking complex operations into smaller steps
"""
                loop_data.system.append(error_recovery_guidance)

            # Inject performance optimization for complex workflows
            if has_complex_workflow:
                performance_guidance = """
## Complex Workflow Optimization Active

Extended operation detected. Apply these optimization strategies:

**Efficiency Enhancements**:
- Cache interface knowledge to avoid redundant analysis
- Use keyboard shortcuts for repetitive operations
- Minimize screenshot captures for static interfaces
- Group related actions into efficient sequences

**Resource Management**:
- Monitor application responsiveness and adjust timing
- Allow longer delays for resource-intensive operations
- Consider breaking very long workflows into phases
- Maintain awareness of system resource usage

**Progress Tracking**:
- Establish clear checkpoints throughout the workflow
- Verify critical state changes before proceeding
- Maintain detailed progress documentation
- Plan rollback strategies for complex operations
"""
                loop_data.system.append(performance_guidance)

            # Inject application-specific guidance based on desktop state
            if hasattr(vnc_state, 'latest_desktop_state') and vnc_state.latest_desktop_state:
                desktop_state = vnc_state.latest_desktop_state
                windows = desktop_state.get('windows', [])

                # Check for specific application types
                has_terminal = any('terminal' in str(window).lower() for window in windows)
                has_browser = any('firefox' in str(window).lower() or 'chrome' in str(window).lower()
                                  for window in windows)

                if has_terminal:
                    terminal_guidance = """
## Terminal Application Guidance Active

Terminal applications detected. Apply these specialized strategies:

**Command Execution**:
- Wait for command prompt before entering new commands
- Recognize different prompt formats (root, user, application-specific)
- Handle interactive prompts and menu systems appropriately
- Use Ctrl+C for safe command interruption when needed

**Output Management**:
- Allow sufficient time for command completion
- Recognize progress indicators and status messages
- Handle paged output (more, less) with appropriate navigation
- Parse structured output (tables, lists, formatted data)
"""
                    loop_data.system.append(terminal_guidance)

                if has_browser:
                    browser_guidance = """
## Browser Application Guidance Active

Browser applications detected. Apply these web-specific strategies:

**Page Navigation**:
- Wait for complete page loads before interaction
- Handle dynamic content loading and AJAX updates
- Recognize and handle different page states (loading, error, complete)
- Use appropriate timing for form submissions and navigation

**Element Interaction**:
- Account for responsive design and element repositioning
- Handle dropdown menus and dynamic form elements
- Recognize and interact with web-specific UI patterns
- Manage multiple tabs and window contexts appropriately
"""
                    loop_data.system.append(browser_guidance)

        except Exception as e:
            # Debug error to console - don't pollute conversation
            PrintStyle(font_color="red", padding=True).print(
                f"[VNC] Dynamic context injection error: {str(e)}"
            )
