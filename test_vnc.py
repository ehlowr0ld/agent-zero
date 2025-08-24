import asyncio
import asyncvnc2

async def debug_coordinate_system():
    async with asyncvnc2.connect('localhost', 5900, '', 'changeme') as client:
        print(f"🖥️ [VNC-ANALYSIS] Screen Analysis:")
        print(f"   VNC reports screen size: {client.video.width}x{client.video.height}")
        print(f"   OmniParser analyzed at: 1024x1024")

        # Calculate scaling factors
        scale_x = client.video.width / 1024
        scale_y = client.video.height / 1024

        print(f"   Required scaling: X={scale_x:.3f}, Y={scale_y:.3f}")

        if scale_x != 1.0 or scale_y != 1.0:
            print(f"🚨 FOUND THE BUG! Screen size mismatch!")
            print(f"   Your clicks need to be scaled by these factors")

        # Test with your actual OmniParser coordinates
        test_omni_coords = [0.876953125, 0.00390625, 0.046875, 0.025390625]  # "23.58" text
        x, y, w, h = test_omni_coords

        # Calculate click center
        click_x_omni = (x + w/2) * 1024
        click_y_omni = (y + h/2) * 1024

        # Scale to VNC coordinates
        click_x_vnc = click_x_omni * scale_x
        click_y_vnc = click_y_omni * scale_y

        print(f"   Example transformation:")
        print(f"   OmniParser click: ({click_x_omni:.1f}, {click_y_omni:.1f})")
        print(f"   VNC click should be: ({click_x_vnc:.1f}, {click_y_vnc:.1f})")

        # Test the actual mouse movement
        client.mouse.move(click_x_vnc, click_y_vnc)
        print(f"   VNC mouse moved to: ({client.mouse.x}, {client.mouse.y})")

asyncio.run(debug_coordinate_system())
