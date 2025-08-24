"""
VNC Response Logger Extension

This extension captures agent responses during VNC sessions and logs them
to the VNC action log for display in the persistent chat bubble.
"""

from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle
from agent import AgentContextType


class VNCResponseLogger(Extension):
    """Extension for logging agent responses to VNC action log"""

    async def execute(self, **kwargs):
        """
        Mirror agent responses to VNC action log when in background sessions

        This extension:
        - Detects agent responses in VNC background contexts
        - Captures reasoning and response content
        - Adds them to VNC action log for visibility
        - Mirrors responses to original context in dual mode
        """

        # Extract parameters from kwargs
        loop_data = kwargs.get('loop_data')
        text = kwargs.get('text', '')

        try:
            # Only process in BACKGROUND contexts with active VNC sessions
            if self.agent.context.type != AgentContextType.BACKGROUND:
                return

            # Check if we have an active VNC session
            vnc_state = self.agent.get_data("_vnc_operator_state")
            if not vnc_state or not hasattr(vnc_state, 'session_id'):
                return

            # Only process substantial responses (avoid spam from short chunks)
            if not text or len(text.strip()) < 20:
                return

            # Check if this is a complete response (look for response indicators)
            if loop_data and hasattr(loop_data, 'response_text'):
                complete_response = loop_data.response_text

                # Only process if this is the final chunk of a complete response
                if text in complete_response and len(text) > len(complete_response) * 0.8:
                    # This appears to be a complete response - mirror it
                    vnc_state.record_agent_response(complete_response)

                    # Response mirroring now handled via persistent chat bubble instead of context switching

                    # Debug output to console
                    PrintStyle(font_color="#90EE90", padding=False).print(
                        f"[VNC] Mirrored agent response ({len(complete_response)} chars) to VNC UI"
                    )

        except Exception as e:
            # Debug error to console - don't pollute conversation
            PrintStyle(font_color="red", padding=True).print(
                f"[VNC] Response mirror extension error: {str(e)}"
            )
