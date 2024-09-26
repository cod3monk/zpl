#!/usr/bin/env python

from __future__ import division
from __future__ import print_function

#import Image
from PIL import Image
import re
import PIL.ImageOps
import sys
import math
import webbrowser
import os.path
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
import io

class Label:
    """
    Used to build a ZPL2 label.

    All dimensions are given in millimeters and automatically converted to
    printer dot units.
    """

    def __init__(self, height, width=110.0, dpmm=12.0):
        """
        Creates one (or more) ZPL2 labels.

        *height* and *width* are given in millimeters
        *dpmm* refers to dots per millimeter (e.g. 12 for 300dpi)
        """
        self.height = height
        self.width = width
        self.dpmm = dpmm

        self.code = "^XA"
        self.code += "^PW%i" % (width*dpmm)
        self.code += "^LL%i" % (height*dpmm)

    def labelhome(self, x, y, justification=None):
        """
        Set label home at x and y (in millimeters).
        Justification is 0 for left, 1 for right, and 2 for auto.
        """
        self.code += "^LH%i,%i" % (x*self.dpmm, y*self.dpmm)
        if justification != None:
            assert justification in '012', "invalid justification"
            self.code += ',' + justification

    def origin(self, x, y, justification=None):
        """
        New block located at x and y (in millimeters).
        Justification is 0 for left, 1 for right, and 2 for auto.
        """
        self.code += "^FO%i,%i" % (x*self.dpmm, y*self.dpmm)
        if justification != None:
            assert justification in '012', "invalid justification"
            self.code += ',' + justification

    def endorigin(self):
        """
        Marks the end of a block started by the origin function.
        """
        self.code += '^FS'
    
    def set_darkness(self, value):
        """
        Sets the darkness of the printed label. The value input is integer between 0 - 30,
        which corresponds to (no darkness 0) or (full darkness 30).
        """
        assert (isinstance(value, int)), "The value must be an integer"
        
        assert (value >= 0 and value <= 30), "The value must be between 0 and 30"
        self.code += "~SD" + str(value)

    def zpl_raw(self, commands):
        """
        Send raw ZPL commands to the printer.
        """
        self.code += commands

    def textblock(self, width, justification='C', lines=1):
        """
        New text block.
        Makes the next text command bound by this block's parameters.
        Note: Does not work with write_text as it already has creates its own text block.

        *width* of textblock in millimeters.
        *justification* is 'L' for left, 'R' for right, 'C' for center, or 'J' for justified.
        *lines* is the maximum number of lines to write.
        """
        assert justification in ['L','R','C','J']
        self.code += "^FB%i,%i,%i,%s,%i" % (width*self.dpmm, lines, 0, justification, 0)

    def write_text(self, text, char_height=None, char_width=None, font='0', orientation='N',
                   line_width=None, max_line=1, line_spaces=0, justification='L', hanging_indent=0, qrcode=False):
        if char_height and char_width and font and orientation:
            assert orientation in 'NRIB', "invalid orientation"
            if re.match(r'^[A-Z0-9]$', font):
                self.code += "^A%c%c,%i,%i" % (font, orientation, char_height*self.dpmm,
                                               char_width*self.dpmm)
            elif re.match(r'[REBA]?:[A-Z0-9\_]+\.(FNT|TTF|TTE)', font):
                self.code += "^A@%c,%i,%i,%s" % (orientation, char_height*self.dpmm,
                                               char_width*self.dpmm, font)
            else:
                raise ValueError("Invalid font.")
        if line_width:
            assert justification in "LCRJ", "invalid justification"
            self.code += "^FB%i,%i,%i,%c,%i" % (line_width*self.dpmm, max_line, line_spaces,
                                                justification, hanging_indent)
        if qrcode:
            self.code += "^FDQA,%s" % text
        else:
            self.code += "^FD%s" % text
        
        if justification == 'C':
            self.code += "\&"

    def set_default_font(self, height, width, font='0'):
        """
        Sets the default font from here onward.

        *height* and *width* are given in millimeters.
        """
        assert re.match(r'[A-Z0-9]', font), "invalid font"
        self.code += "^CF%c,%i,%i" % (font, height*self.dpmm, width*self.dpmm)

    def change_international_font(self, character_set=28, remaps=[]):
        """
        Change the international font/encoding, that enables you to call
        up the international character set you want to use for printing

        *character_set* is an int representing a character set.
        As described in the ZPL2 programming guide under the "Change International Font/Encoding" section.
        character_set=28 is UTF-8.
        *remaps* arg is a list of tuples with the number of the source
        character and the substitute character destination.
        May only work on certain character sets.
        Ex: remaps=[(65, 97), (66, 98)] remaps 'A' (65) to 'a' (97) and 'B' (66) to 'b' (98)
        """
        ci_code = '^CI%i' % (character_set)

        charset_regex_range = "(3[0-6]|[12]?[0-9])"  # Matches 0 to 36
        range_regex = "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"  # Matches 0 to 255
        ci_regex = r"^\^CI%s((\,%s,%s){1,})*$" % (
            charset_regex_range, range_regex, range_regex)

        for src, dest in remaps:
            ci_code += ',%i,%i' % (src, dest)

        assert re.match(ci_regex, ci_code), "invalid character set"
        self.code += ci_code

    def _convert_image(self, image, width, height, compression_type='A'):
        """
        converts *image* (of type PIL.Image) to a ZPL2 format

        compression_type can be one of ['A', 'B', 'C']

        returns data
        """
        image = image.resize((int(width*self.dpmm), int(height*self.dpmm)), PIL.Image.NEAREST)
        # invert, otherwise we get reversed B/W
        # https://stackoverflow.com/a/38378828
        image = PIL.ImageOps.invert(image.convert('L')).convert('1')

        if compression_type == "A":
            # return image.tobytes().encode('hex').upper()
            return image.tobytes().hex().upper()
        # TODO this is not working
        #elif compression_type == "B":
        #    return image.tostring()
        else:
            raise Exception("unsupported compression type")

    def upload_graphic(self, name, image, width, height=0):
        """
        Uploads an image which can be recalled and placed with print_graphic.

        *image* is a type PIL.Image
        *name* is the given name of the image. If not specified, "UNKNOWN" is used.
        A name can only be used once. A second image of the same name will overwrite the previous image.
        Don't use spaces or periods.
        *width* and *height* in millimeters.
        """
        if not height:
            height = int(float(image.size[1])/image.size[0]*width)

        assert 1 <= len(name) <= 8, "filename must have length [1:8]"

        totalbytes = math.ceil(width*self.dpmm/8.0)*height*self.dpmm
        bytesperrow = math.ceil(width*self.dpmm/8.0)

        data = self._convert_image(image, width, height)

        self.code += "~DG%s.GRF,%i,%i,%s" % (name, totalbytes, bytesperrow, data)

        return height

    def write_graphic(self, image, width, height=0, compression_type="A"):
        """
        Embeds image with given width.

        *image* has to be of type PIL.Image.
        If height is not given, it will be chosen proportionally
        """
        if not height:
            height = int(float(image.size[1])/image.size[0]*width)

        totalbytes = math.ceil(width*self.dpmm/8.0)*height*self.dpmm
        bytesperrow = math.ceil(width*self.dpmm/8.0)

        data = self._convert_image(image, width, height, compression_type=compression_type)

        if compression_type == "A":
            self.code += "^GFA,%i,%i,%i,%s" % (len(data), totalbytes, bytesperrow, data)
        # TODO this is not working:
        elif compression_type == "B":
            self.code += "^GFB,%i,%i,%i,%s" % (len(data), totalbytes, bytesperrow, data)
        else:
            raise Exception("Unsupported compression type.")

        return height

    def draw_box(self, width, height, thickness=1, color='B', rounding=0):
        """
        Draws a box.

        *width* and *height* in dots.
        *color* can be "B" or "W"
        *rounding* rounds corners. Int between 0 - 8.
        """
        assert color in 'BW', "invalid color"
        assert rounding <= 8, "invalid rounding"
        self.code += "^GB%i,%i,%i,%c,%i" % (width, height, thickness, color, rounding)

    def draw_ellipse(self, width, height, thickness=1, color='B'):
        """
        Draws an ellipse.

        *width* and *height* in dots.
        *color* can be either "B" or "W"
        """
        assert color in 'BW', "invalid color"
        self.code += "^GE%i,%i,%i,%c" % (width, height, thickness, color)

    def print_graphic(self, name, scale_x=1, scale_y=1):
        """
        Prints a preloaded image by name uploaded by upload_graphic.
        """
        self.code += "^XG%s,%i,%i" % (name, scale_x, scale_y)

    def reverse_print(self, active='Y'):
        """
        When active, allows a field to appear as white over black or black over white.

        *active* can be 'Y' for enabled and 'N' for disabled.
        """
        assert active in ['Y', 'N'], "invalid parameter"
        self.code += "^LR%s" % active

    def run_script(self, filename):
        """Run script previously loaded by saveFormat.

        *filename* is the name referenced in saveFormat"""
        self.code += "^XF%s^FS"

    def write_field_number(self, number, name=None, char_height=None, char_width=None, font='0',
                           orientation='N', line_width=None, max_line=1, line_spaces=0,
                           justification='L', hanging_indent=0):
        """
        Declare a field identified by a number that can be filled in with text later.
        """
        if char_height and char_width and font and orientation:
            assert re.match(r'[A-Z0-9]', font), "invalid font"
            assert orientation in 'NRIB', "invalid orientation"
            self.code += "^A%c%c,%i,%i" % (font, orientation, char_height*self.dpmm,
                                           char_width*self.dpmm)
        if line_width:
            assert justification in "LCRJ", "invalid justification"
            self.code += "^FB%i,%i,%i,%c,%i" % (line_width*self.dpmm, max_line, line_spaces,
                                                justification, hanging_indent)
        self.code += "^FN%i" % number
        if name:
            assert re.match("^[a-zA-Z0-9 ]+$", name), "name may only contain alphanumerical " + \
                "characters and spaces"
            self.code += '"%s"' % name

    def barcode_field_default(self, module_width, bar_width_ratio, height):
        """
        Changes the default values of the barcode *module_width*, *bar_width_ratio*, and *height* in millimeters.
        """
        self.code += '^BY%s,%s,%s' % (module_width * self.dpmm,
                                      bar_width_ratio,
                                      height * self.dpmm)

    def field_orientation(self, orientation, justification=None):
        """
        Sets default field orientation, and optionally, justification.
        *justification* is 0 for left, 1 for right, and 2 for auto
        """
        assert orientation in 'NRIB', "invalid orientation"
        self.code += '^FW%s' % orientation
        if justification != None:
            assert justification in '012', "invalid justification"
            self.code += ',' + justification


    def _barcode_config(self,height, barcode_type, orientation, check_digit,
                       print_interpretation_line, print_interpretation_line_above,
                       magnification, errorCorrection, mask, mode):
        # TODO split into multiple functions?
        # TODO support all ^B barcode types

        if barcode_type in '2A':
            barcode_zpl = '^B{barcode_type}{orientation},{height:d},{print_interpretation_line},' \
                            '{print_interpretation_line_above},{check_digit}'.format(**locals())
        
        elif barcode_type == '3':
            barcode_zpl = '^B{barcode_type}{orientation},{check_digit},{height:d},{print_interpretation_line},' \
                            '{print_interpretation_line_above}'.format(**locals())
        
        #QR code
        elif barcode_type == 'Q':
            assert orientation == 'N', 'QR Code orientation may only be N'
            model = 2  # enchanced model, always recommended according to ZPL II documentation
            assert magnification in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                     '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'], \
                'QR Code maginification may be 1 - 10.'
            assert errorCorrection in 'HQML', 'QR Code errorCorrection may be H (more reliable, ' \
                'less dense), Q, M or L (less reliable, more dense).'
            assert mask in [1, 2, 3, 4, 5, 6, 7, '1', '2', '3', '4', '5', '6', '7'], \
                'QR Code mask may be 1 - 7.'
            barcode_zpl = '^B{barcode_type}{orientation},{model},{magnification},{errorCorrection},{mask}'.format(**locals())
        
        elif barcode_type == 'U':
            barcode_zpl = '^B{barcode_type}{orientation},{height:d},{print_interpretation_line},' \
                            '{print_interpretation_line_above},{check_digit}'.format(**locals())
        
        elif barcode_type == 'C':
            barcode_zpl = '^B{barcode_type}{orientation},{height:d},{print_interpretation_line},' \
                            '{print_interpretation_line_above},{check_digit},{mode}'.format(**locals())
        
        elif barcode_type == 'E':
            barcode_zpl = '^B{barcode_type}{orientation},{height:d},{print_interpretation_line},' \
                            '{print_interpretation_line_above}'.format(**locals())
        
        elif barcode_type == 'X':
            barcode_zpl = '^B{barcode_type}{orientation},{height:d},200'.format(**locals())

        return barcode_zpl



    def write_barcode(self, height, barcode_type, orientation='N', check_digit='N',
                       print_interpretation_line='Y', print_interpretation_line_above='N',
                       magnification=1, errorCorrection='Q', mask='7', mode='N'):

        print('The write_barcode() function is kept for backward compatibility, it is recommended to use the barcode() function instead.')

        # guard for only currently allowed bar codes
        assert barcode_type in '23AQUCEX', "invalid barcode type"


        self.code += self._barcode_config(height, barcode_type, orientation, check_digit, \
            print_interpretation_line, print_interpretation_line_above, magnification, errorCorrection, mask, mode)


    def barcode(self, barcode_type, code, height=70, orientation='N', check_digit='N',
                       print_interpretation_line='Y', print_interpretation_line_above='N',
                       magnification=1, errorCorrection='Q', mask='7', mode='N'):
        """
        Creates a barcode of selected type

        *barcode_type*
        '2': Interleaved 2 of 5 Bar Code
        '3': Code 39 Bar Code
        'Q': QR Code Bar Code
        'U': UPC-A Bar Code
        'C': Code 128 Bar Code (*mode* can be 'N' = No mode, 'U' = UCC Case Mode, 'A' = Automatic Mode, 'D' = UCC/EAN Mode)
        'E': EAN-13 Bar Code
        'X': Data Matrix Bar Code
        """

        # guard for only currently allowed bar codes
        assert barcode_type in '23AQUCEX', "invalid barcode type"

        self.code += self._barcode_config(height, barcode_type, orientation, check_digit, \
            print_interpretation_line, print_interpretation_line_above, magnification, errorCorrection, mask, mode)

        #write the actual code
        if barcode_type in '23AUCEX':
            self.code += "^FD{}".format(code)
        elif barcode_type in 'Q':
            self.code += "^FD{}A,{}".format(errorCorrection,code)

    def dumpZPL(self):
        """Returns the current raw ZPL command"""
        return self.code+"^XZ"

    def saveFormat(self, name):
        """
        Saves a format that is defined by following write_field_number calls and to be recalled later using run_script.
        """
        self.code= self.code[:3] + ("^DF%s^FS" % name) + self.code[3:]

    def preview(self, index=0, outputfile=None):
        """
        Opens rendered preview using Labelary API.

        Not all commands are supported, see http://labelary.com for more information.
        """
        try:
            url = 'http://api.labelary.com/v1/printers/%idpmm/labels/%fx%f/%i/' % (
                self.dpmm, self.width/25.4, self.height/25.4, index)
            res = urlopen(url, self.dumpZPL().encode()).read()
        except IOError:
            raise Exception("Invalid preview received, mostlikely bad ZPL2 code uploaded.")
        if outputfile:
            with open(outputfile,'wb') as output:
                output.write(res)
        else:
            Image.open(io.BytesIO(res)).show()


def __main__():
    l = Label(100,80)
    height = 0
    l.origin(0,0)
    l.write_text("Problem?", char_height=10, char_width=8, line_width=60, justification='C')
    l.endorigin()

    height += 13
    image_width = 5
    l.origin((l.width-image_width)/2, height)
    image_height = l.write_graphic(
        Image.open(os.path.join(os.path.dirname(__file__), 'trollface-large.png')),
        image_width)
    l.endorigin()

    height += image_height + 5
    l.origin(22, height)
    l.write_barcode(height=70, barcode_type='U', check_digit='Y')
    l.write_text('07000002198')
    l.endorigin()

    height += 20
    l.origin(22, height)
    l.write_barcode(height=None, barcode_type='Q', magnification=4)
    l.write_text('https://github.com/cod3monk/zpl')
    l.endorigin()

    height += 20
    l.origin(0, height)
    l.write_text('Happy Troloween!', char_height=5, char_width=4, line_width=60,
                 justification='C')
    l.endorigin()

    print(l.dumpZPL())
    l.preview()


if __name__ == "__main__":
    __main__()
