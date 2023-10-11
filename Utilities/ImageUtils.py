from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont  # Import PIL functions


class Template:  # Your template
    thumb_dim = 150
    title_y_pos = 170

    def __init__(self, titles, images):
        self.titles = titles
        self.images = images  # Array of BytesIO objects from url request.content

    def draw(self):
        img = Image.new(mode="RGBA", size=(1040, 200))
        font = ImageFont.truetype("arial.ttf", 20)  # Loads font
        imgdraw = ImageDraw.Draw(img)  # Create a canvas
        buffer = 20
        x_pos = 20
        y_pos = 20
        for index, image_ in enumerate(self.images):
            pasted = Image.open(image_).convert("RGBA")  # Opens Selected Image
            pasted = pasted.resize((self.thumb_dim, int(pasted.size[1] * (self.thumb_dim / pasted.size[0]))))
            pasted = pasted.crop((0, 0, self.thumb_dim, self.thumb_dim))
            img.paste(pasted, (x_pos, y_pos))
            imgdraw.text((x_pos, self.title_y_pos),
                         f"[{index + 1}]{self.titles[index][:12]}..." if len(self.titles[index]) > 11
                         else f"[{index + 1}]{self.titles[index]}", (255, 255, 255, 255),
                         font=font, stroke_fill='black', stroke_width=2)
            x_pos += self.thumb_dim + buffer
        return img

    def write(self):
        img = Image.new(mode="RGBA", size=(1040, 200))
        font = ImageFont.truetype("arial.ttf", 20)  # Loads font
        imgdraw = ImageDraw.Draw(img)  # Create a canvas
        buffer = 20
        x_pos = 20
        y_pos = 20
        for index, image_ in enumerate(self.images):
            pasted = Image.new(mode="RGB", size=(150, 150))  # Opens Selected Image
            text_draw = ImageDraw.Draw(pasted)
            text_draw.text((0, 0), image_['content'][:20], (0, 0, 0), font=ImageFont.truetype("arial.ttf", 10))
            img.paste(pasted, (x_pos, y_pos))
            imgdraw.text((x_pos, self.title_y_pos),
                         f"[{index + 1}]{self.titles[index][:12]}..." if len(self.titles[index]) > 11
                         else f"[{index + 1}]{self.titles[index]}", (255, 255, 255, 255),
                         font=font, stroke_fill='black', stroke_width=2)
            x_pos += self.thumb_dim + buffer
        return img
