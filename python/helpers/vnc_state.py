import uuid
import asyncio
import base64
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from agent import Agent, UserMessage
from python.helpers.vnc import VNCSession
from python.helpers import rfc_files, images, history
from python.helpers.print_style import PrintStyle


@dataclass
class ActionRecord:
    """Record of a single action performed during VNC session"""
    action_type: str
    timestamp: datetime
    coordinates: Optional[Tuple[int, int]] = None
    button: Optional[str] = None
    text: Optional[str] = None
    keys: Optional[List[str]] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class IntentDeclaration:
    """Record of an agent's declared intent and associated actions"""
    timestamp: datetime
    intent: str
    reasoning: str
    actions: List[ActionRecord]
    completed: bool = False


class VNCOperatorState:
    """
    Manages the state of a VNC desktop control session

    This class handles the complete lifecycle of VNC sessions including:
    - Context switching between normal and background contexts
    - Desktop state management and screenshot tracking
    - Action and intent logging
    - Session summarization and cleanup
    """

    def __init__(self, agent: Agent, host: str = "localhost", port: int = 5900,
                 username: str = "agent-zero", password: str = "changeme"):
        self.agent = agent
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        # Session identification and timing
        self.session_id = str(uuid.uuid4())
        self.session_start_time: Optional[datetime] = None
        self.session_end_time: Optional[datetime] = None

        # VNC session and paths
        self.vnc_session: Optional[VNCSession] = None
        self.session_folder_relative = f"vnc/sessions/{self.session_id[:8]}"
        self.session_folder = rfc_files.get_abs_path(self.session_folder_relative)
        self.original_screenshot_path = ""
        self.annotated_screenshot_path = ""

        # Task description
        self.task_description = ""

        # Desktop state and session data
        self.screen_dimensions = (1024, 1024)  # Default, updated on connection
        self.latest_desktop_state: Optional[Dict[str, Any]] = None

        # Intent and action tracking
        self.intent_declarations: List[IntentDeclaration] = []
        self.action_history: List[ActionRecord] = []
        self.current_intent: Optional[IntentDeclaration] = None

        # Vision screenshot tracking (keep only last 1 for context management)
        self.screenshot_history: List[Dict[str, Any]] = []
        self.max_screenshots_in_context = 1

        # Screenshot metadata tracking for auditing and referencing
        self.screenshot_metadata: List[Dict[str, Any]] = []

        # Desktop state coordination
        self.last_screenshot_time: Optional[datetime] = None
        self.desktop_state_dirty = True  # Force initial screenshot
        self.min_screenshot_interval = 1.0  # Minimum seconds between screenshots
        self.last_context_screenshot_time: Optional[datetime] = None  # When we last added screenshot to context
        self.action_screenshot_delay = 0.5  # Delay after actions before taking screenshot (allow UI to update)
        # Create session folder via RFC
        rfc_files.make_directories(self.session_folder_relative)

    def _count_elements_from_annotations(self, annotations: str) -> int:
        """Count actual elements from the formatted annotation string"""
        if not annotations or not isinstance(annotations, str):
            return 0

        try:
            # Count lines that start with "Element N:"
            lines = annotations.strip().split('\n')
            element_count = 0
            for line in lines:
                if line.strip().startswith('Element ') and ':' in line:
                    element_count += 1
            return element_count
        except Exception as e:
            print(f"[VNC-STATE] Error counting elements: {e}")
            return 0

    async def initialize_session(self, task_description: str = "") -> None:
        """Initialize the VNC session with full setup"""
        self.task_description = task_description
        self.session_start_time = datetime.now(timezone.utc)

        # No context switching - use persistent chat bubble pattern instead

        # Initialize VNC session with session_id for consistent file naming
        self.vnc_session = VNCSession(self.host, self.port, self.username, self.password, self.session_id)

        # Clean up old screenshots (older than 24 hours) to prevent disk space issues
        try:
            removed_count = VNCSession.cleanup_old_screenshots(max_age_hours=24)
            if removed_count > 0:
                print(f"[VNC-INIT] Cleaned up {removed_count} old screenshot files")
        except Exception as e:
            print(f"[VNC-INIT] Warning: Could not clean up old screenshots: {e}")

        # Take initial screenshot and populate desktop state
        # This avoids needing "dirty" flag logic in ensure_screenshot_in_context
        await self.update_desktop_state()

    async def setup_persistent_vnc_log(self) -> None:
        """Setup persistent VNC log entry for chat bubble (replaces context switching)"""
        # Create VNC session marker message for user visibility
        vnc_session_marker = UserMessage(
            message=f"🖥️ **VNC Desktop Session Started** (ID: {self.session_id[:8]})\n"
                    f"Task: {self.task_description}\n\n"
                    f"*VNC interface will appear below and update in real-time.*"
        )
        self.agent.hist_add_user_message(vnc_session_marker)

    async def finalize_session_log(self) -> None:
        """Add session completion marker and summary to chat (replaces context restoration)"""
        # Mark session as ended
        self.session_end_time = datetime.now(timezone.utc)

        end_time = self.session_end_time or datetime.now(timezone.utc)
        start_time = self.session_start_time or datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        completion_marker = UserMessage(
            message=f"🖥️ **VNC Desktop Session Completed**\n"
                    f"Session ID: {self.session_id[:8]}\n"
                    f"Duration: {duration:.1f} seconds\n"
                    f"Actions performed: {len(self.action_history)}\n"
                    f"Intents declared: {len(self.intent_declarations)}\n\n"
                    f"*VNC interface has been closed. Session summary follows below.*"
        )
        self.agent.hist_add_user_message(completion_marker)

        # Generate and add summary
        session_summary = await self.generate_session_summary()
        summary_message = UserMessage(
            message=f"📋 **VNC Session Summary**\n{session_summary}"
        )
        self.agent.hist_add_user_message(summary_message)

    async def update_desktop_state(self, force_refresh: bool = False, delay_before_screenshot: bool = False) -> Dict[str, Any]:
        """Central desktop state coordinator - only takes new screenshots when needed"""
        if not self.vnc_session:
            raise RuntimeError("VNC session not initialized")

        # Check if we need a new screenshot
        now = datetime.now(timezone.utc)
        time_since_last = None
        if self.last_screenshot_time:
            time_since_last = (now - self.last_screenshot_time).total_seconds()

        need_refresh = (
            force_refresh or
            self.desktop_state_dirty or
            self.latest_desktop_state is None or
            (time_since_last is not None and time_since_last >= self.min_screenshot_interval)
        )

        if need_refresh:
            # Add delay if requested (e.g., after actions to let UI update)
            if delay_before_screenshot:
                print(f"[VNC-STATE] Waiting {self.action_screenshot_delay}s for UI to update after action...")
                await asyncio.sleep(self.action_screenshot_delay)
            time_str = f"{time_since_last:.1f}s" if time_since_last is not None else "never"
            print(f"[VNC-STATE] Taking new screenshot (force={force_refresh}, dirty={self.desktop_state_dirty}, "
                  f"time_since_last={time_str})")
            # Get annotated screenshot and desktop state
            annotated_path, annotations, desktop_state = await self.vnc_session.get_annotated_screenshot()

            # Update paths and cache desktop state (now using RFC relative paths)
            self.original_screenshot_path = self.vnc_session.image_path_original_relative
            self.annotated_screenshot_path = self.vnc_session.image_path_annotated_relative
            self.latest_desktop_state = desktop_state

            # Update screen dimensions
            if 'screen_dimensions' in desktop_state:
                dimensions = desktop_state['screen_dimensions']
                self.screen_dimensions = (dimensions['width'], dimensions['height'])

            # Derive fractional mouse position for prompts and guidance
            try:
                mp = desktop_state.get('mouse_position') or {}
                # Check if mouse position has error flag or unknown values
                if mp.get('_error') or mp.get('x') == 'unknown' or mp.get('y') == 'unknown':
                    desktop_state['mouse_position_fraction'] = {'x': 'unknown', 'y': 'unknown'}
                else:
                    w, h = self.screen_dimensions
                    fx = round(float(mp.get('x', 0)) / w, 4) if w else 0.0
                    fy = round(float(mp.get('y', 0)) / h, 4) if h else 0.0
                    desktop_state['mouse_position_fraction'] = {'x': fx, 'y': fy}
            except Exception:
                desktop_state['mouse_position_fraction'] = {'x': 'unknown', 'y': 'unknown'}

            # Update coordination state
            self.last_screenshot_time = now
            self.desktop_state_dirty = False
            # Note: Screenshot taken but not added to context yet - will be added when actually used
        else:
            age_str = f"{time_since_last:.1f}s" if time_since_last is not None else "unknown"
            print(f"[VNC-STATE] Reusing cached desktop state (age: {age_str})")
            desktop_state = self.latest_desktop_state

        return desktop_state

    def mark_desktop_dirty(self, reason: str = "state_changed"):
        """Mark desktop state as dirty, requiring fresh screenshot on next update"""
        self.desktop_state_dirty = True
        print(f"[VNC-STATE] Desktop marked as dirty: {reason}")

    async def mark_action_completed(self, action_name: str):
        """Mark that an action was completed and ensure new state reaches agent context"""
        print(f"[VNC-STATE] Action '{action_name}' completed, updating state with delay")
        self.mark_desktop_dirty(f"action_{action_name}")
        # Ensure the new state gets into agent context (with delay for UI to settle)
        await self.ensure_screenshot_in_context(force_new=False, delay_before_screenshot=True)

    async def ensure_screenshot_in_context(self, force_new: bool = False, delay_before_screenshot: bool = False) -> Dict[str, Any]:
        """Ensure current screenshot is in agent context - only add if screen actually changed"""
        # Smart force logic: only force if screen isn't already fresh
        should_force = force_new and (self.desktop_state_dirty or
                                      self.last_screenshot_time is None or
                                      (datetime.now(timezone.utc) - self.last_screenshot_time).total_seconds() > 2.0)

        # If we have fresh desktop state and don't need to force, reuse it
        if (not should_force and
            not self.desktop_state_dirty and
            self.latest_desktop_state is not None and
            self.last_screenshot_time is not None):
            print("[VNC-STATE] Reusing existing fresh desktop state (no screenshot needed)")
            desktop_state = self.latest_desktop_state
        else:
            # Get current desktop state (may take new screenshot)
            desktop_state = await self.update_desktop_state(force_refresh=should_force, delay_before_screenshot=delay_before_screenshot)

        # Only add to context if screen has actually changed OR never added before
        should_add_to_context = (
            self.last_context_screenshot_time is None or  # Never added to context (first time)
            (self.last_screenshot_time and self.last_context_screenshot_time and
             self.last_screenshot_time > self.last_context_screenshot_time)  # New screenshot since last context addition
        )

        if should_add_to_context and self.annotated_screenshot_path:
            print("[VNC-STATE] Adding screenshot to context - screen changed since last context addition")
            print(f"[VNC-STATE] last_screenshot={self.last_screenshot_time}, last_context={self.last_context_screenshot_time}")
            await self.add_screenshot_to_context(
                self.annotated_screenshot_path,
                desktop_state.get('annotations', ''),
                desktop_state
            )
            # Update context timestamp to prevent duplicate additions
            self.last_context_screenshot_time = datetime.now(timezone.utc)
        else:
            print("[VNC-STATE] Screen unchanged since last context addition - skipping duplicate")
        return desktop_state

    def declare_intent(self, intent: str, reasoning: str) -> IntentDeclaration:
        """Declare a new intent for upcoming actions"""
        # Mark previous intent as completed
        if self.current_intent and not self.current_intent.completed:
            self.current_intent.completed = True

        # Create new intent declaration
        intent_declaration = IntentDeclaration(
            timestamp=datetime.now(timezone.utc),
            intent=intent,
            reasoning=reasoning,
            actions=[]
        )

        self.intent_declarations.append(intent_declaration)
        self.current_intent = intent_declaration

        return intent_declaration

    def record_action(self, action_type: str, coordinates: Optional[Tuple[int, int]] = None,
                      button: Optional[str] = None, text: Optional[str] = None,
                      keys: Optional[List[str]] = None, success: bool = True,
                      error_message: Optional[str] = None) -> ActionRecord:
        """Record an action performed during the session"""
        action = ActionRecord(
            action_type=action_type,
            timestamp=datetime.now(timezone.utc),
            coordinates=coordinates,
            button=button,
            text=text,
            keys=keys,
            success=success,
            error_message=error_message
        )

        self.action_history.append(action)

        # Add to current intent if one exists
        if self.current_intent:
            self.current_intent.actions.append(action)

        return action

    def record_intervention(self, intervention_message: str) -> ActionRecord:
        """Record an intervention message as a special action type"""
        intervention_action = self.record_action(
            action_type="intervention",
            text=intervention_message,
            success=True
        )

        # Debug output to console - don't pollute conversation with intervention logging
        PrintStyle(font_color="#FF69B4", padding=False).print(
            f"[VNC] Intervention recorded: {intervention_message[:50]}{'...' if len(intervention_message) > 50 else ''}"
        )

        return intervention_action

    def record_agent_response(self, response_text: str) -> ActionRecord:
        """Record an agent response for visibility in VNC UI"""
        response_action = self.record_action(
            action_type="agent_response",
            text=response_text,
            success=True
        )

        return response_action

    def record_agent_reasoning(self, reasoning_text: str) -> ActionRecord:
        """Record agent reasoning for visibility in VNC UI"""
        reasoning_action = self.record_action(
            action_type="agent_reasoning",
            text=reasoning_text,
            success=True
        )

        return reasoning_action

    def record_tool_result(self, tool_name: str, result_text: str) -> ActionRecord:
        """Record tool execution results for visibility in VNC UI"""
        tool_action = self.record_action(
            action_type="tool_result",
            text=f"Tool: {tool_name}\nResult: {result_text}",
            success=True
        )

        # Mark desktop state as dirty since we performed an action
        self.mark_desktop_dirty("action_performed")
        return tool_action

    async def add_screenshot_to_context(self, screenshot_path: str, annotations: Any, desktop_state: Dict[str, Any]) -> None:
        """Add both plain and annotated screenshots to agent context, keeping only the latest screenshot"""
        try:
            # Compression settings
            MAX_PIXELS = 768_000
            QUALITY = 75

            # Read and process PLAIN screenshot
            original_content = rfc_files.read_file_base64(self.original_screenshot_path)
            original_bytes = base64.b64decode(original_content)
            original_compressed = images.compress_image(original_bytes, max_pixels=MAX_PIXELS, quality=QUALITY)
            original_b64 = base64.b64encode(original_compressed).decode("utf-8")

            # Read and process ANNOTATED screenshot (with fallback if OmniParser failed)
            try:
                annotated_content = rfc_files.read_file_base64(screenshot_path)
                annotated_bytes = base64.b64decode(annotated_content)
                annotated_compressed = images.compress_image(annotated_bytes, max_pixels=MAX_PIXELS, quality=QUALITY)
                annotated_b64 = base64.b64encode(annotated_compressed).decode("utf-8")
                has_annotated = True
            except Exception as e:
                print(f"[VNC] Warning: Annotated screenshot not available ({e}), using plain screenshot only")
                # Use original screenshot as fallback for annotated view
                annotated_b64 = original_b64
                has_annotated = False

            # Create vision message content with BOTH screenshots
            annotated_desc = ("Same view with interactive elements marked and numbered for reference"
                              if has_annotated else "Same as plain screenshot (annotations unavailable)")
            vision_content = [
                {
                    "type": "text",
                    "text": (
                        f"VNC Desktop State: {self._count_elements_from_annotations(annotations) if annotations and has_annotated else 0} interactive elements detected. "
                        f"Mouse position: ({desktop_state.get('mouse_position', {}).get('x', 'N/A')}, "
                        f"{desktop_state.get('mouse_position', {}).get('y', 'N/A')}). "
                        f"Active windows: {len(desktop_state.get('windows', []))}.\n\n"
                        f"Two views provided:\n"
                        f"1. PLAIN SCREENSHOT: Clean desktop view without annotations\n"
                        f"2. ANNOTATED SCREENSHOT: {annotated_desc}\n\n"
                        f"Annotations: {annotations if has_annotated else 'Not available - analyze plain screenshot visually'}"
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{original_b64}"}
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{annotated_b64}"}
                }
            ]

            # Create RawMessage for agent history
            # Use same token estimation technique as vision_load tool: 1500 tokens per content item
            TOKENS_ESTIMATE = 1500  # Same constant as vision_load tool
            total_tokens = TOKENS_ESTIMATE * len(vision_content)  # 1 text + 2 images = 4500 tokens
            msg: history.RawMessage = {
                "raw_content": vision_content,  # type: ignore
                "preview": "VNC Desktop - Plain + Annotated Screenshots"
            }

            # Add to agent history and get the message object for tracking
            message_obj = self.agent.hist_add_message(False, content=msg, tokens=total_tokens)

            # Extract screenshot ID from path for tracking
            screenshot_id = "unknown"
            try:
                # Extract from path: vnc/screenshots/session_<guid>_<timestamp>_<id>_<type>.<ext>
                filename = screenshot_path.split('/')[-1]  # Get filename
                parts = filename.split('_')
                if len(parts) >= 4:
                    screenshot_id = parts[3]  # Fourth part is the unique ID
            except Exception:
                pass

            # Track screenshot message in history for removal
            screenshot_record = {
                'timestamp': datetime.now(timezone.utc),
                'path': screenshot_path,
                'annotations': annotations,
                'message_obj': message_obj,  # Track actual message object for removal
                'screenshot_id': screenshot_id
            }

            # Remove ALL old screenshots before adding the new one to ensure only latest is in context
            while len(self.screenshot_history) > 0:
                old_record = self.screenshot_history.pop(0)
                if old_record['message_obj'] and hasattr(self.agent.history, 'current') and self.agent.history.current:
                    try:
                        # Replace heavy image with text summary to preserve context but save space
                        if old_record['message_obj'] in self.agent.history.current.messages:
                            # Extract original text content and remove only the heavy image data
                            message_idx = self.agent.history.current.messages.index(old_record['message_obj'])
                            original_content = old_record['message_obj'].content

                            # Keep the original text parts, remove only image_url parts
                            text_only_content = []
                            if isinstance(original_content, list):
                                for item in original_content:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        text_only_content.append(item)

                            # Create lightweight replacement message
                            lightweight_msg = text_only_content if text_only_content else [
                                {"type": "text", "text": "Previous VNC screenshot (replaced with summary to save context space)"}
                            ]

                            # Replace the heavy message with lightweight version
                            # Use same token estimation as vision_load: 1500 tokens per content item
                            TOKENS_ESTIMATE = 1500  # Same constant as vision_load tool
                            lightweight_tokens = TOKENS_ESTIMATE * len(text_only_content)  # Usually 1 text item = 1500 tokens
                            new_message_obj = type(old_record['message_obj'])(
                                ai=old_record['message_obj'].ai,
                                content=lightweight_msg,
                                tokens=lightweight_tokens
                            )
                            self.agent.history.current.messages[message_idx] = new_message_obj

                            PrintStyle(font_color="#FFD700", padding=False).print(
                                f"[VNC] Replaced old screenshot with text summary in CHAT HISTORY: {old_record['path']}"
                            )
                    except Exception as e:
                        PrintStyle(font_color="#FFA500", padding=False).print(
                            f"[VNC] Warning: Could not remove old screenshot from chat history: {str(e)}"
                        )

            # Now add the new screenshot
            self.screenshot_history.append(screenshot_record)

            # Track screenshot metadata for auditing
            screenshot_metadata = {
                'screenshot_id': screenshot_id,
                'timestamp': datetime.now(timezone.utc),
                'session_id': self.session_id,
                'original_path': self.original_screenshot_path,
                'annotated_path': screenshot_path,
                'annotations_path': self.vnc_session.image_annotations_text_relative if self.vnc_session else "",
                'mouse_position': desktop_state.get('mouse_position', {}),
                'window_count': len(desktop_state.get('windows', [])),
                'screen_dimensions': desktop_state.get('screen_dimensions', {}),
                'annotation_count': self._count_elements_from_annotations(annotations) if annotations else 0,
                'tokens_used': total_tokens
            }
            self.screenshot_metadata.append(screenshot_metadata)

            # Screenshot cleanup is now handled above before adding the new one

            annotation_count = self._count_elements_from_annotations(screenshot_record['annotations']) if screenshot_record['annotations'] else 0
            content_text = screenshot_record['message_obj'].output_text()
            content_preview = content_text[:50] if content_text else ""
            PrintStyle(font_color="#90EE90", padding=False).print(
                f"[VNC] Added screenshot {screenshot_record['path'][:50]}... with content {content_preview}... to context ({annotation_count} annotations)"
            )
            token_count = len(content_text) if content_text else 0
            PrintStyle(font_color="#90EE90", padding=False).print(
                f"[VNC] Added annotations {screenshot_record['annotations'][:50]}... to context ({token_count} tokens)"
            )

        except Exception as e:
            PrintStyle(font_color="red", padding=True).print(
                f"[VNC] Failed to add screenshot to context: {str(e)}"
            )

    def get_action_log(self) -> List[Dict[str, Any]]:
        """Get formatted action log for UI display"""
        log_entries: List[Dict[str, Any]] = []

        for intent in self.intent_declarations:
            intent_entry: Dict[str, Any] = {
                'type': 'intent',
                'timestamp': intent.timestamp.isoformat(),
                'intent': intent.intent,
                'reasoning': intent.reasoning,
                'completed': intent.completed,
                'actions': []
            }

            for action in intent.actions:
                action_entry = {
                    'type': 'action',
                    'action_type': action.action_type,
                    'timestamp': action.timestamp.isoformat(),
                    'coordinates': action.coordinates,
                    'button': action.button,
                    'text': action.text,
                    'keys': action.keys,
                    'success': action.success,
                    'error_message': action.error_message
                }

                # Special formatting for intervention actions
                if action.action_type == "intervention":
                    action_entry.update({
                        'type': 'intervention',
                        'is_user_intervention': True,
                        'intervention_message': action.text,
                        'display_text': f"User: {action.text}"
                    })

                # Special formatting for agent responses
                elif action.action_type == "agent_response":
                    action_entry.update({
                        'type': 'agent_response',
                        'is_agent_communication': True,
                        'response_text': action.text,
                        'display_text': f"Agent: {action.text}"
                    })

                # Special formatting for agent reasoning
                elif action.action_type == "agent_reasoning":
                    action_entry.update({
                        'type': 'agent_reasoning',
                        'is_agent_communication': True,
                        'reasoning_text': action.text,
                        'display_text': f"Reasoning: {action.text}"
                    })

                # Special formatting for tool results
                elif action.action_type == "tool_result":
                    action_entry.update({
                        'type': 'tool_result',
                        'is_agent_communication': True,
                        'tool_result_text': action.text,
                        'display_text': f"Tool Result: {action.text}"
                    })

                intent_entry['actions'].append(action_entry)

            log_entries.append(intent_entry)

        return log_entries

    def get_screenshot_metadata(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get screenshot metadata for auditing and referencing"""
        metadata = self.screenshot_metadata.copy()
        if limit:
            metadata = metadata[-limit:]  # Get most recent N screenshots

        # Convert datetime objects to ISO strings for JSON serialization
        for item in metadata:
            if isinstance(item.get('timestamp'), datetime):
                item['timestamp'] = item['timestamp'].isoformat()

        return metadata

    def get_screenshot_by_id(self, screenshot_id: str) -> Optional[Dict[str, Any]]:
        """Get screenshot metadata by unique ID"""
        for metadata in self.screenshot_metadata:
            if metadata.get('screenshot_id') == screenshot_id:
                # Convert datetime to ISO string
                result = metadata.copy()
                if isinstance(result.get('timestamp'), datetime):
                    result['timestamp'] = result['timestamp'].isoformat()
                return result
        return None

    async def generate_session_summary(self) -> str:
        """Generate an AI summary of the session activities"""
        if not self.session_start_time:
            return "Session was not properly initialized."

        # Calculate session duration
        end_time = self.session_end_time or datetime.now(timezone.utc)
        duration = end_time - self.session_start_time

        # Collect session information
        summary_parts = []
        summary_parts.append("VNC Desktop Session Summary")
        summary_parts.append(f"Task: {self.task_description}")
        summary_parts.append(f"Duration: {duration.total_seconds():.1f} seconds")
        summary_parts.append(f"Actions performed: {len(self.action_history)}")
        summary_parts.append(f"Intent declarations: {len(self.intent_declarations)}")

        if self.intent_declarations:
            summary_parts.append("\nKey activities:")
            for intent in self.intent_declarations:
                summary_parts.append(f"- {intent.intent}")
                if intent.actions:
                    action_types = [action.action_type for action in intent.actions]
                    summary_parts.append(f"  Actions: {', '.join(set(action_types))}")

        return "\n".join(summary_parts)

    async def cleanup_session(self) -> None:
        """Clean up VNC session resources"""
        self.session_end_time = datetime.now(timezone.utc)

        if self.vnc_session:
            await self.vnc_session.disconnect()
            self.vnc_session = None

        # Mark current intent as completed if it exists
        if self.current_intent and not self.current_intent.completed:
            self.current_intent.completed = True

    def get_coordinate_helpers(self) -> Dict[str, Any]:
        """Get coordinate conversion helpers for the current screen"""
        if not self.vnc_session:
            return {}

        return {
            'screen_width': self.screen_dimensions[0],
            'screen_height': self.screen_dimensions[1],
            'fraction_to_pixels': self.vnc_session.fraction_to_pixels,
            'pixels_to_fraction': self.vnc_session.pixels_to_fraction,
            'convert_annotation_coords': self.vnc_session.convert_annotation_coords
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for persistence"""
        return {
            'session_id': self.session_id,
            'session_start_time': self.session_start_time.isoformat() if self.session_start_time else None,
            'session_end_time': self.session_end_time.isoformat() if self.session_end_time else None,
            'task_description': self.task_description,
            'session_active': self.session_start_time is not None and self.session_end_time is None,
            'screen_dimensions': self.screen_dimensions,
            'current_screenshot_path': self.original_screenshot_path,
            'annotated_screenshot_path': self.annotated_screenshot_path,
            'intent_count': len(self.intent_declarations),
            'action_count': len(self.action_history)
        }

# Removed mirror_to_original_context method - no longer needed without dual context mode
