import asyncio
from python.helpers.tool import Tool, Response
from python.helpers.vnc_state import VNCOperatorState
from typing import List, Dict, Any
from agent import UserMessage


class Operator(Tool):
    def _format_window_details(self, windows: List[Dict[str, Any]]) -> str:
        """Format detailed window information for display"""
        if not windows:
            return "No windows detected"

        # Check for error state
        if len(windows) == 1 and windows[0].get('_error'):
            return f"Window detection unavailable: {windows[0].get('_error_msg', 'X11 tools failed')}"

        # Format window details
        details = [f"Active Windows: {len(windows)}"]
        details.append("\nWindow Details:")
        details.append("ID          | Desktop | PID  | Position    | Size        | Class                | Title")
        details.append("-" * 95)

        for window in windows:
            if window.get('_error'):
                continue

            # Format fields with explanations in comments
            window_id = window.get('id', 'unknown')[:10].ljust(10)  # Window ID (hex identifier)
            desktop = str(window.get('desktop', '?')).ljust(7)  # Desktop number (-1=all desktops)
            pid = str(window.get('pid', '?')).ljust(4)  # Process ID

            # Geometry formatting
            geom = window.get('geometry', {})
            position = "{},{}".format(geom.get('x', '?'), geom.get('y', '?')).ljust(11)  # X,Y coordinates
            size = "{}x{}".format(geom.get('width', '?'), geom.get('height', '?')).ljust(11)  # Width x Height

            window_class = window.get('class', 'unknown')[:20].ljust(20)  # Application.class
            title = window.get('title', 'No title')[:30]  # Window title

            details.append(f"{window_id} | {desktop} | {pid} | {position} | {size} | {window_class} | {title}")

        # Add field explanations
        details.append("\nField Explanations:")
        details.append("• ID: Unique window identifier (hexadecimal)")
        details.append("• Desktop: Virtual desktop number (-1 = visible on all desktops)")
        details.append("• PID: Process ID of the application")
        details.append("• Position: X,Y coordinates of window top-left corner")
        details.append("• Size: Width x Height in pixels")
        details.append("• Class: Application class (format: application.class)")
        details.append("• Title: Current window title/caption")

        return "\n".join(details)

    async def _validate_click_coordinates(self, x: float, y: float, element_id: int, state: VNCOperatorState) -> str:
        """Validate click coordinates against element bounding box and provide correction if needed"""
        try:
            # Get the latest screenshot metadata to access annotations
            if not state.screenshot_metadata:
                return ""  # No validation possible without metadata

            latest_screenshot = state.screenshot_metadata[-1]

            # Parse annotations from the latest screenshot (stored as base64 text)
            annotations_path = latest_screenshot.get('annotations_path', '')
            if not annotations_path:
                return ""  # No annotations available

            # Read annotations file
            from python.helpers import rfc_files
            try:
                annotations_bytes = rfc_files.read_file_bin(annotations_path)
                annotations_content = annotations_bytes.decode('utf-8')
                # Parse the annotations to find the element
                annotations = self._parse_annotations_content(annotations_content)

                if element_id >= len(annotations):
                    return f"❌ Element {element_id} not found. Available elements: 0-{len(annotations)-1}"

                element = annotations[element_id]
                bbox = element.get('bbox', [0, 0, 0, 0])

                if len(bbox) < 4:
                    return ""  # Invalid bbox

                # Check if click coordinates are inside the bounding box
                x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]

                if x1 <= x <= x2 and y1 <= y <= y2:
                    return ""  # Coordinates are valid
                else:
                    # Calculate exact center of the element
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2

                    element_type = element.get('type', 'element')
                    content = element.get('content', '')
                    content_desc = f' ("{content}")' if content else ''

                    return (f"❌ COORDINATE ERROR: Your click at ({x:.3f}, {y:.3f}) is OUTSIDE Element {element_id} {element_type}{content_desc}.\n"
                           f"✅ CORRECTION: Use coordinates ({center_x:.3f}, {center_y:.3f}) to click the CENTER of Element {element_id}.\n"
                           f"Element bounds: ({x1:.3f}, {y1:.3f}) to ({x2:.3f}, {y2:.3f})")

            except Exception as e:
                print(f"[VALIDATION] Error reading annotations: {e}")
                return ""  # Validation failed, allow click to proceed

        except Exception as e:
            print(f"[VALIDATION] Validation error: {e}")
            return ""  # Validation failed, allow click to proceed

    def _parse_annotations_content(self, annotations_content: str) -> List[Dict[str, Any]]:
        """Parse the new clean annotation format to extract element information"""
        import re
        annotations = []

        try:
            # Split by lines and parse each "Element N:" line
            lines = annotations_content.strip().split('\n')
            for line in lines:
                if line.strip().startswith('Element ') and '|' in line:
                    try:
                        # Parse new format: "Element N: TYPE | center=(x,y) | bbox[x1,y1,x2,y2] | content"
                        # Extract element ID
                        element_match = re.match(r'Element (\d+):', line)
                        if not element_match:
                            continue
                        element_id = int(element_match.group(1))

                        # Extract center coordinates
                        center_match = re.search(r'center=\(([0-9.]+),([0-9.]+)\)', line)
                        if not center_match:
                            continue
                        center_x = float(center_match.group(1))
                        center_y = float(center_match.group(2))

                        # Extract bbox coordinates
                        bbox_match = re.search(r'bbox\[([0-9.]+),([0-9.]+),([0-9.]+),([0-9.]+)\]', line)
                        if not bbox_match:
                            continue
                        bbox = [
                            float(bbox_match.group(1)),  # x1
                            float(bbox_match.group(2)),  # y1
                            float(bbox_match.group(3)),  # x2
                            float(bbox_match.group(4))   # y2
                        ]

                        # Extract type and interactivity
                        is_clickable = 'CLICKABLE' in line
                        element_type = 'clickable' if is_clickable else 'text'

                        # Extract content
                        if '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 4:
                                content_part = parts[-1].strip()
                                if content_part.startswith('"') and content_part.endswith('"'):
                                    content = content_part[1:-1]  # Remove quotes
                                elif content_part == '[No text]':
                                    content = ''
                                else:
                                    content = content_part
                            else:
                                content = ''
                        else:
                            content = ''

                        # Create element dict compatible with validation
                        element_dict = {
                            'type': element_type,
                            'bbox': bbox,
                            'interactivity': is_clickable,
                            'content': content,
                            'center_x': center_x,
                            'center_y': center_y
                        }
                        annotations.append(element_dict)

                    except Exception as e:
                        print(f"[PARSE] Error parsing annotation line: {line[:100]}... - {e}")
                        continue
        except Exception as e:
            print(f"[PARSE] Error parsing annotations content: {e}")

        return annotations

    async def execute(self, **kwargs):
        # New unified execute method for action chains
        if self.method == "execute":
            return await self.execute_action_chain(
                actions=kwargs.get("actions", []),
                intent=kwargs.get("intent", None)
            )
        # Legacy single-action methods (backward compatibility)
        elif self.method == "annotated_screenshot":
            return await self.annotated_screenshot()
        elif self.method == "enter_session":
            return await self.enter_session(
                task_description=kwargs.get("task_description", "")
            )
        elif self.method == "exit_session":
            return await self.exit_session()
        elif self.method == "declare_intent":
            return await self.execute_action_chain(
                actions=[],
                intent={"intent": kwargs.get("intent", ""), "reasoning": kwargs.get("reasoning", "")}
            )
        elif self.method == "move_mouse":
            return await self.execute_action_chain(
                actions=[{"method": "move_mouse", "args": {
                    "x": kwargs.get("x", 0.0),
                    "y": kwargs.get("y", 0.0),
                    "coordinate_type": kwargs.get("coordinate_type", "fraction")
                }}]
            )
        elif self.method == "click":
            return await self.execute_action_chain(
                actions=[{"method": "click", "args": {
                    "x": kwargs.get("x", 0.0),
                    "y": kwargs.get("y", 0.0),
                    "button": kwargs.get("button", "left"),
                    "coordinate_type": kwargs.get("coordinate_type", "fraction"),
                    "element_id": kwargs.get("element_id", 0)
                }}],
                intent={"reasoning": kwargs.get("reasoning", "Legacy single click action")}
            )
        elif self.method == "double_click":
            return await self.execute_action_chain(
                actions=[{"method": "double_click", "args": {
                    "x": kwargs.get("x", 0.0),
                    "y": kwargs.get("y", 0.0),
                    "button": kwargs.get("button", "left"),
                    "coordinate_type": kwargs.get("coordinate_type", "fraction"),
                    "element_id": kwargs.get("element_id", 0)
                }}],
                intent={"reasoning": kwargs.get("reasoning", "Legacy single double-click action")}
            )
        elif self.method == "drag":
            return await self.execute_action_chain(
                actions=[{"method": "drag", "args": {
                    "start_x": kwargs.get("start_x", 0.0),
                    "start_y": kwargs.get("start_y", 0.0),
                    "end_x": kwargs.get("end_x", 0.0),
                    "end_y": kwargs.get("end_y", 0.0),
                    "button": kwargs.get("button", "left"),
                    "coordinate_type": kwargs.get("coordinate_type", "fraction")
                }}]
            )
        elif self.method == "scroll":
            return await self.execute_action_chain(
                actions=[{"method": "scroll", "args": {
                    "x": kwargs.get("x", 0.0),
                    "y": kwargs.get("y", 0.0),
                    "direction": kwargs.get("direction", "up"),
                    "amount": kwargs.get("amount", 3),
                    "coordinate_type": kwargs.get("coordinate_type", "fraction")
                }}]
            )
        elif self.method == "type_text":
            return await self.execute_action_chain(
                actions=[{"method": "type_text", "args": {"text": kwargs.get("text", "")}}]
            )
        elif self.method == "press_key":
            return await self.execute_action_chain(
                actions=[{"method": "press_key", "args": {"key": kwargs.get("key", "")}}]
            )
        elif self.method == "key_combination":
            return await self.execute_action_chain(
                actions=[{"method": "key_combination", "args": {"keys": kwargs.get("keys", [])}}]
            )
        elif self.method == "update_screen":
            return await self.update_screen()
        else:
            return Response(message=f"Unknown method: {self.method}", break_loop=False)

    async def annotated_screenshot(self):
        """Capture and return annotated screenshot of the desktop"""
        from python.helpers.vnc import VNC

        vnc = VNC("localhost", 5900)
        try:
            path, annotations = await vnc.get_annotated_image()
            message = self.agent.parse_prompt(
                "fw.tool.operator.annotated_screenshot.md",
                screenshot_path=path,
                annotations=annotations
            )
            return Response(message=message, break_loop=False)
        except Exception as e:
            return Response(message=f"Failed to capture screenshot: {str(e)}", break_loop=False)

    async def execute_action_chain(self, actions: List[dict], intent: dict = None) -> Response:
        """Execute a chain of actions with optional intent, taking only one screenshot at the end"""
        try:
            # Handle interventions before starting
            await self.agent.handle_intervention()

            state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
            if not state or not state.vnc_session:
                return Response("No active VNC session. Use enter_session first.", False)

                        # PRE-VALIDATE ALL ACTIONS FIRST - abort entire chain if any validation fails
            for i, action_def in enumerate(actions):
                method = action_def.get("method")
                args = action_def.get("args", {})

                if not method:
                    return Response(f"❌ VALIDATION FAILED: Action {i+1} missing method. Chain aborted.", False)

                # Pre-validate click and double_click actions - now mandatory parameters
                if method in ["click", "double_click"]:
                    x = args.get("x")
                    y = args.get("y")
                    coordinate_type = args.get("coordinate_type")
                    element_id = args.get("element_id")

                    # Check mandatory parameters
                    if x is None or y is None:
                        return Response(f"❌ VALIDATION FAILED: Action {i+1} ({method}) missing x or y coordinates. Chain aborted.", False)

                    if coordinate_type is None:
                        return Response(f"❌ VALIDATION FAILED: Action {i+1} ({method}) missing coordinate_type (must be 'fraction' or 'pixel'). Chain aborted.", False)

                    if element_id is None:
                        return Response(f"❌ VALIDATION FAILED: Action {i+1} ({method}) missing element_id (use element number or 0 for non-element). Chain aborted.", False)

                    # Check reasoning requirement for element_id=0
                    if element_id == 0:
                        if not intent or not intent.get("reasoning"):
                            return Response(f"❌ VALIDATION FAILED: Action {i+1} ({method}) uses element_id=0 but no reasoning provided in intent. Must explain why clicking non-element area. Chain aborted.", False)

                    # Validate coordinates for detected elements
                    if element_id > 0:
                        validation_result = await self._validate_click_coordinates(x, y, element_id, state)
                        if validation_result:
                            return Response(f"❌ VALIDATION FAILED: Action {i+1} ({method})\n{validation_result}\n\n🚫 ENTIRE CHAIN ABORTED - Fix coordinates and retry.", False)

            executed_actions = []
            # Execute intent first if provided
            if intent and intent.get("intent"):
                state.declare_intent(intent["intent"], intent.get("reasoning", ""))
                executed_actions.append(f"Intent: {intent['intent']}")

            # Execute all actions sequentially without intermediate screenshots
            for i, action_def in enumerate(actions):
                method = action_def.get("method")
                args = action_def.get("args", {})

                try:
                    print(f"[CHAIN] Executing action {i+1}/{len(actions)}: {method}")

                    # Route to internal action methods (validation already done in pre-validation)
                    if method == "move_mouse":
                        result = await self._move_mouse(**args)
                    elif method == "click":
                        result = await self._click(skip_validation=True, **args)
                    elif method == "double_click":
                        result = await self._double_click(skip_validation=True, **args)
                    elif method == "drag":
                        result = await self._drag(**args)
                    elif method == "scroll":
                        result = await self._scroll(**args)
                    elif method == "type_text":
                        result = await self._type_text(**args)
                    elif method == "press_key":
                        result = await self._press_key(**args)
                    elif method == "key_combination":
                        result = await self._key_combination(**args)
                    elif method == "delay":
                        seconds = args.get("seconds", 1)
                        print(f"[CHAIN] Delaying {seconds}s as requested...")
                        await asyncio.sleep(seconds)
                        result = f"Delayed {seconds} seconds"
                    else:
                        executed_actions.append(f"Action {i+1}: Unknown method '{method}'")
                        continue

                    executed_actions.append(f"Action {i+1}: {result}")
                except Exception as e:
                    error_msg = f"Action {i+1} ({method}) failed: {str(e)}"
                    executed_actions.append(error_msg)
                    print(f"[CHAIN] {error_msg}")

                # Add 1-second delay between actions (except after the last action)
                if i < len(actions) - 1:
                    print(f"[CHAIN] Waiting 1s before next action...")
                    await asyncio.sleep(1)

            # Take single screenshot at end of chain if any actions were performed
            if len(actions) > 0:
                # Wait a moment after last action for UI/processes to complete
                print(f"[CHAIN] Chain completed, waiting 2s for UI/processes to settle before screenshot...")
                await asyncio.sleep(2)
                print(f"[CHAIN] Taking final screenshot after {len(actions)} actions")
                await state.mark_action_completed(f"action_chain_{len(actions)}_actions")

            await self.agent.handle_intervention()

            # Create response message
            chain_summary = f"Executed {len(actions)} actions in chain"
            if intent:
                chain_summary = f"Intent: {intent['intent']} | " + chain_summary

            response_details = "\n".join(executed_actions)
            full_message = f"{chain_summary}\n\nDetails:\n{response_details}"

            return Response(message=full_message, break_loop=False)
        except Exception as e:
            return Response(message=f"Error executing action chain: {str(e)}", break_loop=False)

    async def enter_session(self, task_description: str = "") -> Response:
        """Enter VNC desktop control session"""
        try:
            # Initialize VNC operator state for persistent chat bubble mode
            state = VNCOperatorState(self.agent, host="localhost", port=5900)
            await state.initialize_session(task_description)

            # Store state in agent data
            self.agent.set_data("_vnc_operator_state", state)

            # Switch to background context (or enable dual mode)
            await state.setup_persistent_vnc_log()

            # Ensure screenshot is in context for agent's welcome message (only add to context here)
            desktop_state = await state.ensure_screenshot_in_context(force_new=False)

            # Add conversation message to original context for visibility
            session_start_msg = (f"🖥️ **VNC Desktop Session Started**\n"
                                 f"Session ID: {state.session_id[:8]}\n"
                                 f"Task: {task_description}\n"
                                 f"Screen: {state.screen_dimensions[0]}x{state.screen_dimensions[1]}\n\n"
                                 f"*Desktop control is now active. All actions will be visible below.*")

            # Add message to user for visibility
            self.agent.hist_add_user_message(UserMessage(message=session_start_msg))

            screen_dimensions_str = f"{state.screen_dimensions[0]}x{state.screen_dimensions[1]}"
            mp = desktop_state.get('mouse_position', {}) if isinstance(desktop_state, dict) else {}
            mp_frac = desktop_state.get('mouse_position_fraction', {}) if isinstance(desktop_state, dict) else {}

            # Handle error states in display
            if mp.get('_error') or mp.get('x') == 'unknown':
                mouse_position_pixels = "unknown (X11 unavailable)"
            else:
                mouse_position_pixels = str(mp)

            if mp_frac.get('x') == 'unknown':
                mouse_position_fraction = "unknown (X11 unavailable)"
            else:
                mouse_position_fraction = str(mp_frac)

            # Format detailed window information
            windows = desktop_state.get('windows', []) if isinstance(desktop_state, dict) else []
            window_details = self._format_window_details(windows)

            message = self.agent.parse_prompt(
                "fw.tool.operator.enter_session.md",
                task_description=task_description,
                session_id=state.session_id[:8],
                screen_dimensions_str=screen_dimensions_str,
                mouse_position_pixels=mouse_position_pixels,
                mouse_position_fraction=mouse_position_fraction,
                window_details=window_details,
                plain_screenshot=state.original_screenshot_path,
                annotated_screenshot=state.annotated_screenshot_path
            )

            return Response(message=message, break_loop=False)

        except Exception as e:
            error_msg = f"Failed to enter VNC session: {str(e)}"
            return Response(message=error_msg, break_loop=False)

    async def exit_session(self) -> Response:
        """Exit VNC desktop control session"""
        try:
            state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
            if not state:
                return Response(message="No active VNC session found", break_loop=False)

            # Add session ending message for user visibility
            session_end_msg = (f"🖥️ **VNC Desktop Session Ending**\n"
                               f"Session ID: {state.session_id[:8]}\n"
                               f"Actions performed: {len(state.action_history)}\n"
                               f"Intents declared: {len(state.intent_declarations)}\n\n"
                               f"*Generating session summary and returning to normal conversation...*")

            # Add end message to user
            self.agent.hist_add_user_message(UserMessage(message=session_end_msg))

            # Generate session summary before cleanup
            session_summary = await state.generate_session_summary()

            # Cleanup session
            await state.cleanup_session()

            # Restore original context
            await state.finalize_session_log()

            # Clear state from agent data
            self.agent.set_data("_vnc_operator_state", None)

            message = self.agent.parse_prompt(
                "fw.tool.operator.exit_session.md",
                session_summary=session_summary,
                session_id=state.session_id[:8]
            )

            return Response(message=message, break_loop=False)

        except Exception as e:
            error_msg = f"Failed to exit VNC session: {str(e)}"
            return Response(message=error_msg, break_loop=False)

    async def declare_intent(self, intent: str, reasoning: str) -> Response:
        """Declare intent for upcoming desktop actions"""
        try:
            state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
            if not state:
                return Response(
                    message="❌ No active VNC session found. Use 'operator:enter_session' to start a desktop control session first.",
                    break_loop=False
                )

            # Record intent in VNC state
            intent_declaration = state.declare_intent(intent, reasoning)

            # Add intent message for user visibility
            intent_msg = (f"🎯 **VNC Intent Declared**\n"
                          f"Intent: {intent}\n"
                          f"Reasoning: {reasoning}")
            self.agent.hist_add_user_message(UserMessage(message=intent_msg))

            message = self.agent.parse_prompt(
                "fw.tool.operator.declare_intent.md",
                intent=intent,
                reasoning=reasoning,
                session_id=state.session_id[:8],
                timestamp=intent_declaration.timestamp.strftime("%H:%M:%S")
            )

            return Response(message=message, break_loop=False)

        except Exception as e:
            error_msg = f"Failed to declare intent: {str(e)}"
            return Response(message=error_msg, break_loop=False)

    async def _move_mouse(self, x: float, y: float, coordinate_type: str = "fraction") -> str:
        """Internal: Move mouse cursor to specified coordinates (no screenshot)"""
        state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
        if not state or not state.vnc_session:
            raise RuntimeError("No active VNC session")

        # Convert coordinates if needed
        if coordinate_type == "fraction":
            pixel_x, pixel_y = state.vnc_session.fraction_to_pixels(x, y)
        else:
            pixel_x, pixel_y = int(x), int(y)

        # Perform action
        await state.vnc_session.move_mouse(pixel_x, pixel_y)

        # Record action only (no screenshot)
        state.record_action("move_mouse", coordinates=(pixel_x, pixel_y))
        return f"Moved mouse to ({pixel_x}, {pixel_y})"

    async def _click(self, x: float, y: float, coordinate_type: str, element_id: int, button: str = "left", skip_validation: bool = False) -> str:
        """Internal: Click at specified coordinates with optional element validation (no screenshot)"""
        state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
        if not state or not state.vnc_session:
            raise RuntimeError("No active VNC session")

        # Validate element_id if provided (unless validation already done)
        if not skip_validation and element_id > 0:
            validation_result = await self._validate_click_coordinates(x, y, element_id, state)
            if validation_result:
                return validation_result  # Return correction message

        # Convert coordinates if needed
        if coordinate_type == "fraction":
            pixel_x, pixel_y = state.vnc_session.fraction_to_pixels(x, y)
        else:
            pixel_x, pixel_y = int(x), int(y)

        # Perform action with additional delay for UI responsiveness
        await state.vnc_session.click(pixel_x, pixel_y, button)

        # Give UI extra time to respond to click (some applications are slow)
        await asyncio.sleep(0.2)

        # Record action only (no screenshot)
        state.record_action("click", coordinates=(pixel_x, pixel_y), button=button)

        if element_id > 0:
            return f"Clicked {button} button on Element {element_id} at ({pixel_x}, {pixel_y})"
        else:
            return f"Clicked {button} button at ({pixel_x}, {pixel_y}) [non-element area]"

    async def _double_click(self, x: float, y: float, coordinate_type: str, element_id: int, button: str = "left", skip_validation: bool = False) -> str:
        """Internal: Double-click at specified coordinates with optional element validation (no screenshot)"""
        state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
        if not state or not state.vnc_session:
            raise RuntimeError("No active VNC session")

        # Validate element_id if provided (unless validation already done)
        if not skip_validation and element_id > 0:
            validation_result = await self._validate_click_coordinates(x, y, element_id, state)
            if validation_result:
                return validation_result  # Return correction message

        # Convert coordinates if needed
        if coordinate_type == "fraction":
            pixel_x, pixel_y = state.vnc_session.fraction_to_pixels(x, y)
        else:
            pixel_x, pixel_y = int(x), int(y)

        # Perform action with additional delay for UI responsiveness
        await state.vnc_session.double_click(pixel_x, pixel_y, button)

        # Give UI extra time to respond to double-click (some applications are slow)
        await asyncio.sleep(0.2)

        # Record action only (no screenshot)
        state.record_action("double_click", coordinates=(pixel_x, pixel_y), button=button)

        if element_id > 0:
            return f"Double-clicked {button} button on Element {element_id} at ({pixel_x}, {pixel_y})"
        else:
            return f"Double-clicked {button} button at ({pixel_x}, {pixel_y}) [non-element area]"

    async def _drag(self, start_x: float, start_y: float, end_x: float, end_y: float,
                    button: str = "left", coordinate_type: str = "fraction") -> str:
        """Internal: Drag from start coordinates to end coordinates (no screenshot)"""
        state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
        if not state or not state.vnc_session:
            raise RuntimeError("No active VNC session")

        # Convert coordinates if needed
        if coordinate_type == "fraction":
            start_pixel_x, start_pixel_y = state.vnc_session.fraction_to_pixels(start_x, start_y)
            end_pixel_x, end_pixel_y = state.vnc_session.fraction_to_pixels(end_x, end_y)
        else:
            start_pixel_x, start_pixel_y = int(start_x), int(start_y)
            end_pixel_x, end_pixel_y = int(end_x), int(end_y)

        # Perform action
        await state.vnc_session.drag(start_pixel_x, start_pixel_y, end_pixel_x, end_pixel_y, button)

        # Record action only (no screenshot)
        state.record_action("drag", coordinates=((start_pixel_x, start_pixel_y), (end_pixel_x, end_pixel_y)), button=button)
        return f"Dragged from ({start_pixel_x}, {start_pixel_y}) to ({end_pixel_x}, {end_pixel_y})"

    async def _scroll(self, x: float, y: float, direction: str = "up", amount: int = 3,
                      coordinate_type: str = "fraction") -> str:
        """Internal: Scroll at specified coordinates (no screenshot)"""
        state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
        if not state or not state.vnc_session:
            raise RuntimeError("No active VNC session")

        # Convert coordinates if needed
        if coordinate_type == "fraction":
            pixel_x, pixel_y = state.vnc_session.fraction_to_pixels(x, y)
        else:
            pixel_x, pixel_y = int(x), int(y)

        # Perform action
        await state.vnc_session.scroll(pixel_x, pixel_y, direction, amount)

        # Record action only (no screenshot)
        state.record_action("scroll", coordinates=(pixel_x, pixel_y))
        return f"Scrolled {direction} {amount} times at ({pixel_x}, {pixel_y})"

    async def _type_text(self, text: str) -> str:
        """Internal: Type text string (no screenshot)"""
        state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
        if not state or not state.vnc_session:
            raise RuntimeError("No active VNC session")

        # Perform action
        await state.vnc_session.type_text(text)

        # Record action only (no screenshot)
        state.record_action("type_text", text=text)
        return f"Typed text: {text}"

    async def _press_key(self, key: str) -> str:
        """Internal: Press a single key (no screenshot)"""
        state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
        if not state or not state.vnc_session:
            raise RuntimeError("No active VNC session")

        # Perform action
        await state.vnc_session.press_key(key)

        # Record action only (no screenshot)
        state.record_action("press_key", keys=[key])
        return f"Pressed key: {key}"

    async def _key_combination(self, keys: List[str]) -> str:
        """Internal: Press key combination (no screenshot)"""
        state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
        if not state or not state.vnc_session:
            raise RuntimeError("No active VNC session")

        # Perform action
        await state.vnc_session.key_combination(keys)

        # Record action only (no screenshot)
        state.record_action("key_combination", keys=keys)
        return f"Pressed key combination: {' + '.join(keys)}"

    async def update_screen(self) -> Response:
        """Capture fresh screenshot and update desktop state"""
        try:
            # Handle interventions before action
            await self.agent.handle_intervention()

            state: VNCOperatorState = self.agent.get_data("_vnc_operator_state")
            if not state or not state.vnc_session:
                return Response("No active VNC session. Use enter_session first.", False)

            # Get fresh screenshot with delay and add to context (user explicitly requested update)
            desktop_state = await state.ensure_screenshot_in_context(force_new=True, delay_before_screenshot=True)

            # Record action and handle interventions after
            state.record_action("update_screen")
            await self.agent.handle_intervention()

            # Format response with desktop information
            action_log = "\n".join([
                f"Intent: {intent['intent']}" for intent in state.get_action_log()[-3:]
            ]) if state.get_action_log() else "No recent actions"

            screen_dimensions_str = f"{state.screen_dimensions[0]}x{state.screen_dimensions[1]}"
            mp = desktop_state.get('mouse_position', {}) if isinstance(desktop_state, dict) else {}
            mp_frac = desktop_state.get('mouse_position_fraction', {}) if isinstance(desktop_state, dict) else {}

            # Handle error states in display
            if mp.get('_error') or mp.get('x') == 'unknown':
                mouse_position_pixels = "unknown (X11 unavailable)"
            else:
                mouse_position_pixels = str(mp)

            if mp_frac.get('x') == 'unknown':
                mouse_position_fraction = "unknown (X11 unavailable)"
            else:
                mouse_position_fraction = str(mp_frac)

            # Format detailed window information
            windows = desktop_state.get('windows', []) if isinstance(desktop_state, dict) else []
            window_details = self._format_window_details(windows)

            response_text = self.agent.parse_prompt(
                "fw.tool.operator.update_screen.md",
                screen_dimensions_str=screen_dimensions_str,
                mouse_position_pixels=mouse_position_pixels,
                mouse_position_fraction=mouse_position_fraction,
                window_details=window_details,
                plain_screenshot=state.original_screenshot_path,
                annotated_screenshot=state.annotated_screenshot_path,
                action_log=action_log
            )

            return Response(response_text, False)

        except Exception as e:
            return Response(f"Error updating screen: {str(e)}", False)

    def get_log_object(self):
        """Create VNC-specific log object for persistent chat bubble"""
        return self.agent.context.log.log(
            type="vnc",
            heading=f"icon://desktop_windows {self.agent.agent_name}: VNC Desktop Control",
            content="",
            kvps=self.args,
        )
