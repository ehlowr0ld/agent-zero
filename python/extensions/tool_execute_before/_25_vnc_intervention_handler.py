"""
VNC Intervention Handler Extension

This extension captures and records user interventions during VNC sessions,
ensuring they appear in the VNC action log and are properly integrated.
"""

from python.helpers.extension import Extension
from agent import AgentContextType
from python.helpers.print_style import PrintStyle


class VNCInterventionHandler(Extension):
    """Extension for handling user interventions during VNC sessions"""

    async def execute(self, **kwargs):
        """
        Handle user interventions in VNC sessions before tool execution

        This extension:
        - Detects pending interventions during VNC sessions
        - Records interventions in the VNC action log
        - Provides proper context for intervention handling
        """

        # Extract parameters from kwargs
        tool_name = kwargs.get('tool_name')

        try:
            # Check if the current context is a BACKGROUND context and if the tool being executed is an operator tool
            is_background_context = self.agent.context.type == AgentContextType.BACKGROUND
            is_operator_tool = tool_name == "operator"

            if is_background_context and is_operator_tool:
                # Retrieve the VNC operator state from the agent's data
                vnc_state = self.agent.get_data("_vnc_operator_state")
                if vnc_state and hasattr(vnc_state, 'session_id'):

                    # Check if there's a pending intervention message
                    if hasattr(self.agent, 'intervention') and self.agent.intervention:
                        intervention_message = self.agent.intervention.message

                        # Record the intervention in the VNC session's action history
                        vnc_state.record_intervention(intervention_message)

                        # Debug output to console
                        PrintStyle(font_color="#FF69B4", padding=False).print(
                            f"[VNC] Recorded user intervention: {intervention_message[:50]}{'...' if len(intervention_message) > 50 else ''}"
                        )

        except Exception as e:
            # Debug error to console - don't pollute conversation
            PrintStyle(font_color="red", padding=True).print(
                f"[VNC] Intervention handler extension error: {str(e)}"
            )
