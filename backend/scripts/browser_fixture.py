from pathlib import Path
import struct
from backend import media

folder = Path('artifacts').resolve()
folder.mkdir(exist_ok=True)
media.run(['-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=15', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000', '-t', '3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(folder / 'browser-fixture.mp4')])
# A valid MP4 free-space box makes the real upload cross Next.js's old 10 MiB
# truncation boundary without requiring a long, expensive test video.
fixture = folder / 'browser-fixture.mp4'
target_size = 12 * 1024**2
padding = target_size - fixture.stat().st_size
if padding >= 8:
    with fixture.open('ab') as file:
        file.write(struct.pack('>I4s', padding, b'free'))
        file.write(bytes(padding - 8))
