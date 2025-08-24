"""
VNC Reasoning Mirroring Extension

This extension captures agent reasoning during VNC background sessions and mirrors
it to the VNC action log, ensuring users can see agent thought processes.
"""

from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle
from agent import AgentContextType


class VNCReasoningMirror(Extension):
    """Extension for mirroring agent reasoning to VNC action log"""

    async def execute(self, **kwargs):
        """
        Mirror agent reasoning to VNC action log when in background sessions

        This extension:
        - Detects agent reasoning in VNC background contexts
        - Captures reasoning content
        - Adds it to VNC action log for visibility
        - Ensures users see agent thought processes
        """

        # Extract parameters from kwargs
        text = kwargs.get('text', '')

        try:
            # Only process in BACKGROUND contexts with active VNC sessions
            if self.agent.context.type != AgentContextType.BACKGROUND:
                return

            # Check if we have an active VNC session
            vnc_state = self.agent.get_data("_vnc_operator_state")
            if not vnc_state or not hasattr(vnc_state, 'session_id'):
                return

            # Only process substantial reasoning (avoid spam from short chunks)
            if not text or len(text.strip()) < 20:
                return

            # Record the reasoning in VNC action log
            vnc_state.record_agent_reasoning(text)

            # Debug output to console
            PrintStyle(font_color="#FFD700", padding=False).print(
                f"[VNC] Mirrored agent reasoning ({len(text)} chars) to VNC UI"
            )

        except Exception as e:
            # Debug error to console - don't pollute conversation
            PrintStyle(font_color="red", padding=True).print(
                f"[VNC] Reasoning mirror extension error: {str(e)}"
            )
