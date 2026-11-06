"""Runtime Korean particle selection (을/를, 이/가 ...) after the message formatter.

The game builds every message with the formatter at 0x020D9F4C(mode, buf, fmt, va).
All six callers are redirected to a small Thumb wrapper placed in the unused tail of
ITCM (0x01FFFDC0-0x01FFFFFF, zero in every save state checked).  The wrapper calls
the original formatter, then rewrites particle markers in the finished buffer in place.

Markers are reserved Shift-JIS codes written by build_full_text.py instead of
"을(를)" etc.  Hangul glyph codes are assigned in the order no-batchim, ㄹ-batchim,
other-batchim, so the class of the previous character is two code comparisons.
"""
import struct
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB

ITCM_BASE = 0x01FFFDC0
ITCM_END = 0x02000000
FORMATTER = 0x020D9F4C
CALL_SITES = [0x020767B2, 0x02076826, 0x02076862, 0x020ADB9E, 0x020D9F2A, 0x020D9F46]

# marker index -> (pattern in the translation text, text if batchim, text if none)
# index 4 ((으)로) treats ㄹ as "no batchim"; every other marker treats ㄹ as batchim.
MARKERS = [
    ('을(를)', '을', '를'),
    ('이(가)', '이', '가'),
    ('은(는)', '은', '는'),
    ('과(와)', '과', '와'),
    ('(으)', '으', ''),
    ('(이)', '이', ''),
    ('(이)에', '이', '예'),   # first half of (이)에요: 이에요 / 예요
    (None, '에', ''),         # second half, always follows marker 6
]
EU_INDEX = 4
PLACEHOLDER = 0xE000          # private-use characters standing for markers while encoding
# digit readings: 영 일 이 삼 사 오 육 칠 팔 구 -> 2 = batchim, 1 = ㄹ, 0 = none
DIGIT_CLASS = bytes([2, 1, 0, 2, 0, 0, 2, 1, 1, 0])
SKIP2 = [0x8176, 0x8178, 0x816A, 0x8140]   # 」 』 ） and full-width space keep the class
# the formatter (mode 3) turns ASCII digits into font digits 0x8740 '1' .. 0x8748 '9', 0x8749 '0'
DIGIT1 = 0x8740
SKIP1 = [0x20, 0x29]                        # space and ')'


def batchim_class(ch):
    """0 = no final consonant, 1 = ㄹ, 2 = other final consonant."""
    if not '가' <= ch <= '힣':
        return 0
    final = (ord(ch) - 0xAC00) % 28
    return 0 if final == 0 else (1 if final == 8 else 2)


def to_placeholders(text):
    """Replace particle patterns with private-use characters (longest pattern first)."""
    text = text.replace('(이)에요', chr(PLACEHOLDER + 6) + chr(PLACEHOLDER + 7) + '요')
    for i, (pattern, _, _) in enumerate(MARKERS[:6]):
        text = text.replace(pattern, chr(PLACEHOLDER + i))
    return text


def from_placeholders(text):
    text = text.replace(chr(PLACEHOLDER + 6) + chr(PLACEHOLDER + 7) + '요', '(이)에요')
    for i, (pattern, _, _) in enumerate(MARKERS[:6]):
        text = text.replace(chr(PLACEHOLDER + i), pattern)
    return text


def assemble(marker0, h0, h1, t1, t2, code_of):
    """Return the ITCM blob: wrapper, fixer, then data tables.  code_of maps a Hangul char to its glyph code."""
    table = b''.join(struct.pack('<HH', code_of(a) if a else 0, code_of(b) if b else 0) for _, a, b in MARKERS)
    src = f"""
    wrap:
        push {{r1, lr}}
        bl {FORMATTER:#x}
        pop {{r1}}
        push {{r0}}
        mov r0, r1
        bl fix
        pop {{r0}}
        pop {{pc}}
    fix:
        push {{r4, r5, r6, r7, lr}}
        mov r1, r0
        mov r2, r0
        movs r3, #0
    loop:
        ldrb r4, [r1]
        cmp r4, #0
        beq done
        cmp r4, #0x1a
        bne not_tag
        ldrb r5, [r1, #1]
        cmp r5, #2
        bhs copytag
        movs r5, #2
    copytag:
        ldrb r6, [r1]
        strb r6, [r2]
        adds r1, #1
        adds r2, #1
        subs r5, #1
        bne copytag
        b loop
    not_tag:
        cmp r4, #0x81
        blo single
        cmp r4, #0xa0
        blo dbl
        cmp r4, #0xe0
        blo single
    dbl:
        ldrb r5, [r1, #1]
        lsls r6, r4, #8
        orrs r6, r5
        ldr r7, lit_marker0
        subs r7, r6, r7
        cmp r7, #8
        bhs normal2
        adds r1, #2
        movs r4, #1
        cmp r7, #{EU_INDEX}
        bne thresh
        movs r4, #2
    thresh:
        ldr r5, lit_table
        lsls r7, r7, #2
        adds r5, r5, r7
        cmp r3, r4
        bhs use_a
        adds r5, #2
    use_a:
        ldrh r6, [r5]
        cmp r6, #0
        beq loop
        lsrs r4, r6, #8
        strb r4, [r2]
        strb r6, [r2, #1]
        adds r2, #2
        b loop
    normal2:
        strb r4, [r2]
        strb r5, [r2, #1]
        adds r1, #2
        adds r2, #2
        ldr r7, lit_d1
        subs r5, r6, r7
        cmp r5, #10
        bhs not_digit2
        adds r5, #1
        cmp r5, #10
        bne digit2
        movs r5, #0
    digit2:
        ldr r7, lit_digits
        ldrb r3, [r7, r5]
        b loop
    not_digit2:
        ldr r7, lit_s0
        cmp r6, r7
        beq loop
        ldr r7, lit_s1
        cmp r6, r7
        beq loop
        ldr r7, lit_s2
        cmp r6, r7
        beq loop
        ldr r7, lit_s3
        cmp r6, r7
        beq loop
        ldr r7, lit_h0
        cmp r6, r7
        blo cls0
        ldr r7, lit_h1
        cmp r6, r7
        bhi cls0
        movs r3, #2
        ldr r7, lit_t2
        cmp r6, r7
        bhs loop
        movs r3, #1
        ldr r7, lit_t1
        cmp r6, r7
        bhs loop
    cls0:
        movs r3, #0
        b loop
    single:
        strb r4, [r2]
        adds r1, #1
        adds r2, #1
        cmp r4, #{SKIP1[0]:#x}
        beq loop
        cmp r4, #{SKIP1[1]:#x}
        beq loop
        subs r5, r4, #0x30
        cmp r5, #10
        bhs cls0
        ldr r6, lit_digits
        ldrb r3, [r6, r5]
        b loop
    done:
        strb r4, [r2]
        pop {{r4, r5, r6, r7, pc}}
        .align 2
    lit_marker0: .word {marker0:#x}
    lit_table:   .word table
    lit_digits:  .word digits
    lit_d1: .word {DIGIT1:#x}
    lit_s0: .word {SKIP2[0]:#x}
    lit_s1: .word {SKIP2[1]:#x}
    lit_s2: .word {SKIP2[2]:#x}
    lit_s3: .word {SKIP2[3]:#x}
    lit_h0: .word {h0:#x}
    lit_h1: .word {h1:#x}
    lit_t1: .word {t1:#x}
    lit_t2: .word {t2:#x}
    table:
    """
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    # first pass to learn where the tables land
    enc, _ = ks.asm(src + '.byte 0\ndigits:\n.byte 0', ITCM_BASE)
    code_len = len(enc) - 2
    table_addr = ITCM_BASE + code_len
    digits_addr = table_addr + len(table)
    src2 = src.replace('lit_table:   .word table', f'lit_table:   .word {table_addr:#x}').replace('lit_digits:  .word digits', f'lit_digits:  .word {digits_addr:#x}')
    enc, _ = ks.asm(src2, ITCM_BASE)
    blob = bytes(enc)
    assert len(blob) == code_len, (len(blob), code_len)
    blob += table + DIGIT_CLASS
    blob += bytes((-len(blob)) % 4)
    assert ITCM_BASE + len(blob) <= ITCM_END, len(blob)
    return blob, {'wrapper': ITCM_BASE, 'table': table_addr, 'digits': digits_addr, 'size': len(blob)}


def thumb_bl(src, dst):
    off = dst - (src + 4)
    assert -0x400000 <= off < 0x400000 and off % 2 == 0
    off &= 0x7FFFFF
    return struct.pack('<HH', 0xF000 | (off >> 12), 0xF800 | ((off >> 1) & 0x7FF))


def patch_calls(arm9, base=0x02000000):
    """Redirect the formatter calls in the main ARM9 section to the ITCM wrapper."""
    out = bytearray(arm9)
    for site in CALL_SITES:
        o = site - base
        assert bytes(out[o:o + 4]) == thumb_bl(site, FORMATTER), hex(site)
        out[o:o + 4] = thumb_bl(site, ITCM_BASE)
    return bytes(out)
