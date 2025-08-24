"""
VNC Poll Data Extension

This extension adds VNC session data to the poll response, allowing the frontend
to receive VNC updates through the standard Agent Zero polling mechanism.
"""

from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle


class VNCPollData(Extension):
    """Extension for adding VNC data to poll responses"""

    async def execute(self, **kwargs):
        """
        Add VNC session data to poll response

        This extension adds:
        - VNC session status and metadata
        - Current screenshot information
        - Action log updates
        - Session state for frontend synchronization
        """

        try:
            # Extract parameters from kwargs
            context = kwargs.get('context')
            response_data = kwargs.get('response_data')

            if not context or not response_data:
                return

            # Check for active VNC session in the context
            vnc_state = context.agent0.get_data("_vnc_operator_state")

            if vnc_state and hasattr(vnc_state, 'session_id'):
                # VNC session exists - gather data for frontend
                vnc_data = {
                    'is_active': bool(vnc_state.session_start_time and not vnc_state.session_end_time),
                    'session_id': vnc_state.session_id,
                    'task_description': vnc_state.task_description,
                    'start_time': vnc_state.session_start_time.isoformat() if vnc_state.session_start_time else None,
                    'screen_dimensions': {
                        'width': vnc_state.screen_dimensions[0],
                        'height': vnc_state.screen_dimensions[1]
                    },
                    'original_screenshot_path': getattr(vnc_state, 'original_screenshot_path', None),
                    'annotated_screenshot_path': getattr(vnc_state, 'annotated_screenshot_path', None),
                    'screenshot_timestamp': vnc_state.latest_desktop_state.get('screenshot', {}).get('timestamp') if vnc_state.latest_desktop_state else None,
                    'screenshot_history_count': len(vnc_state.screenshot_history) if hasattr(vnc_state, 'screenshot_history') else 0,
                    'last_update': vnc_state.latest_desktop_state.get('timestamp') if vnc_state.latest_desktop_state else None
                }

                # Add action log summary
                action_log = vnc_state.get_action_log()
                vnc_data['action_log'] = action_log
                vnc_data['current_intent'] = vnc_state.current_intent.intent if vnc_state.current_intent else None
                vnc_data['total_intents'] = len(vnc_state.intent_declarations)
                vnc_data['total_actions'] = len(vnc_state.action_history)

                # Add VNC data to poll response
                response_data['vnc'] = vnc_data

            else:
                # No VNC session - send inactive status
                response_data['vnc'] = {
                    'is_active': False,
                    'session_id': None,
                    'message': 'No active VNC session'
                }

        except Exception as e:
            # Debug error to console - don't pollute conversation
            PrintStyle(font_color="red", padding=True).print(
                f"[VNC Poll] Error adding VNC data to poll: {str(e)}"
            )

            # Ensure VNC data exists even if error occurred
            response_data = kwargs.get('response_data')
            if response_data and 'vnc' not in response_data:
                response_data['vnc'] = {
                    'is_active': False,
                    'error': str(e)
                }
