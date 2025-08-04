from io import BytesIO
from PIL import Image, ImageDraw, ImageFont  # Import PIL functions
from sqlalchemy.engine import RowMapping

from thumbhubbot import CONFIG


class Template:  # Your template
    thumb_dim = 150
    title_y_pos = 170

    def __init__(self, titles, images):
        self.titles = titles
        self.images = images  # Array of BytesIO objects from url request.content and results dictionaries

    def draw(self):
        img = Image.new(mode="RGBA", size=(1040, 200))
        font = ImageFont.truetype(CONFIG.font, 20)  # Loads font
        imgdraw = ImageDraw.Draw(img)  # Create a canvas
        buffer = 20
        x_pos = 20
        y_pos = 20
        for index, thumb in enumerate(self.images):
            if isinstance(thumb, BytesIO):
                self._image_thumb(thumb, x_pos, y_pos, img)
            elif type(thumb) == RowMapping or type(thumb) == dict:
                self._text_thumb(thumb, x_pos, y_pos, img)

            imgdraw.text((x_pos, self.title_y_pos),
                         f"[{index + 1}]{self.titles[index][:12]}..." if len(self.titles[index]) > 11
                         else f"[{index + 1}]{self.titles[index]}", (255, 255, 255, 255),
                         font=font, stroke_fill='black', stroke_width=2)
            x_pos += self.thumb_dim + buffer
        return img

    def _text_thumb(self, clip, x_pos, y_pos, img):
        pasted = Image.new(mode="RGB", size=(150, 150))  # Opens Selected Image
        text_draw = ImageDraw.Draw(pasted)
        wrapped_text = self._get_wrapped_text(f"{clip['src_snippet'][:190]}...",
                                              ImageFont.truetype(CONFIG.font, 12), 130)
        text_draw.text((10, 10), wrapped_text, (255, 255, 255),
                       font=ImageFont.truetype(CONFIG.font, 12))
        img.paste(self._gradient(pasted), (x_pos, y_pos))

    def _image_thumb(self, clip, x_pos, y_pos, img):
        pasted = Image.open(clip).convert("RGBA")  # Opens Selected Image
        pasted = pasted.resize((self.thumb_dim, int(pasted.size[1] * (self.thumb_dim / pasted.size[0]))))
        pasted = pasted.crop((0, 0, self.thumb_dim, self.thumb_dim))
        img.paste(pasted, (x_pos, y_pos))

    @staticmethod
    def _gradient(im):
        w, h = 150, 150
        alpha = Image.linear_gradient('L').rotate(-180).resize((w, h))
        im.putalpha(alpha)
        return im

    @staticmethod
    def _get_wrapped_text(text: str, font: ImageFont.ImageFont,
                          line_length: int):
        lines = ['']
        for word in text.split():
            line = f'{lines[-1]} {word}'.strip()
            if font.getlength(line) <= line_length:
                lines[-1] = line
            else:
                lines.append(word)
        return '\n'.join(lines)
