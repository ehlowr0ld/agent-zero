import asyncio
import subprocess
from typing import Dict, Any, List
import os

# Start with parent environment
env = os.environ.copy()

# Ensure critical X11 variables are set
env.update({
    'DISPLAY': os.environ.get('DISPLAY', ':0'),
    'XAUTHORITY': os.environ.get('XAUTHORITY', f"{os.environ.get('HOME', '')}/.Xauthority"),
    'VNCDISPLAY': '1024x1024'
})


async def get_mouse_position() -> Dict[str, Any]:
    """Get current mouse position using xdotool inside container"""
    try:
        result = await asyncio.create_subprocess_shell(
            'DISPLAY=:0 /usr/local/bin/xdotool getmouselocation --shell',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        stdout, stderr = await result.communicate()

        if result.returncode == 0 and stdout:
            lines = stdout.decode().strip().split('\n')
            mouse_info = {}
            for line in lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    mouse_info[key.lower()] = int(value) if value.isdigit() else value

            if mouse_info and 'x' in mouse_info and 'y' in mouse_info:
                mouse_info['_error'] = False
                return mouse_info
        else:
            print(f"[X11] xdotool failed: returncode={result.returncode}, stderr={stderr.decode()}")

    except Exception as e:
        print(f"[X11] get_mouse_position exception: {e}")

    # Return error state when xdotool fails
    return {"x": "unknown", "y": "unknown", "screen": "unknown", "window": "unknown", "_error": True}


async def get_window_list() -> List[Dict[str, Any]]:
    """Get window information using wmctrl inside container"""
    try:
        result = await asyncio.create_subprocess_shell(
            'DISPLAY=:0 wmctrl -l -i -G -p -x',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        stdout, stderr = await result.communicate()

        if result.returncode == 0:
            windows = []
            lines = stdout.decode().strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split(None, 9)
                    if len(parts) >= 8:
                        windows.append({
                            'id': parts[0],
                            'desktop': int(parts[1]) if parts[1].isdigit() else -1,
                            'pid': int(parts[2]) if parts[2].isdigit() else -1,
                            'geometry': {
                                'x': int(parts[3]) if parts[3].isdigit() else 0,
                                'y': int(parts[4]) if parts[4].isdigit() else 0,
                                'width': int(parts[5]) if parts[5].isdigit() else 0,
                                'height': int(parts[6]) if parts[6].isdigit() else 0
                            },
                            'class': parts[7],
                            'machine': parts[8],
                            'title': parts[9] if len(parts) > 9 else ''
                        })
            return windows
        else:
            print(f"[X11] wmctrl error: {stderr.decode()}")
            return [{"_error": True, "_error_msg": f"wmctrl failed: {stderr.decode()}"}]
    except Exception as e:
        print(f"[X11] get_window_list exception: {e}")
        return [{"_error": True, "_error_msg": f"Exception: {str(e)}"}]


async def get_window_hierarchy() -> Dict[str, Any]:
    """Get detailed window hierarchy using xwininfo inside container"""
    try:
        result = await asyncio.create_subprocess_shell(
            'DISPLAY=:0 xwininfo -tree -root',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        stdout, stderr = await result.communicate()

        if result.returncode == 0:
            hierarchy_raw = stdout.decode().strip()
            # Parse the hierarchy into structured data
            hierarchy: Dict[str, Any] = {
                'raw_output': hierarchy_raw,
                'root_window': None,
                'window_count': 0,
                'windows': [],
                '_error': False
            }

            lines = hierarchy_raw.split('\n')
            for line in lines:
                if 'Window id:' in line and 'the root window' in line:
                    # Extract root window ID
                    import re
                    match = re.search(r'Window id: (0x[0-9a-fA-F]+)', line)
                    if match:
                        hierarchy['root_window'] = match.group(1)
                elif 'children:' in line:
                    # Extract number of children
                    import re
                    match = re.search(r'(\d+) children?:', line)
                    if match:
                        hierarchy['window_count'] = int(match.group(1))

            return hierarchy
        else:
            print(f"[X11] xwininfo error: {stderr.decode()}")
            return {
                'raw_output': 'unavailable', 'root_window': 'unknown', 'window_count': 'unknown',
                'windows': [], '_error': True, '_error_msg': f"xwininfo failed: {stderr.decode()}"
            }
    except Exception as e:
        print(f"[X11] get_window_hierarchy exception: {e}")
        return {
            'raw_output': 'unavailable', 'root_window': 'unknown', 'window_count': 'unknown',
            'windows': [], '_error': True, '_error_msg': f"Exception: {str(e)}"
        }
