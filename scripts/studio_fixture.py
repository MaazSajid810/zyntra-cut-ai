from pathlib import Path
from PIL import Image,ImageDraw
from backend import media

root=Path('artifacts').resolve();root.mkdir(exist_ok=True)
image=Image.new('RGBA',(160,80),(0,0,0,0))
draw=ImageDraw.Draw(image);draw.rounded_rectangle((0,0,159,79),12,fill=(193,245,74,255));draw.text((18,30),'MY CHANNEL',fill=(0,0,0,255))
image.save(root/'studio-logo.png')
media.run(['-f','lavfi','-i','color=c=0x972eb5:s=320x180:r=15','-t','1','-c:v','libx264',str(root/'studio-broll.mp4')])
media.run(['-f','lavfi','-i','sine=frequency=220:sample_rate=16000:duration=1','-c:a','pcm_s16le',str(root/'studio-music.wav')])
