"""
VNC Context Injection Extension

This extension injects VNC-specific context information into the agent's prompt
when operating in a VNC background context, providing task context and guidance.
"""

from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle


class VNCContextInjection(Extension):
    """Extension for injecting VNC context information in background sessions"""

    async def execute(self, **kwargs):
        """
        Inject VNC context information when in a background VNC session

        This extension checks if the agent is in a VNC background context and injects:
        - Current VNC session information
        - Available VNC actions and guidance
        - Desktop state information
        - Session history and intent tracking
        """

        # Extract parameters from kwargs
        loop_data = kwargs.get('loop_data')

        try:
            # Only inject VNC context when there's an active VNC session
            # (VNC sessions now operate in main context, not background context)

            # Check if we have an active VNC session
            vnc_state = self.agent.get_data("_vnc_operator_state")
            if not vnc_state or not hasattr(vnc_state, 'session_id'):
                return

            # Inject VNC session context into the prompt
            vnc_context = self.agent.parse_prompt(
                "operator.vnc_session_context.md",
                session_id=vnc_state.session_id[:8],
                task_description=vnc_state.task_description,
                screen_dimensions=f"{vnc_state.screen_dimensions[0]}x{vnc_state.screen_dimensions[1]}",
                session_start_time=vnc_state.session_start_time.strftime("%H:%M:%S"),
                current_intent=vnc_state.current_intent.intent if vnc_state.current_intent else "No current intent",
                actions_performed=len(vnc_state.action_history),
                annotated_screenshot_path=vnc_state.annotated_screenshot_path
            )

            # Add to system prompts for this message loop iteration
            loop_data.system.append(vnc_context)

            # If we have recent desktop state, include it
            if hasattr(vnc_state, 'latest_desktop_state') and vnc_state.latest_desktop_state:
                desktop_info = self.agent.parse_prompt(
                    "operator.desktop_state_info.md",
                    mouse_position=vnc_state.latest_desktop_state.get('mouse_position', {}),
                    window_count=len(vnc_state.latest_desktop_state.get('windows', [])),
                    window_hierarchy_count=vnc_state.latest_desktop_state.get('window_hierarchy', {}).get('window_count', 0)
                )
                loop_data.system.append(desktop_info)

            # Include action guidance
            action_guidance = self.agent.parse_prompt("operator.vnc_action_guidance.md")
            loop_data.system.append(action_guidance)

            # Include verification protocol (CRITICAL for preventing assumptions)
            verification_protocol = self.agent.parse_prompt("operator.verification_protocol.md")
            loop_data.system.append(verification_protocol)

            # Include core desktop automation principles
            desktop_automation_core = self.agent.parse_prompt("agent.system.desktop_automation_core.md")
            loop_data.system.append(desktop_automation_core)

            # Include Kali Linux XFCE4 environment-specific guidance
            kali_xfce4_guide = self.agent.parse_prompt("operator.kali_xfce4_environment.md")
            loop_data.system.append(kali_xfce4_guide)

            # Include screenshot analysis protocol
            screenshot_analysis = self.agent.parse_prompt("operator.screenshot_analysis_protocol.md")
            loop_data.system.append(screenshot_analysis)

            # Add intervention handling guidance
            intervention_guidance = """
## VNC Session Intervention Support

**User Interventions During VNC Sessions:**
- Users can send messages at any time during VNC operations
- Interventions will appear in your action log as special entries
- You should acknowledge interventions and adapt your actions accordingly
- Continue with your task unless the intervention requires a different approach
- All VNC actions automatically handle intervention processing

**When Interventions Occur:**
1. Complete your current action if safe to do so
2. Acknowledge the user's message
3. Adapt your plan based on the intervention
4. Continue or modify your task as appropriate
"""
            loop_data.system.append(intervention_guidance)

        except Exception as e:
            # Debug error to console - don't pollute conversation
            PrintStyle(font_color="red", padding=True).print(
                f"[VNC] Context injection extension error: {str(e)}"
            )
