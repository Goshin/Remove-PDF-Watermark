#!/usr/bin/env python3

# The MIT License (MIT)
#
# Copyright (c) 2016 John Chong
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import shutil
from collections import OrderedDict
import argparse
import io
import logging

import img2pdf
from PIL import Image
from PyPDF2 import PdfFileReader


def is_gray(a, b, c):
    r = 40
    if a + b + c < 350:
        return True
    if abs(a - b) > r:
        return False
    if abs(a - c) > r:
        return False
    if abs(b - c) > r:
        return False
    return True


def remove_watermark(image):
    image = image.convert("RGB")
    color_data = image.getdata()

    new_color = []
    for item in color_data:
        if is_gray(item[0], item[1], item[2]):
            new_color.append(item)
        else:
            new_color.append((255, 255, 255))

    image.putdata(new_color)
    return image


def process_page(pdf, page_index, skipped):
    content = pdf.getPage(page_index)['/Resources']['/XObject'].getObject()
    images = {}
    for obj in content:
        if content[obj]['/Subtype'] == '/Image':
            size = (content[obj]['/Width'], content[obj]['/Height'])
            data = content[obj]._data
            if content[obj]['/ColorSpace'] == '/DeviceRGB':
                mode = "RGB"
            else:
                mode = "P"

            if content[obj]['/Filter'] == '/FlateDecode':
                img = Image.frombytes(mode, size, data)
            else:
                img = Image.open(io.BytesIO(data))
            images[int(obj[3:])] = img
    images = OrderedDict(sorted(images.items())).values()
    widths, heights = zip(*(i.size for i in images))
    total_height = sum(heights)
    max_width = max(widths)
    concat_image = Image.new('RGB', (max_width, total_height))
    offset = 0
    for i in images:
        concat_image.paste(i, (0, offset))
        offset += i.size[1]
    if not skipped:
        concat_image = remove_watermark(concat_image)
    concat_image.save("./temp/{}.jpg".format(page_index))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_pdf_path', metavar='PATH')
    parser.add_argument('-o', '--output', metavar='out', type=argparse.FileType('wb'),
                        help='Output PDF file')
    parser.add_argument('-s', '--skip', type=int, default=0,
                        help='Skip over the first n page(s).')
    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    logging.basicConfig(level='INFO', format='%(asctime)s - %(levelname)s - %(message)s')

    directory = './temp/'
    if not os.path.exists(directory):
        os.makedirs(directory)

    images_path = []
    pdf = PdfFileReader(open(args.input_pdf_path, "rb"))
    for i in range(0, pdf.getNumPages()):
        logger.info("Processing page {}/{}".format(i + 1, pdf.getNumPages()))
        images_path.append("./temp/{}.jpg".format(i))
        process_page(pdf, i, i < args.skip)

    logger.info('Writing to output PDF file')
    args.output.write(img2pdf.convert(*list(map(img2pdf.input_images, images_path))))
    logger.info('Done')

    shutil.rmtree(directory, True)


if __name__ == '__main__':
    main()
