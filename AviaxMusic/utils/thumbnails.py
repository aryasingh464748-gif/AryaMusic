import os
import aiohttp
import textwrap
import math
from PIL import (Image, ImageDraw, ImageEnhance,
                 ImageFilter, ImageFont, ImageOps)

# Mocking internal imports for the structure - keep your original ones
# from anony import config
# from anony.helpers import Track

class Thumbnail:
    def __init__(self):
        # Colors & Styling
        self.accent_color = (255, 255, 255, 255)
        self.glass_color = (0, 0, 0, 80) # Semi-transparent black
        self.progress_bg = (255, 255, 255, 60)
        
        # Load Fonts (Adjust paths as needed)
        self.font_title = ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 45)
        self.font_artist = ImageFont.truetype("anony/helpers/Inter-Light.ttf", 30)
        self.font_small = ImageFont.truetype("anony/helpers/Inter-Light.ttf", 22)

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
            return output_path

    def draw_rounded_rect(self, draw, coords, radius, fill):
        draw.rounded_rectangle(coords, radius=radius, fill=fill)

    def draw_icons(self, draw, center_y, width):
        """Draws the aesthetic UI icons: Star, Rewind, Play, FastForward, Earphones"""
        cx = width // 2
        # Play/Pause Icon
        draw.rounded_rectangle([cx - 5, center_y - 20, cx + 5, center_y + 20], radius=5, fill="white")
        draw.rounded_rectangle([cx - 20, center_y - 20, cx - 10, center_y + 20], radius=5, fill="white")
        draw.rounded_rectangle([cx + 10, center_y - 20, cx + 20, center_y + 20], radius=5, fill="white")

        # Rewind/Forward (Simple triangles)
        draw.polygon([(cx - 70, center_y), (cx - 50, center_y - 15), (cx - 50, center_y + 15)], fill="white")
        draw.polygon([(cx - 90, center_y), (cx - 70, center_y - 15), (cx - 70, center_y + 15)], fill="white")
        draw.polygon([(cx + 70, center_y), (cx + 50, center_y - 15), (cx + 50, center_y + 15)], fill="white")
        draw.polygon([(cx + 90, center_y), (cx + 70, center_y - 15), (cx + 70, center_y + 15)], fill="white")

        # Star (Left)
        draw.text((cx - 250, center_y - 20), "⭐", font=self.font_title, fill="white", anchor="mm")
        # Earphones (Right)
        draw.text((cx + 250, center_y - 20), "🎧", font=self.font_title, fill="white", anchor="mm")

    async def generate(self, song, size=(1280, 720)) -> str:
        try:
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}.png"
            
            # Ensure cache dir exists
            os.makedirs("cache", exist_ok=True)
            await self.save_thumb(temp, song.thumbnail)

            # 1. Background (Blurred & Darkened)
            original = Image.open(temp).convert("RGBA")
            bg = original.resize(size, Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(25))
            bg = ImageEnhance.Brightness(bg).enhance(0.7)

            # 2. Create the Glass Panel
            panel_w, panel_h = 800, 450
            px1, py1 = (size[0] - panel_w) // 2, (size[1] - panel_h) // 2
            px2, py2 = px1 + panel_w, py1 + panel_h

            # Crop bg for the blur effect inside the panel
            mask = Image.new("L", size, 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.rounded_rectangle([px1, py1, px2, py2], radius=40, fill=255)
            
            panel_content = bg.filter(ImageFilter.BoxBlur(20))
            bg.paste(panel_content, (0, 0), mask)
            
            # Draw the semi-transparent overlay
            overlay = Image.new("RGBA", size, (0, 0, 0, 0))
            draw_ov = ImageDraw.Draw(overlay)
            draw_ov.rounded_rectangle([px1, py1, px2, py2], radius=40, fill=self.glass_color)
            bg = Image.alpha_composite(bg, overlay)

            # 3. Album Art (Left Side of Panel)
            art_size = 220
            art_x, art_y = px1 + 50, py1 + 50
            album_art = ImageOps.fit(original, (art_size, art_size), centering=(0.5, 0.5))
            
            # Round the album art corners
            art_mask = Image.new("L", (art_size, art_size), 0)
            ImageDraw.Draw(art_mask).rounded_rectangle([0, 0, art_size, art_size], radius=20, fill=255)
            bg.paste(album_art, (art_x, art_y), art_mask)

            # 4. Text (Title & Artist)
            draw = ImageDraw.Draw(bg)
            text_x = art_x + art_size + 30
            
            # Bot Name / Header
            draw.text((text_x, py1 + 80), "Jerry Bots", font=self.font_small, fill=(200, 200, 200))
            
            # Song Title (Wrapped)
            title = song.title[:35] + "..." if len(song.title) > 35 else song.title
            draw.text((text_x, py1 + 115), title, font=self.font_title, fill="white")
            
            # Artist Name
            draw.text((text_x, py1 + 175), "Aashiq Awara", font=self.font_artist, fill=(200, 200, 200))

            # 5. Seekbar (Duration Line)
            bar_y = py1 + 320
            bar_start, bar_end = px1 + 70, px2 - 70
            
            # Bar Background
            draw.rounded_rectangle([bar_start, bar_y, bar_end, bar_y + 6], radius=3, fill=self.progress_bg)
            # Bar Progress (Static 30% for aesthetic)
            progress_end = bar_start + (bar_end - bar_start) * 0.3
            draw.rounded_rectangle([bar_start, bar_y, progress_end, bar_y + 6], radius=3, fill="white")
            
            # Time Labels
            draw.text((bar_start - 10, bar_y - 15), "0:24", font=self.font_small, fill="white", anchor="rm")
            draw.text((bar_end + 10, bar_y - 15), f"- {song.duration}", font=self.font_small, fill="white", anchor="lm")

            # 6. Icons (Star, Play, Earphones)
            self.draw_icons(draw, py1 + 385, size[0])

            bg.convert("RGB").save(output)
            os.remove(temp)
            return output
        except Exception as e:
            print(f"Error: {e}")
            return "default_thumb.png"
