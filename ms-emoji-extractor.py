# A script that extracts the emojis found in a text file (one per line) or a single emoji provided as first arg
# uharfbuzz from https://stackoverflow.com/questions/55373103/python-fonttools-check-if-font-supports-multi-codepoint-emoji
# and extraction from https://github.com/faveris/glyph_extractor
import sys
from PIL import Image, ImageFont, ImageDraw
from uharfbuzz import Face, Font, Buffer, ot_font_set_funcs, shape
import operator
import os

class MsEmojiExtractor:
    def __init__(self):
        fontPath = r"seguiemj.ttf"
        self.outputDir = "output"
        if not os.path.exists(self.outputDir):
            os.makedirs(self.outputDir)
        self.size = 256
        self.imagefont = ImageFont.truetype(fontPath, self.size, layout_engine=ImageFont.Layout.BASIC)
        with open(fontPath, 'rb') as fontfile:
            self.fontdata = fontfile.read()

    def bleed(self, img):
        pixels = img.load()
        edge = set()
        width = img.size[0]
        height = img.size[1]
        for x in range(width):
            for y in range(height):
                if pixels[x, y][3] == 255:
                    for i in range(max(0, x - 1), min(x + 2, width)):
                        for j in range(max(0, y - 1), min(y + 2, height)):
                            alpha = pixels[i, j][3]
                            if alpha > 0 and alpha < 255:
                                edge.add((i, j))

        for (x, y) in edge:
            color = (0, 0, 0, 0)
            count = 0
            for i in range(max(0, x - 1), min(x + 2, width)):
                for j in range(max(0, y - 1), min(y + 2, height)):
                    if (pixels[i, j][3] == 255):
                        color = tuple(map(operator.add, color, pixels[i, j]))
                        count += 1

            if count > 0:
                color = tuple(map(operator.floordiv, color[:3], (count, count, count)))
                color = color + (255,)
                pixels[x, y] = color

        return len(edge) > 0

    def clear(self, img):
        pixels = img.load()
        width = img.size[0]
        height = img.size[1]
        for x in range(width):
            for y in range(height):
                pixels[x, y] = pixels[x, y][:3] + (0,)

    def isEmojiSupportedByFont(self, emoji: str) -> bool:
        # Load font (has to be done for call):
        face = Face(self.fontdata)
        font = Font(face)
        upem = face.upem
        font.scale = (upem, upem)
        ot_font_set_funcs(font)

        # Create text buffer:
        buf = Buffer()
        buf.add_str(emoji)
        buf.guess_segment_properties()
        infos = buf.glyph_infos

        # Shape text:
        features = {"kern": True, "liga": True}
        shape(font, buf, features)

        # Remove all variant selectors:
        while len(infos) > 0 and infos[-1].codepoint == 3:
            infos = infos[:-1]

        # Filter empty:
        if len(infos) <= 0:
            return False

        # Remove uncombined, ending with skin tone like "👭🏿":
        lastCp = infos[-1].codepoint
        if lastCp == 1076 or lastCp == 1079 or lastCp == 1082 or lastCp == 1085 or lastCp == 1088:
            return False

        # If there is a code point 0 or 3 => Emoji not fully supported by font:
        return all(info.codepoint != 0 and info.codepoint != 3 for info in infos)

    def extractPng(self, emoji: str):
        key = "-".join(map(lambda s: s.replace("0x", ""), map(str, map(hex, map(ord, emoji)))))
        filename = f"{key}.png"

        (left, top, right, bottom) = self.imagefont.getbbox(emoji)
        width = -left + right
        height = top + bottom

        print(f"L={left} T={top} R={right} B={bottom} {width}x{height}")
        if width <= 0 or height <= 0:
            print(f"{emoji} -> empty")
        else:
            try:
                img = Image.new('RGBA', size=(width, height))
                d = ImageDraw.Draw(img)

                d.text((-left, -top), emoji, font=self.imagefont, anchor="la", embedded_color=True)
                while self.bleed(img): pass
                self.clear(img)
                d.text((-left, -top), emoji, font=self.imagefont, anchor="la", embedded_color=True)

                img.save(os.path.join(self.outputDir, filename))
                print(f"{emoji} -> {filename}")
            except Exception as err:
                print(f"{emoji} -> {err}", file=sys.stderr)

if len(sys.argv) > 1:
    obj = MsEmojiExtractor()
    try:
        with open(sys.argv[1], 'r') as file:
            for line in file:
                chars = line.strip()
                isSupported = obj.isEmojiSupportedByFont(chars)
                if isSupported:
                    obj.extractPng(chars)
    except:
        chars = sys.argv[1]
        isSupported = obj.isEmojiSupportedByFont(chars)
        if isSupported:
            obj.extractPng(chars)
    #for char in chars:
    #    print(char, obj.isEmojiSupportedByFont(char))
