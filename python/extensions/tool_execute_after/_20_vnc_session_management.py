"""
VNC Session Management Extension

This extension handles VNC session lifecycle management after tool execution,
specifically managing context switching and session state for operator tools.
"""

from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle


class VNCSessionManagement(Extension):
    """Extension for managing VNC session lifecycle after tool execution"""

    async def execute(self, **kwargs):
        """
        Handle VNC session management after tool execution

        This extension monitors operator tool calls and manages session state:
        - Ensures proper context switching for enter_session/exit_session
        - Manages session cleanup if tools fail
        - Maintains session state consistency
        """

        # Extract parameters from kwargs
        tool_name = kwargs.get('tool_name')

        # Only handle operator tool calls
        if tool_name != "operator":
            return

        try:
            # Get VNC operator state if it exists
            vnc_state = self.agent.get_data("_vnc_operator_state")

            # Check if this was a session management operation
            tool_method = getattr(self.agent.get_tool("operator", None, {}, "", self.agent.loop_data), 'method', None)

            if tool_method == "enter_session":
                # Session entry was attempted - verify state was created
                if vnc_state and hasattr(vnc_state, 'session_id'):
                    # Important operational info for UI
                    self.agent.context.log.log(
                        type="util",
                        heading="VNC Session Active",
                        content=f"Desktop control session {vnc_state.session_id[:8]} started"
                    )

                    # Debug to console
                    PrintStyle(font_color="#00CED1", padding=False).print(
                        f"[VNC] Session {vnc_state.session_id[:8]} successfully started"
                    )
                else:
                    # Session creation failed - ensure clean state
                    self.agent.set_data("_vnc_operator_state", None)
                    PrintStyle(font_color="orange", padding=True).print(
                        "[VNC] Session creation failed - cleaned up state"
                    )

            elif tool_method == "exit_session":
                # Session exit was attempted - ensure state is cleaned up
                if not vnc_state:
                    # State was properly cleaned up - inform user
                    self.agent.context.log.log(
                        type="util",
                        heading="VNC Session Ended",
                        content="Desktop control session completed successfully"
                    )

                    PrintStyle(font_color="#00CED1", padding=False).print(
                        "[VNC] Session successfully terminated"
                    )
                else:
                    # Force cleanup if state still exists
                    try:
                        await vnc_state.cleanup_session()
                        await vnc_state.finalize_session_log()
                        self.agent.set_data("_vnc_operator_state", None)

                        PrintStyle(font_color="orange", padding=True).print(
                            "[VNC] Forced cleanup after exit_session"
                        )
                    except Exception as e:
                        PrintStyle(font_color="red", padding=True).print(
                            f"[VNC] Force cleanup failed: {str(e)}"
                        )

            # Handle session state during other VNC operations
            elif vnc_state and tool_method in [
                "declare_intent", "move_mouse", "click", "double_click", "drag",
                "scroll", "type_text", "press_key", "key_combination", "update_screen"
            ]:
                # Verify session is still valid for VNC operations
                if not hasattr(vnc_state, 'vnc_session') or not vnc_state.vnc_session:
                    # Session is invalid - clean up
                    self.agent.set_data("_vnc_operator_state", None)
                    PrintStyle(font_color="orange", padding=True).print(
                        "[VNC] Invalid session state detected - cleaned up"
                    )

        except Exception as e:
            # Debug error to console - don't pollute conversation
            PrintStyle(font_color="red", padding=True).print(
                f"[VNC] Session management extension error: {str(e)}"
            )
