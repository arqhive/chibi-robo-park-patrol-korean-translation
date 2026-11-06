"""Decode original Nitro 2D resources and TEX0 textures. No source modification."""
import struct
from PIL import Image
import ndspy.texture
import ndspy.color
import ndspy._common

ndspy.color.prepareLUTs()


def blocks(data):
    at = struct.unpack_from('<H', data, 12)[0]
    result = {}
    for _ in range(struct.unpack_from('<H', data, 14)[0]):
        size = struct.unpack_from('<I', data, at+4)[0]
        assert 8 <= size <= len(data)-at
        result[data[at:at+4]] = data[at+8:at+size]
        at += size
    assert at == len(data)
    return result


def colors(raw):
    result = []
    for (v,) in struct.iter_unpack('<H', raw):
        result.append(tuple(((v >> shift) & 31)*255//31 for shift in [0, 5, 10])+(255,))
    return result


def palette(data):
    body = blocks(data)[b'TTLP']
    size, offset = struct.unpack_from('<II', body, 8)
    assert offset+size <= len(body)
    return colors(body[offset:offset+size])


def characters(data):
    body = blocks(data)[b'RAHC']
    ht, wt, fmt, mapping, layout, size, offset = struct.unpack_from('<HH5I', body)
    assert fmt in (3, 4) and layout == 0, (fmt, layout)
    assert offset+size <= len(body)
    return body[offset:offset+size], 4 if fmt == 3 else 8, (wt, ht)


def tile_pixels(raw, offset, bpp, pal, bank=0):
    count = bpp*8
    assert offset >= 0 and offset+count <= len(raw), (offset, count, len(raw))
    pixels = []
    for v in raw[offset:offset+count]:
        for idx in ([v & 15, v >> 4] if bpp == 4 else [v]):
            color_index = idx+(bank*16 if bpp == 4 else 0)
            assert color_index < len(pal), (color_index, len(pal))
            pixels.append(pal[color_index][:3]+(255 if idx else 0,))
    im = Image.new('RGBA', (8, 8)); im.putdata(pixels)
    return im


def tile_sheet(raw, bpp, pal, width_tiles=16):
    n = len(raw)//(8*bpp)
    assert len(raw) % (8*bpp) == 0
    out = Image.new('RGBA', (width_tiles*8, ((n+width_tiles-1)//width_tiles)*8))
    for i in range(n): out.paste(tile_pixels(raw, i*8*bpp, bpp, pal), ((i%width_tiles)*8, (i//width_tiles)*8))
    return out


SHAPES = {0: [(8,8),(16,16),(32,32),(64,64)], 1: [(16,8),(32,8),(32,16),(64,32)], 2: [(8,16),(8,32),(16,32),(32,64)]}


def cells(ncer, raw, bpp, pal):
    body = blocks(ncer)[b'KBEC']
    count, flags, offset, mapping, transfer = struct.unpack_from('<HHIII', body)
    assert flags in (0, 1) and mapping in range(4) and transfer == 0, (flags, mapping, transfer)
    stride = 16 if flags else 8
    oam_base = offset+count*stride
    result = []
    for i in range(count):
        n, attr, oam_offset = struct.unpack_from('<HHI', body, offset+i*stride)
        sprites = []; issues = []
        for j in range(n):
            a0,a1,a2 = struct.unpack_from('<HHH', body, oam_base+oam_offset+j*6)
            y, x = a0 & 255, a1 & 511
            if y >= 128: y -= 256
            if x >= 256: x -= 512
            shape, size = a0 >> 14, a1 >> 14
            if shape not in SHAPES: raise ValueError('prohibited OAM shape')
            w,h = SHAPES[shape][size]
            if a0 & 256:
                issues.append('affine_transform_not_applied')
            elif a0 & 512:
                continue  # disabled non-affine OBJ
            mode = (a0 >> 10) & 3
            if mode: issues.append('OBJ_blend_or_window_mode')
            assert (8 if a0 & 8192 else 4) == bpp
            start = (a2 & 1023)*(32 << mapping)
            sprite = Image.new('RGBA', (w,h))
            for yy in range(h//8):
                for xx in range(w//8):
                    tile = tile_pixels(raw, start+(yy*(w//8)+xx)*8*bpp, bpp, pal, a2 >> 12)
                    sprite.paste(tile, (xx*8, yy*8))
            if not a0 & 256:
                if a1 & 4096: sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                if a1 & 8192: sprite = sprite.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            sprites.append((x,y,w,h,sprite))
        if not sprites:
            result.append((Image.new('RGBA',(1,1)), {'cell':i,'origin':[0,0],'objects':0,'issues':issues}));continue
        left, top = min(s[0] for s in sprites), min(s[1] for s in sprites)
        right, bottom = max(s[0]+s[2] for s in sprites), max(s[1]+s[3] for s in sprites)
        assert 0 < right-left <= 1024 and 0 < bottom-top <= 1024
        out = Image.new('RGBA',(right-left,bottom-top))
        for x,y,w,h,im in reversed(sprites): out.alpha_composite(im,(x-left,y-top))
        result.append((out,{'cell':i,'origin':[left,top],'objects':len(sprites),'issues':sorted(set(issues))}))
    return result


def background(nscr, raw, bpp, pal):
    body = blocks(nscr)[b'NRCS']
    w,h,fmt,screen_format,size = struct.unpack_from('<HHHHI',body)
    assert screen_format == 0 and size == (w//8)*(h//8)*2 and len(body) >= 12+size
    out=Image.new('RGBA',(w,h))
    for y in range(h//8):
        for x in range(w//8):
            # Text screen blocks are 32x32 tiles in hardware layout.
            if w > 256 or h > 256:
                idx=((y//32)*(w//256)+x//32)*1024+(y%32)*32+x%32
            else: idx=y*(w//8)+x
            entry=struct.unpack_from('<H',body,12+idx*2)[0]
            tile=tile_pixels(raw,(entry&1023)*8*bpp,bpp,pal,entry>>12)
            if entry&1024:tile=tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if entry&2048:tile=tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            out.paste(tile,(x*8,y*8))
    return out


def texture_blocks(data):
    assert data[:4] in (b'BMD0', b'BTX0')
    count=struct.unpack_from('<H',data,14)[0]
    for i in range(count):
        at=struct.unpack_from('<I',data,16+i*4)[0]
        if data[at:at+4] == b'TEX0':
            size=struct.unpack_from('<I',data,at+4)[0]
            assert at+size<=len(data)
            # Use ndspy's installed TEX0 parser without modifying/repacking models.
            section=bytearray(data[at:at+size]);notes=[]
            # ndspy asserts a nonempty radix-root marker even for zero-entry
            # dictionaries. Normalize only that unused marker in the parser copy.
            for off in [struct.unpack_from('<H',section,14)[0],struct.unpack_from('<I',section,52)[0]]:
                if section[off+1] == 0 and struct.unpack_from('<I',section,off+8)[0] == 0x7f:
                    struct.pack_into('<I',section,off+8,0x17f)
                    notes.append('empty_dictionary_root_normalized_for_ndspy_read_only')
            parsed=ndspy.texture._readTEX0(section)
            # Shared palette offsets are legal. ndspy 4.2 treats the next equal
            # offset as the end and yields an empty palette; use the next DISTINCT
            # offset for each alias instead. This affects reads only.
            pal_offset=struct.unpack_from('<I',section,52)[0]
            pal_data=struct.unpack_from('<I',section,56)[0]
            pal_length=struct.unpack_from('<H',section,48)[0]*8
            entries=ndspy._common.loadInfoBlock(section,pal_offset,4)
            starts=[pal_data+struct.unpack_from('<H',entry)[0]*8 for _,_,_,entry in entries]
            ends=sorted(set(starts+[pal_data+pal_length]))
            if len(starts)!=len(set(starts)):
                repaired=[]
                for (name,u0,u2,entry),start in zip(entries,starts):
                    end=next(v for v in ends if v>start)
                    flag=struct.unpack_from('<H',entry,2)[0]
                    repaired.append((name,ndspy.texture.Palette(u0,u2,flag,section[start:end])))
                parsed['palettes']=repaired
                notes.append('shared_palette_offsets_decoded_with_next_distinct_end')
            parsed['parser_notes']=notes
            yield parsed
