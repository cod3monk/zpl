

# Zebra-specific run-length encoding mapping,
# where run lengths (1–400) are encoded using characters 'G' to 'z'.
# See Zebra ZPL II Programming Guide for details.
ZPL_COMPRESS_MAP = {
    1: "G",
    2: "H",
    3: "I",
    4: "J",
    5: "K",
    6: "L",
    7: "M",
    8: "N",
    9: "O",
    10: "P",
    11: "Q",
    12: "R",
    13: "S",
    14: "T",
    15: "U",
    16: "V",
    17: "W",
    18: "X",
    19: "Y",
    20: "g",
    40: "h",
    60: "i",
    80: "j",
    100: "k",
    120: "l",
    140: "m",
    160: "n",
    180: "o",
    200: "p",
    220: "q",
    240: "r",
    260: "s",
    280: "t",
    300: "u",
    320: "v",
    340: "w",
    360: "x",
    380: "y",
    400: "z",
}

ZPL_COMPRESS_COUNTS = list(ZPL_COMPRESS_MAP.keys())
ZPL_COMPRESS_COUNTS.sort(reverse=True)


def _compress_char(count: int, char: str) -> str:
    data = ""
    local_count_glyph = ""

    while count > 0:
        local_count = 0
        for counts in ZPL_COMPRESS_COUNTS:
            if counts > count:
                continue
            count -= counts
            local_count_glyph += ZPL_COMPRESS_MAP[counts]
            local_count += counts
            break

    if local_count_glyph == "G":
        data += f"{char}"
    else:
        data += f"{local_count_glyph}{char}"
    return data


def compress_zpl_data(zpl_data: str) -> str:
    """
    Compresses ZPL (Zebra Programming Language) data using run-length encoding.

    This function applies ZPL-specific compression techniques to reduce the size
    of label definitions before sending them to the printer. It is particularly
    useful for compressing large graphic (~^GFA) fields or repeated character sequences.

    Parameters
    ----------
    zpl_data : str
        The raw ZPL string to be compressed.

    Returns
    -------
    str
        The compressed ZPL string.

    Notes
    -----
    - This function does not validate whether the input is valid ZPL.
    - It is intended for use with printable ZPL data such as graphics or large text fields.

    Examples
    --------
    >>> raw_zpl = '^GFA,...long hex string...^FS'
    >>> compressed = compress_zpl(raw_zpl)
    >>> print(compressed)
    '^GFA,...compressed hex string...^FS'
    """

    zipped_data = ""
    i = 0
    while i < len(zpl_data):
        cnt = 1
        next = zpl_data[i]
        for j in range(i + 1, len(zpl_data)):
            if zpl_data[j] == next:
                cnt += 1
            else:
                break
        zipped_data += _compress_char(cnt, next)
        i += cnt
    return zipped_data
