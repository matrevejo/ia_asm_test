from PIL import Image
import numpy as np

# Load makon image
im = Image.open(r'c:\Users\oscar\IA life simulator\Assets\Resources\Creatures\makon_front_idle.png').convert('RGBA')
bbox = im.getbbox()
im_cropped = im.crop(bbox)
im_cropped.thumbnail((32, 32), Image.Resampling.LANCZOS)
final_im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
offset = ((32 - im_cropped.width) // 2, (32 - im_cropped.height) // 2)
final_im.paste(im_cropped, offset)

arr = np.array(final_im)
pixels = np.zeros((32, 32), dtype=int)
for y in range(32):
    for x in range(32):
        r, g, b, a = arr[y, x]
        if a < 100:
            c = 0
        else:
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            if gray < 80:
                c = 1
            elif gray < 165:
                c = 2
            else:
                c = 3
        pixels[y, x] = c

def get_lines(x_start):
    res = []
    for y in range(32):
        p0 = 0
        p1 = 0
        for bit in range(16):
            c = pixels[y, x_start + bit]
            shift = 15 - bit
            if c & 1:
                p0 |= (1 << shift)
            if c & 2:
                p1 |= (1 << shift)
        res.append((p0, p1))
    return res

spr0 = get_lines(0)
spr1 = get_lines(16)

with open('hd/code/makon_data.i', 'w') as f:
    f.write('; Makon Sprite 0 (Left 16x32)\n')
    for y, (p0, p1) in enumerate(spr0):
        f.write(f'\t\tdc.w\t${p0:04x},${p1:04x}\t; Line {y:02d}\n')
    f.write('\n; Makon Sprite 1 (Right 16x32)\n')
    for y, (p0, p1) in enumerate(spr1):
        f.write(f'\t\tdc.w\t${p0:04x},${p1:04x}\t; Line {y:02d}\n')

print('Conversion complete! Written to hd/code/makon_data.i')
