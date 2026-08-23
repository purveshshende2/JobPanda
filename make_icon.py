"""Generate the JobPanda favicon (panda face) - run once."""
from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

BLACK = (34, 34, 40, 255)
WHITE = (250, 250, 250, 255)

# ears
d.ellipse([8, 8, 88, 88], fill=BLACK)
d.ellipse([168, 8, 248, 88], fill=BLACK)

# head
d.ellipse([28, 30, 228, 230], fill=WHITE, outline=BLACK, width=6)

# eye patches (angled)
d.ellipse([62, 92, 126, 168], fill=BLACK)
d.ellipse([130, 92, 194, 168], fill=BLACK)

# eyes
d.ellipse([86, 116, 104, 138], fill=WHITE)
d.ellipse([152, 116, 170, 138], fill=WHITE)
d.ellipse([91, 121, 101, 133], fill=(20, 20, 24, 255))
d.ellipse([157, 121, 167, 133], fill=(20, 20, 24, 255))

# nose + mouth
d.ellipse([114, 172, 142, 192], fill=BLACK)
d.arc([106, 186, 128, 206], start=0, end=110, fill=BLACK, width=5)
d.arc([128, 186, 150, 206], start=70, end=180, fill=BLACK, width=5)

# bamboo accent
BAMBOO = (76, 160, 90, 255)
d.rounded_rectangle([226, 120, 244, 236], radius=9, fill=BAMBOO)
for y in (150, 190):
    d.line([226, y, 244, y], fill=(46, 120, 60, 255), width=5)
d.ellipse([214, 96, 254, 132], fill=BAMBOO)

img.save("assets/panda.png")
print("saved assets/panda.png")
