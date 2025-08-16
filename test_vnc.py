import asyncio, asyncvnc
from PIL import Image


async def run_client():
    async with asyncvnc.connect('127.0.0.1', 5901, 'agent-zero', 'agent0') as client:
        client.keyboard.write('hello world!')
        pixels = await client.screenshot()

        # Save as PNG using PIL/pillow
        image = Image.fromarray(pixels)
        image.save('screenshot.png')

asyncio.run(run_client())
