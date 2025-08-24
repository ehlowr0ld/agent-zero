#!/usr/bin/env python3
"""
OmniParser HTTP Service with Socket Handover (SO_REUSEPORT) and Keepalive
- Listens on a fixed port with SO_REUSEPORT so multiple generations can bind the same port
- Spawns a worker child process that preloads models and binds the same port
- After serving a request, the active process closes its listener and exits; worker takes over immediately
- Includes a --keepalive mode for cron: if no worker is listening, start a new one in the background; otherwise exit
"""
import os
import sys
import io
import time
import base64
import asyncio
import signal
import socket
import subprocess
from typing import Optional
from uuid import uuid4

from aiohttp import web
from PIL import Image

# -----------------------
# Path setup (like agent0)
# -----------------------
ROOT = os.path.abspath(os.path.dirname(__file__) + '/../..')
sys.path.append(os.path.join(ROOT, 'lib/OmniParser'))
sys.path.append(os.path.join(ROOT, 'lib/OmniParser/util'))
sys.path.append(ROOT)

from python.helpers import files  # noqa: E402

# Create weights directories
PREFIX = files.get_abs_path(ROOT, 'OmniParser', 'weights')
os.makedirs(f'{PREFIX}/easyocr', exist_ok=True)
os.makedirs(f'{PREFIX}/tesseract', exist_ok=True)
os.makedirs(f'{PREFIX}/yolo', exist_ok=True)
os.environ['EASYOCR_MODEL_PATH'] = f'{PREFIX}/easyocr'
os.environ['TESSDATA_PREFIX'] = f'{PREFIX}/tesseract/tessdata'
os.environ['YOLO_MODEL_PATH'] = f'{PREFIX}/yolo'

# Import after path setup
from lib.OmniParser.util.utils import setup_easy_ocr, setup_pytesseract  # noqa: E402
import lib.OmniParser.agent0 as agent0  # noqa: E402

# -----------------------
# Config
# -----------------------
HOST = '127.0.0.1'
PORT = int(os.environ.get('OMNIPARSER_PORT', '8887'))
SERVICE_ID = os.environ.get('OMNIPARSER_ID', str(uuid4())[:8])
KEEPALIVE_ENV = 'OMNIPARSER_KEEPALIVE'

# Global handover flag - controls one-request-per-worker behavior
ENABLE_HANDOVER = os.environ.get('OMNIPARSER_ENABLE_HANDOVER', 'true').lower() in ('true', '1', 'yes', 'on')

# Globals per-process
_models_loaded = False
_worker_spawned = False
_listener_sock: Optional[socket.socket] = None
_runner: Optional[web.AppRunner] = None
_site: Optional[web.TCPSite] = None
_first_request_handled = False
_shutting_down = False


# -----------------------
# Worker Coordination Lock Files
# -----------------------
def get_worker_starting_lock_path(port: int) -> str:
    """Get path for worker starting coordination lock file"""
    return f"/tmp/omniparser_starting_{port}.lock"


def create_worker_starting_lock(port: int):
    """Create worker starting lock file to signal worker is initializing"""
    lock_path = get_worker_starting_lock_path(port)
    try:
        with open(lock_path, 'w') as f:
            f.write(f"{os.getpid()}:{time.time()}")
        print(f"[OMNI-COORD] PID={os.getpid()} Created worker starting lock: {lock_path}")
        sys.stdout.flush()
    except Exception as e:
        print(f"[OMNI-ERROR] PID={os.getpid()} Failed to create worker starting lock: {e}")
        sys.stdout.flush()


def remove_worker_starting_lock(port: int):
    """Remove worker starting lock file to signal worker is ready"""
    lock_path = get_worker_starting_lock_path(port)
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
            print(f"[OMNI-COORD] PID={os.getpid()} Removed worker starting lock: {lock_path}")
            sys.stdout.flush()
    except Exception as e:
        print(f"[OMNI-ERROR] PID={os.getpid()} Failed to remove worker starting lock: {e}")
        sys.stdout.flush()


def cleanup_worker_starting_lock(port: int):
    """Cleanup worker starting lock file (for error cases)"""
    remove_worker_starting_lock(port)


# -----------------------
# Model loading
# -----------------------
async def load_models_once():
    global _models_loaded
    if _models_loaded:
        return
    print(f"[OMNI-{SERVICE_ID}] Loading models...")
    sys.stdout.flush()
    t0 = time.time()

    # Load and assign into agent0 globals so agent0.process uses them
    agent0.setup_yolo_model()
    print(f"[OMNI-{SERVICE_ID}] YOLO model loaded in {time.time() - t0:.3f}s")
    sys.stdout.flush()

    agent0.setup_caption_model_processor()
    print(f"[OMNI-{SERVICE_ID}] Caption model loaded in {time.time() - t0:.3f}s")
    sys.stdout.flush()

    setup_easy_ocr()
    print(f"[OMNI-{SERVICE_ID}] Easy OCR loaded in {time.time() - t0:.3f}s")
    sys.stdout.flush()

    setup_pytesseract()
    print(f"[OMNI-{SERVICE_ID}] Pytesseract OCR loaded in {time.time() - t0:.3f}s")
    sys.stdout.flush()

    _models_loaded = True
    print(f"[OMNI-{SERVICE_ID}] Models loaded in {time.time() - t0:.3f}s")
    sys.stdout.flush()

# # -----------------------
# # Socket with SO_REUSEPORT
# # -----------------------
# def make_reuseport_socket(host: str, port: int) -> socket.socket:
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     # Critical for multiple processes binding the same port
#     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
#     # Let aiohttp handle the binding - don't pre-bind here
#     # sock.bind((host, port))
#     # sock.listen(socket.SOMAXCONN)
#     sock.setblocking(False)
#     return sock


# -----------------------
# HTTP Handlers
# -----------------------
async def health_handler(request: web.Request) -> web.Response:
    print(f"[OMNI-HEALTH] PID={os.getpid()} Health check from {request.remote}")
    sys.stdout.flush()
    return web.json_response({
        'status': 'healthy',
        'service_id': SERVICE_ID,
        'models_loaded': _models_loaded,
        'pid': os.getpid(),
        'uptime': int(time.time())
    })


async def process_handler(request: web.Request) -> web.Response:
    global _first_request_handled
    print(f"[OMNI-PROCESS] PID={os.getpid()} Processing request from {request.remote}")
    sys.stdout.flush()

    try:
        try:
            data = await request.json()
        except Exception as e:
            print(f"[OMNI-ERROR] PID={os.getpid()} Invalid JSON in request: {e}")
            sys.stdout.flush()
            raise ValueError(f'Invalid JSON: {e}')

        # Accept either image_base64 or image_path
        image: Optional[Image.Image] = None
        input_image_path_abs: Optional[str] = None
        output_image_path_abs: Optional[str] = None
        output_text_path_abs: Optional[str] = None

        # Log request type
        if 'image_base64' in data:
            print(f"[OMNI-PROCESS] PID={os.getpid()} Processing base64 image")
        elif 'image_path' in data:
            print(f"[OMNI-PROCESS] PID={os.getpid()} Processing image path: {data['image_path']}")
        sys.stdout.flush()

        # Resolve output paths if provided
        if 'image_output_path' in data:
            try:
                output_image_path_abs = files.get_abs_path(data['image_output_path'])
            except Exception as e:
                print(f"[OMNI-ERROR] PID={os.getpid()} Invalid image_output_path: {e}")
                sys.stdout.flush()
                raise ValueError(f'Invalid image_output_path: {e}')
        if 'text_output_path' in data:
            try:
                output_text_path_abs = files.get_abs_path(data['text_output_path'])
            except Exception as e:
                print(f"[OMNI-ERROR] PID={os.getpid()} Invalid text_output_path: {e}")
                sys.stdout.flush()
                raise ValueError(f'Invalid text_output_path: {e}')

        if 'image_base64' in data:
            try:
                raw = base64.b64decode(data['image_base64'])
                image = Image.open(io.BytesIO(raw))
            except Exception as e:
                print(f"[OMNI-ERROR] PID={os.getpid()} Invalid base64 image: {e}")
                sys.stdout.flush()
                raise ValueError(f'Invalid base64 image: {e}')
        elif 'image_path' in data:
            try:
                input_image_path_abs = files.get_abs_path(data['image_path'])
                if input_image_path_abs is None:
                    raise ValueError(f"Invalid image path: {data['image_path']}")
                image = Image.open(input_image_path_abs)
            except Exception as e:
                print(f"[OMNI-ERROR] PID={os.getpid()} Cannot open image_path {data['image_path']}: {e}")
                sys.stdout.flush()
                raise ValueError(f'cannot open image_path: {e}')
        else:
            print(f"[OMNI-ERROR] PID={os.getpid()} No image provided in request")
            sys.stdout.flush()
            raise ValueError('Provide image_base64 or image_path')

        # Conditionally spawn worker ASAP on first handled request (only if handover enabled)
        if ENABLE_HANDOVER and not _first_request_handled:
            print(f"[OMNI-PROCESS] PID={os.getpid()} First request - spawning standby worker (handover enabled)")
            sys.stdout.flush()
            _first_request_handled = True
            asyncio.create_task(spawn_worker_if_needed())
        elif not ENABLE_HANDOVER and not _first_request_handled:
            print(f"[OMNI-PROCESS] PID={os.getpid()} First request - continuing to serve (handover disabled)")
            sys.stdout.flush()
            _first_request_handled = True

        # Defaults
        box_threshold = float(data.get('box_threshold', 0.25))
        iou_threshold = float(data.get('iou_threshold', 0.3))
        use_pytesseract = bool(data.get('use_pytesseract', False))
        imgsz = data.get('imgsz', (1024, 1024))

        if isinstance(imgsz, int):
            imgsz = (imgsz, imgsz)

        # Process via agent0.process
        print(f"[OMNI-PROCESS] PID={os.getpid()} Starting image processing (box_thresh={box_threshold}, "
              f"iou_thresh={iou_threshold}, pytesseract={use_pytesseract}, imgsz={imgsz[0]}x{imgsz[1]})")
        sys.stdout.flush()

        try:
            result_image, parsed_content = agent0.process(image, box_threshold, iou_threshold, use_pytesseract, imgsz, batch_size=10)
            print(f"[OMNI-PROCESS] PID={os.getpid()} Image processing completed successfully")
            sys.stdout.flush()
        except Exception as e:
            print(f"[OMNI-ERROR] PID={os.getpid()} Processing failed: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            raise e

        # Save outputs if paths were provided
        try:
            if output_image_path_abs:
                print(f"[OMNI-PROCESS] PID={os.getpid()} Saving result image to {output_image_path_abs}")
                sys.stdout.flush()
                os.makedirs(os.path.dirname(output_image_path_abs), exist_ok=True)
                result_image.save(output_image_path_abs, format='PNG')
            if output_text_path_abs is not None:
                print(f"[OMNI-PROCESS] PID={os.getpid()} Saving result text to {output_text_path_abs}")
                sys.stdout.flush()
                os.makedirs(os.path.dirname(output_text_path_abs), exist_ok=True)
                with open(output_text_path_abs, 'w', encoding='utf-8') as f:
                    f.write(parsed_content)
        except Exception as e:
            print(f"[OMNI-ERROR] PID={os.getpid()} Failed saving outputs: {e}")
            sys.stdout.flush()
            raise e

        # Schedule graceful handover (close listener, exit) after response is flushed (only if handover enabled)
        if ENABLE_HANDOVER and _first_request_handled:
            print(f"[OMNI-PROCESS] PID={os.getpid()} Request completed successfully, scheduling handover")
            sys.stdout.flush()
            asyncio.create_task(schedule_handover(force=False))
        elif not ENABLE_HANDOVER:
            print(f"[OMNI-PROCESS] PID={os.getpid()} Request completed successfully, ready for next request (handover disabled)")
            sys.stdout.flush()
    except ValueError as e:
        print(f"[OMNI-ERROR] PID={os.getpid()} Global exception in process_handler: {e}")
        sys.stdout.flush()
        return web.json_response({'status': 'error', 'error': f'exception in process_handler: {e}'}, status=400)
    except Exception as e:
        print(f"[OMNI-ERROR] PID={os.getpid()} Global exception in process_handler: {e}")
        sys.stdout.flush()
        return web.json_response({'status': 'error', 'error': f'exception in process_handler: {e}'}, status=500)

    return web.json_response({
        'status': 'success',
        'processing_time': time.time(),
    })


# -----------------------
# Handover and Standby
# -----------------------
async def schedule_handover(force: bool = False):
    global _first_request_handled
    if not force and not _first_request_handled:
        return
    if not ENABLE_HANDOVER and not force:
        print(f"[OMNI-HANDOVER] PID={os.getpid()} Handover disabled, skipping")
        sys.stdout.flush()
        return
    # Remove lock file
    try:
        os.remove(f"/tmp/omniparser_healthy_{PORT}.lock")
    except Exception:
        pass
    # Give the response loop a moment to flush
    await asyncio.sleep(0.05)
    await stop_listening_and_exit()


async def stop_listening_and_exit():
    global _site, _runner, _listener_sock, _shutting_down
    if _shutting_down:
        return
    _shutting_down = True
    print(f"[OMNI-{SERVICE_ID}] Handover: stopping listener and exiting PID={os.getpid()}")
    try:
        if _site:
            await _site.stop()
    except Exception:
        pass
    try:
        if _runner:
            await _runner.cleanup()
    except Exception:
        pass
    try:
        if _listener_sock:
            _listener_sock.close()
    except Exception:
        pass
    # Exit process; standby (already bound) continues serving
    os._exit(0)


async def spawn_worker_if_needed(force: bool = False):
    global _worker_spawned, _first_request_handled
    # Only spawn if not already marked as standby
    if not force and not _first_request_handled:
        return
    if not ENABLE_HANDOVER and not force:
        print(f"[OMNI-SPAWN] PID={os.getpid()} Worker spawning disabled (handover disabled)")
        sys.stdout.flush()
        return
    if _worker_spawned:
        return
    _worker_spawned = True
    # Create worker starting coordination lock before spawning
    create_worker_starting_lock(PORT)
    # Spawn child with STANDBY_ENV=1 so it doesn't spawn again
    env = os.environ.copy()
    print(f"[OMNI-{SERVICE_ID}] Spawning standby process on same port {PORT}...")
    try:
        subprocess.Popen([sys.executable, __file__, '--port', str(PORT)], env=env)
    except Exception as e:
        print(f"[OMNI-ERROR] PID={os.getpid()} Failed to spawn worker: {e}")
        cleanup_worker_starting_lock(PORT)  # Clean up lock if spawn failed
        sys.stdout.flush()
        raise


# -----------------------
# App initialization
# -----------------------
async def init_app() -> web.Application:
    app = web.Application()
    app.router.add_get('/health', health_handler)
    app.router.add_post('/process', process_handler)
    return app


async def run_server(port: int):
    global _listener_sock, _runner, _site

    import sys

    print(f"[OMNI-WORKER] PID={os.getpid()} After flush, about to check lock logic...")
    sys.stdout.flush()

    # Only active workers check for existing workers and create lock files
    lock_file = f"/tmp/omniparser_healthy_{port}.lock"
    print(f"[OMNI-WORKER] PID={os.getpid()} Lock file path: {lock_file}")
    sys.stdout.flush()

    if os.path.exists(lock_file):
        print(f"[OMNI-WORKER] PID={os.getpid()} Lock file exists, exiting")
        sys.stdout.flush()
        os._exit(0)

    # Create lock file
    with open(lock_file, 'x') as f:
        f.write(str(os.getpid()))

    def remove_lock():
        try:
            os.remove(lock_file)
        except Exception:
            pass

    try:
        print("[OMNI-WORKER] Starting init_app()...")
        sys.stdout.flush()
        app = await init_app()
        print("[OMNI-WORKER] init_app() completed")
        sys.stdout.flush()
        print(f"[OMNI-WORKER] PID={os.getpid()} Creating app runner...")
        sys.stdout.flush()
        _runner = web.AppRunner(app)
        await _runner.setup()
        print(f"[OMNI-WORKER] PID={os.getpid()} Creating TCP site directly (no custom socket)...")
        sys.stdout.flush()
        _site = web.TCPSite(_runner, HOST, port, reuse_address=True, reuse_port=True)
        print(f"[OMNI-WORKER] PID={os.getpid()} Starting site (this may hang)...")
        sys.stdout.flush()
        await _site.start()
        handover_mode = "ENABLED (one-request-per-worker)" if ENABLE_HANDOVER else "DISABLED (persistent worker)"
        print(f"[OMNI-{SERVICE_ID}] Listening on http://{HOST}:{port} PID={os.getpid()} REUSEPORT=ON HANDOVER={handover_mode}")
        sys.stdout.flush()
        # Preload models promptly (but don't block listener)
        models_task = asyncio.create_task(load_models_once())

        # Wait for models to load, then signal worker is ready
        await models_task
        remove_worker_starting_lock(port)
        print(f"[OMNI-{SERVICE_ID}] Worker fully ready and accepting requests PID={os.getpid()}")
        sys.stdout.flush()

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    except Exception as e:
        print(f"[OMNI-ERROR] PID={os.getpid()} Worker startup failed: {e}")
        sys.stdout.flush()
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        startup_failed = True
    finally:
        if ENABLE_HANDOVER:
            await spawn_worker_if_needed(force=True)
        remove_lock()
        cleanup_worker_starting_lock(port)  # Clean up coordination lock
        # Exit after cleanup if startup failed
        if 'startup_failed' in locals():
            os._exit(1)

# -----------------------
# Keepalive (for cron)
# -----------------------


def is_port_healthy(port: int, timeout: float = 0.5) -> bool:
    # Check for worker lock file first (fast)
    if os.path.exists(f"/tmp/omniparser_healthy_{port}.lock"):
        return True

    # Port check (slower)
    try:
        with socket.create_connection((HOST, port), timeout=timeout):
            return True
    except Exception:
        return False


def start_daemon(port: int):
    env = os.environ.copy()
    # Inherit stdout/stderr so we can see worker output
    subprocess.Popen([sys.executable, __file__, '--port', str(port)], env=env, stdout=None, stderr=None)  # Inherit parent's stdout/stderr
    print(f"[OMNI-KEEPALIVE] PID={os.getpid()} Started worker on port {port}")


# -----------------------
# Entrypoint
# -----------------------
async def main_async(port: int):
    print(f"[OMNI-MAIN] PID={os.getpid()} main_async called for port {port}")
    sys.stdout.flush()

    try:
        await run_server(port)
    except Exception as e:
        print(f"[OMNI-ERROR] PID={os.getpid()} run_server failed: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        raise


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=PORT)
    parser.add_argument('--keepalive', action='store_true', help='Cron-friendly: ensure a worker is running, else start and exit')
    args = parser.parse_args()

    print(f"[OMNI-MAIN] PID={os.getpid()} main() called with port={args.port}, keepalive={args.keepalive}")
    import sys
    sys.stdout.flush()

    if args.keepalive:
        # Cron calls: if worker is already listening, exit; else start a background worker
        if is_port_healthy(args.port):
            print(f"[OMNI-KEEPALIVE] PID={os.getpid()} Worker already running on port {args.port}")
            return

        # Create keepalive lock to prevent multiple keepalive processes
        keepalive_lock = f"/tmp/omniparser_keepalive_{args.port}.lock"
        if os.path.exists(keepalive_lock):
            print(f"[OMNI-KEEPALIVE] PID={os.getpid()} Keepalive lock file exists, exiting")
            return

        try:
            with open(keepalive_lock, 'x') as f:
                f.write(str(os.getpid()))

            try:
                start_daemon(args.port)
            finally:
                try:
                    os.remove(keepalive_lock)
                except Exception:
                    pass

        except FileExistsError:
            print(f"[OMNI-KEEPALIVE] PID={os.getpid()} Another keepalive is already starting worker on port {args.port}")
            return

        return

    print(f"[OMNI-DEBUG] PID={os.getpid()} About to start main server...")
    sys.stdout.flush()
    print(f"[OMNI-MAIN] PID={os.getpid()} Starting main server (non-keepalive) on port {args.port}")
    sys.stdout.flush()
    try:
        asyncio.run(main_async(args.port))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[OMNI-ERROR] PID={os.getpid()} main_async failed: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
    finally:
        if ENABLE_HANDOVER:
            asyncio.run(spawn_worker_if_needed(force=True))


if __name__ == '__main__':
    print(f"[OMNI-CONFIG] PID={os.getpid()} ENABLE_HANDOVER={ENABLE_HANDOVER}")
    sys.stdout.flush()

    # install signal handler to clean up lock files
    def signal_handler(signum, frame):
        print(f"[OMNI-DEBUG] PID={os.getpid()} Signal {signum} received, cleaning up lock files")
        sys.stdout.flush()
        try:
            os.remove(f"/tmp/omniparser_healthy_{PORT}.lock")
            os.remove(f"/tmp/omniparser_keepalive_{PORT}.lock")
            cleanup_worker_starting_lock(PORT)  # Clean up coordination lock
        except Exception:
            pass
        # Exit process; standby (already bound) continues serving
        os._exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    # Note: SIGKILL and SIGSEGV cannot be handled
    try:
        signal.signal(signal.SIGABRT, signal_handler)
    except (OSError, ValueError):
        pass  # Some signals may not be available on all platforms

    print(f"[OMNI-DEBUG] PID={os.getpid()} Script started with args: {sys.argv}")
    sys.stdout.flush()
    main()
