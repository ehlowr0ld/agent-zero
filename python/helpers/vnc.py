# Remove unused import
import uuid
import asyncio
import subprocess
from typing import Optional, Tuple, Dict, Any, List
import io

import requests
import time
import os

import python.helpers.runtime as agent_runtime
import python.helpers.rfc_files as rfc_files
from python.helpers.print_style import PrintStyle


# Import worker coordination functions from OmniParser server
try:
    from lib.OmniParser.omniparser_server import (
        get_worker_starting_lock_path,
        cleanup_worker_starting_lock
    )
except ImportError:
    # Fallback if server module not available
    def get_worker_starting_lock_path(port: int) -> str:
        return f"/tmp/omniparser_starting_{port}.lock"

    def cleanup_worker_starting_lock(port: int):
        lock_path = get_worker_starting_lock_path(port)
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
        except Exception:
            pass

from PIL import Image, ImageDraw
import asyncvnc2


def wait_for_worker_ready(port: int, timeout: float = 20.0) -> bool:
    """Wait for OmniParser worker starting lock to disappear (RFC client coordination)"""
    lock_path = get_worker_starting_lock_path(port)
    start_time = time.time()

    print(f"[VNC-COORD] Checking for worker starting lock: {lock_path}")

    if not os.path.exists(lock_path):
        print("[VNC-COORD] No worker starting lock found, worker ready")
        return True

    print(f"[VNC-COORD] Worker starting lock found, waiting up to {timeout}s for worker to be ready...")

    while time.time() - start_time < timeout:
        if not os.path.exists(lock_path):
            elapsed = time.time() - start_time
            print(f"[VNC-COORD] Worker starting lock disappeared after {elapsed:.2f}s, worker ready")
            return True
        time.sleep(0.1)  # Check every 100ms

    # Timeout reached - remove lock and proceed
    elapsed = time.time() - start_time
    print(f"[VNC-COORD] Timeout after {elapsed:.2f}s, removing worker starting lock and proceeding")
    cleanup_worker_starting_lock(port)
    return False


async def omniparser_http_impl(
    service_url: str,
    image_path: str,
    image_output_path: str,
    text_output_path: str,
    box_threshold: float,
    iou_threshold: float,
    use_pytesseract: bool,
    imgsz: int,
    use_florence_captioning: bool = True,
) -> Tuple[int, str, str]:
    """RFC-executed implementation that calls the local HTTP OmniParser worker.
    Worker will save files to the specified output paths and only return success JSON.
    Returns (exitcode, stdout, stderr) as strings.
    """
    try:
        # Extract port from service URL for worker coordination
        import re
        url_match = re.search(r':(\d+)', service_url)
        port = int(url_match.group(1)) if url_match else 8887

        # Wait for worker to be ready (coordination with OmniParser server)
        worker_ready = wait_for_worker_ready(port, timeout=20.0)
        if not worker_ready:
            print("[VNC-COORD] Warning: Worker coordination timeout, proceeding anyway")

        # Continue with HTTP request
        payload = {
            'image_path': image_path,
            'image_output_path': image_output_path,
            'text_output_path': text_output_path,
            'box_threshold': box_threshold,
            'iou_threshold': iou_threshold,
            'use_pytesseract': use_pytesseract,
            'imgsz': imgsz,
            'use_florence_captioning': use_florence_captioning,
        }
        resp = requests.post(service_url, json=payload, timeout=600)
        if resp.status_code != 200:
            return 1, '', f'HTTP {resp.status_code}: {resp.text}'
        data = resp.json()
        if data.get('status') != 'success':
            return 1, '', data.get('error', 'Unknown error from worker')
        return 0, 'OK', ''
    except Exception as e:
        return 1, '', str(e)


class VNCSession:
    """
    Enhanced VNC session management with asyncvnc2 client for desktop control.
    Provides mouse/keyboard actions, screenshot capture, and system information gathering.
    """

    def __init__(self, host: str, port: int, username: str = 'agent-zero', password: str = 'changeme', session_id: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        # Use provided session_id or generate new UUID - but reuse within session
        self.guid = session_id[:8] if session_id else str(uuid.uuid4())[:8]
        self.client: Optional[asyncvnc2.Client] = None
        self.screen_width = 1024
        self.screen_height = 1024

        # Screenshot paths - will be updated with unique IDs for each screenshot
        self.image_path_original_relative = ""
        self.image_path_annotated_relative = ""
        self.image_annotations_text_relative = ""
        rfc_files.make_directories("vnc/screenshots")

    def _generate_screenshot_paths(self) -> Tuple[str, str, str]:
        """Generate unique screenshot paths with timestamp and UUID for each capture"""
        import time
        timestamp = int(time.time() * 1000)  # Milliseconds for uniqueness
        screenshot_id = str(uuid.uuid4())[:8]

        # Format: vnc/screenshots/session_<session>_<timestamp>_<id>_<type>.<ext>
        base_name = f"session_{self.guid}_{timestamp}_{screenshot_id}"

        original_path = f"vnc/screenshots/{base_name}_original.png"
        annotated_path = f"vnc/screenshots/{base_name}_annotated.png"
        annotations_path = f"vnc/screenshots/{base_name}_annotations.txt"

        return original_path, annotated_path, annotations_path

    @staticmethod
    def cleanup_old_screenshots(max_age_hours: int = 24) -> int:
        """Clean up screenshots older than specified hours. Returns count of files removed."""
        import time

        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            removed_count = 0

            # Use RFC to list files in screenshots directory
            try:
                file_items = rfc_files.list_directory("vnc/screenshots")
                for file_item in file_items:
                    # file_item is a dict with 'name', 'path', 'is_file', etc.
                    if not isinstance(file_item, dict) or not file_item.get('is_file'):
                        continue

                    file_name = file_item.get('name', '')
                    if not file_name.startswith("session_"):
                        continue

                    full_path = f"vnc/screenshots/{file_name}"

                    # Extract timestamp from filename (session_<guid>_<timestamp>_<id>_<type>.<ext>)
                    parts = file_name.split('_')
                    if len(parts) >= 3:
                        try:
                            timestamp_ms = int(parts[2])  # Third part is timestamp
                            file_age_seconds = current_time - (timestamp_ms / 1000.0)

                            if file_age_seconds > max_age_seconds:
                                rfc_files.delete_file(full_path)
                                removed_count += 1
                                print(f"[VNC-CLEANUP] Removed old screenshot: {full_path} (age: {file_age_seconds / 3600:.1f}h)")
                        except (ValueError, IndexError):
                            # Skip files with invalid timestamp format
                            continue

            except Exception as e:
                print(f"[VNC-CLEANUP] Error listing screenshot directory: {e}")

            if removed_count > 0:
                print(f"[VNC-CLEANUP] Removed {removed_count} old screenshot files (older than {max_age_hours}h)")
            else:
                print(f"[VNC-CLEANUP] No old screenshot files found (older than {max_age_hours}h)")

            return removed_count

        except Exception as e:
            print(f"[VNC-CLEANUP] Error during cleanup: {e}")
            return 0

    def draw_cursor_on_image(self, image: Image.Image, mouse_x: int, mouse_y: int) -> Image.Image:
        """
        Draw a cursor overlay on the image at the specified mouse position

        Args:
            image: PIL Image to draw cursor on
            mouse_x: X coordinate of mouse cursor
            mouse_y: Y coordinate of mouse cursor

        Returns:
            PIL Image with cursor drawn
        """
        # Make a copy to avoid modifying the original
        image_with_cursor = image.copy()

        # Load the mouse pointer PNG from docs folder
        cursor_path = "docs/pointer-black-50.png"

        try:
            cursor_image = Image.open(cursor_path).convert("RGBA")

            # The cursor image is 50x50 pixels with top-left corner as the tip
            # Position it so the top-left corner (tip) is at the mouse coordinates
            paste_x = mouse_x
            paste_y = mouse_y

            # Ensure cursor doesn't go outside image bounds
            img_width, img_height = image_with_cursor.size
            cursor_width, cursor_height = cursor_image.size

            # Clip cursor position if it would extend beyond image boundaries
            if paste_x + cursor_width > img_width:
                paste_x = img_width - cursor_width
            if paste_y + cursor_height > img_height:
                paste_y = img_height - cursor_height
            if paste_x < 0:
                paste_x = 0
            if paste_y < 0:
                paste_y = 0

            # Paste the cursor image with alpha transparency
            image_with_cursor.paste(cursor_image, (paste_x, paste_y), cursor_image)

        except Exception as e:
            print(f"[VNC] Failed to load cursor image from {cursor_path}: {e}")
            # Fallback to simple dot if PNG loading fails
            draw = ImageDraw.Draw(image_with_cursor)
            draw.ellipse([mouse_x - 5, mouse_y - 5, mouse_x + 5, mouse_y + 5], fill='red', outline='black', width=2)

        return image_with_cursor

    async def connect(self) -> None:
        """Establish VNC connection"""
        # For this implementation, we'll use connection per operation
        # to avoid complex connection state management
        pass

    async def disconnect(self) -> None:
        """Close VNC connection"""
        # No persistent connection to close
        pass

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def _get_client(self):
        """Get a connected client for operations"""
        client = asyncvnc2.connect(self.host, self.port, username=self.username, password=self.password)
        async def check_and_fix_vnc_coordinates(client):
            """Check for VNC coordinate system issues"""
            vnc_width = client.video.width
            vnc_height = client.video.height

            PrintStyle.debug(f"📊 [VNC-SETUP] VNC Screen: {vnc_width}x{vnc_height}")
            PrintStyle.debug(f"📊 [VNC-SETUP] OmniParser: 1024x1024")

            if vnc_width != 1024 or vnc_height != 1024:
                PrintStyle.debug(f"🚨 COORDINATE SCALING REQUIRED!")
                PrintStyle.debug(f"   All OmniParser coordinates must be scaled by:")
                PrintStyle.debug(f"   X-factor: {vnc_width/1024:.3f}")
                PrintStyle.debug(f"   Y-factor: {vnc_height/1024:.3f}")
                return vnc_width/1024, vnc_height/1024
            else:
                PrintStyle.debug("✅ No scaling needed")
                return 1.0, 1.0
        return client

    # Mouse Operations
    async def move_mouse(self, x: int, y: int) -> None:
        """Move mouse cursor to absolute coordinates"""
        async with await self._get_client() as client:
            client.mouse.move(x, y)
            await client.drain()

    async def click(self, x: int, y: int, button: str = 'left') -> None:
        """Click at specified coordinates with error handling and timing"""
        button_map = {'left': 0, 'middle': 1, 'right': 2}
        button_code = button_map.get(button, 0)

        try:
            # Validate coordinates are within screen bounds
            if x < 0 or y < 0 or x > self.screen_width or y > self.screen_height:
                print(f"[VNC-CLICK] WARNING: Click coordinates ({x}, {y}) outside screen bounds ({self.screen_width}x{self.screen_height})")
                # Clamp to screen bounds
                x = max(0, min(x, self.screen_width - 1))
                y = max(0, min(y, self.screen_height - 1))
                print(f"[VNC-CLICK] Clamped coordinates to ({x}, {y})")

            print(f"[VNC-CLICK] Attempting {button} click at ({x}, {y})")
            async with await self._get_client() as client:
                # Move mouse to position first
                client.mouse.move(x, y)
                await client.drain()

                # Small delay to ensure mouse is positioned
                await asyncio.sleep(0.05)

                # Perform click
                client.mouse.click(button_code)
                await client.drain()

                # Small delay after click to ensure it's registered
                await asyncio.sleep(0.1)

                # Optional: Verify mouse position (for debugging)
                # Note: Some VNC servers don't immediately update mouse position
                try:
                    # Try to get updated mouse position to verify
                    from python.helpers import agent_runtime
                    from python.helpers import x11_operations
                    mouse_result = await agent_runtime.call_development_function(x11_operations.get_mouse_position)
                    if not mouse_result.get('_error'):
                        actual_x, actual_y = mouse_result.get('x', 'unknown'), mouse_result.get('y', 'unknown')
                        print(f"[VNC-CLICK] Mouse position after click: ({actual_x}, {actual_y}) [target was ({x}, {y})]")
                except Exception:
                    pass  # Ignore mouse position verification errors

                print(f"[VNC-CLICK] Successfully executed {button} click at ({x}, {y})")
        except Exception as e:
            print(f"[VNC-CLICK] ERROR: Failed to click at ({x}, {y}) - {e}")
            import traceback
            traceback.print_exc()
            raise e

    async def double_click(self, x: int, y: int, button: str = 'left') -> None:
        """Double-click at specified coordinates with proper timing"""
        try:
            print(f"[VNC-DBLCLICK] Attempting {button} double-click at ({x}, {y})")

            # First click
            await self.click(x, y, button)

            # Standard double-click interval (usually 200-300ms for most systems)
            await asyncio.sleep(0.2)

            # Second click
            await self.click(x, y, button)

            print(f"[VNC-DBLCLICK] Successfully executed {button} double-click at ({x}, {y})")
        except Exception as e:
            print(f"[VNC-DBLCLICK] ERROR: Failed to double-click at ({x}, {y}) - {e}")
            raise e

    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, button: str = 'left') -> None:
        """Drag from start coordinates to end coordinates"""
        button_map = {'left': 0, 'middle': 1, 'right': 2}
        button_code = button_map.get(button, 0)

        async with await self._get_client() as client:
            client.mouse.move(start_x, start_y)
            with client.mouse.hold(button_code):
                client.mouse.move(end_x, end_y)
            await client.drain()

    async def scroll(self, x: int, y: int, direction: str = 'up', amount: int = 3) -> None:
        """Scroll at specified coordinates"""
        async with await self._get_client() as client:
            client.mouse.move(x, y)
            if direction == 'up':
                client.mouse.scroll_up(amount)
            else:
                client.mouse.scroll_down(amount)
            await client.drain()

    # Keyboard Operations
    async def type_text(self, text: str) -> None:
        """Type text string"""
        async with await self._get_client() as client:
            client.keyboard.write(text)
            await client.drain()

    async def press_key(self, key: str) -> None:
        """Press a single key"""
        async with await self._get_client() as client:
            client.keyboard.press(key)
            await client.drain()

    async def key_combination(self, keys: List[str]) -> None:
        """Press key combination (e.g., ['Ctrl', 'c'])"""
        async with await self._get_client() as client:
            client.keyboard.press(*keys)
            await client.drain()

    # Screenshot and Annotation
    async def capture_screenshot(self) -> Image.Image:
        """Capture raw screenshot"""
        async with await self._get_client() as client:
            pixels = await client.screenshot()
            image = Image.fromarray(pixels)
            # Update screen dimensions from actual screenshot
            self.screen_width = image.width
            self.screen_height = image.height
            return image

    async def get_annotated_screenshot(self) -> Tuple[str, str, Dict[str, Any]]:
        """
        Capture screenshot with annotations and system information
        Returns: (annotated_image_path, annotations_json, desktop_state)
        """
        try:
            # Generate unique screenshot paths for this capture
            self.image_path_original_relative, self.image_path_annotated_relative, self.image_annotations_text_relative = self._generate_screenshot_paths()

            # Capture screenshot
            image = await self.capture_screenshot()
            image = image.convert("RGB")

            # Get system information including mouse position
            desktop_state = await self.get_desktop_state()
            mouse_pos = desktop_state.get('mouse_position', {})
            mouse_x = mouse_pos.get('x', 0)
            mouse_y = mouse_pos.get('y', 0)

            # Draw cursor on original image
            image_with_cursor = self.draw_cursor_on_image(image, mouse_x, mouse_y)

            # Save original with cursor via RFC using unique path
            original_buffer = io.BytesIO()
            image_with_cursor.save(original_buffer, format='PNG')
            rfc_files.write_file_binary(self.image_path_original_relative, original_buffer.getvalue())
            print(f"[VNC] Saved original screenshot via RFC to {self.image_path_original_relative}")

            # Call HTTP worker via RFC-executed function to generate annotated image & text
            service_url = 'http://127.0.0.1:8887/process'
            print(f"[VNC] Calling OmniParser HTTP worker at {service_url}")

            exitcode, stdout, stderr = await agent_runtime.call_development_function(
                omniparser_http_impl,
                service_url,
                self.image_path_original_relative,
                self.image_path_annotated_relative,
                self.image_annotations_text_relative,
                0.5,    # box_threshold (MUCH HIGHER to drastically reduce false positives)
                0.3,    # iou_threshold
                False,  # use_pytesseract
                1024,   # imgsz
                False,  # use_florence_captioning (DISABLED - was producing noise)
            )

            if exitcode != 0:
                print(f"[VNC] Error executing OmniParser worker: {stderr}")
                return "", "", {
                    'error': f"Error executing OmniParser: {stderr}",
                    'screenshot': {
                        'raw_path': '',
                        'annotated_path': '',
                        'dimensions': [self.screen_width, self.screen_height]
                    },
                    'annotations': '',
                    'mouse_position': {'x': 0, 'y': 0},
                    'windows': [],
                    'window_hierarchy': {},
                    'screen_dimensions': {'width': self.screen_width, 'height': self.screen_height}
                }

            print(f"[VNC] OmniParser worker response: {stdout}")
            print(f"[VNC] Saved annotated screenshot via RFC to {self.image_path_annotated_relative}")

            # Add screenshot data to existing desktop_state (which already contains mouse, windows, etc.)
            desktop_state['screenshot'] = {
                'raw_path': self.image_path_original_relative,  # RFC relative path for links
                'annotated_path': self.image_path_annotated_relative,  # RFC relative path for links
                'dimensions': [self.screen_width, self.screen_height]
            }
            # Read annotations as text (not base64) since they're formatted text from OmniParser
            annotations_bytes = rfc_files.read_file_bin(self.image_annotations_text_relative)
            desktop_state['annotations'] = annotations_bytes.decode('utf-8')

            return self.image_path_annotated_relative, desktop_state['annotations'], desktop_state

        except Exception as e:
            print(f"Error in get_annotated_screenshot: {e}")
            import traceback
            traceback.print_exc()
            # Return safe defaults to prevent NoneType errors
            return "", "", {
                'error': str(e),
                'screenshot': {
                    'raw_path': '',
                    'annotated_path': '',
                    'dimensions': [self.screen_width, self.screen_height]
                },
                'annotations': '',
                'mouse_position': {'x': 0, 'y': 0},
                'windows': [],
                'window_hierarchy': {},
                'screen_dimensions': {'width': self.screen_width, 'height': self.screen_height}
            }

    # System Information Gathering
    async def get_mouse_position(self) -> Dict[str, Any]:
        """Get current mouse position using RFC call to X11 operations"""
        from python.helpers import runtime
        from python.helpers import x11_operations

        try:
            result = await runtime.call_development_function(x11_operations.get_mouse_position)
            print(f"[VNC DEBUG] get_mouse_position returned: {result}")
            return result
        except Exception as e:
            print(f"[VNC] RFC get_mouse_position exception: {e}")
            return {"x": "unknown", "y": "unknown", "screen": "unknown", "window": "unknown", "_error": True, "_error_msg": f"RFC exception: {str(e)}"}

    async def get_window_list(self) -> List[Dict[str, Any]]:
        """Get window information using RFC call to X11 operations"""
        from python.helpers import runtime
        from python.helpers import x11_operations

        try:
            result = await runtime.call_development_function(x11_operations.get_window_list)
            print(f"[VNC DEBUG] get_window_list returned: {len(result) if isinstance(result, list) else 'not a list'} items")
            if isinstance(result, list) and len(result) > 0:
                print(f"[VNC DEBUG] First item: {result[0]}")
            return result
        except Exception as e:
            print(f"[VNC] RFC get_window_list exception: {e}")
            return [{"_error": True, "_error_msg": f"RFC exception: {str(e)}"}]

    async def get_window_hierarchy(self) -> Dict[str, Any]:
        """Get detailed window hierarchy using RFC call to X11 operations"""
        from python.helpers import runtime
        from python.helpers import x11_operations

        try:
            result = await runtime.call_development_function(x11_operations.get_window_hierarchy)
            print(f"[VNC DEBUG] get_window_hierarchy returned: {result}")
            return result
        except Exception as e:
            print(f"[VNC] RFC get_window_hierarchy exception: {e}")
            return {'raw_output': '', 'root_window': None, 'window_count': 0, 'windows': [], '_error': True, '_error_msg': f"RFC exception: {str(e)}"}

    async def get_desktop_state(self) -> Dict[str, Any]:
        """Get comprehensive desktop state information"""
        mouse_info = await self.get_mouse_position()
        windows = await self.get_window_list()
        window_hierarchy = await self.get_window_hierarchy()

        return {
            'mouse_position': mouse_info,
            'windows': windows,
            'window_hierarchy': window_hierarchy,
            'screen_dimensions': {'width': self.screen_width, 'height': self.screen_height}
        }

    # Coordinate Conversion Utilities
    def fraction_to_pixels(self, fx: float, fy: float) -> Tuple[int, int]:
        """Convert fractional coordinates (0.0-1.0) to pixel coordinates"""
        x = int(fx * self.screen_width)
        y = int(fy * self.screen_height)
        return x, y

    def pixels_to_fraction(self, x: int, y: int) -> Tuple[float, float]:
        """Convert pixel coordinates to fractional coordinates (0.0-1.0)"""
        fx = x / self.screen_width
        fy = y / self.screen_height
        return fx, fy

    def convert_annotation_coords(self, bbox: List[float]) -> List[int]:
        """Convert annotation bounding box from fractional to pixel coordinates"""
        if len(bbox) >= 4:
            x1, y1 = self.fraction_to_pixels(bbox[0], bbox[1])
            x2, y2 = self.fraction_to_pixels(bbox[2], bbox[3])
            return [x1, y1, x2, y2]
        return [0, 0, 0, 0]


# Legacy compatibility class
class VNC(VNCSession):
    """Legacy compatibility wrapper for existing code"""

    def __init__(self, host, port, username='agent-zero', password='agent0'):
        # Map old parameter name
        if password == 'agent0':
            password = 'changeme'
        super().__init__(host, port, username, password)

    async def grab_image_bytes(self):
        """Legacy method for compatibility"""
        return await self.capture_screenshot()

    async def get_annotated_image(self) -> tuple[str, str]:
        """Legacy method for compatibility"""
        annotated_path, annotations, _ = await self.get_annotated_screenshot()
        return annotated_path, annotations
