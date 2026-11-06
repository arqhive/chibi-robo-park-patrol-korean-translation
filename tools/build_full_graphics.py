"""Pack reviewed images into Nitro resources; verify every decoded cell."""
import struct,json,hashlib
from collections import defaultdict
import numpy as np
from PIL import Image
from extract_graphics import blocks,palette,characters,cells,background,SHAPES

def rebuild(source,replacements):
    head=source[:struct.unpack_from('<H',source,12)[0]];at=len(head);parts=[]
    for _ in range(struct.unpack_from('<H',source,14)[0]):
        magic=source[at:at+4];size=struct.unpack_from('<I',source,at+4)[0];body=replacements.get(magic,source[at+8:at+size]);body+=bytes((-len(body))%4)
        parts.append(magic+struct.pack('<I',len(body)+8)+body);at+=size
    out=bytearray(head+b''.join(parts));struct.pack_into('<I',out,8,len(out));return bytes(out)

def ncgr(source,raw):
    body=blocks(source)[b'RAHC'];offset=struct.unpack_from('<I',body,20)[0];head=bytearray(body[:offset]);struct.pack_into('<I',head,16,len(raw))
    # Sprite NCGR uses FFFF dimensions; background dimensions updated separately.
    return rebuild(source,{b'RAHC':bytes(head)+raw})

def indices(raw,bpp,w,h):
    a=np.frombuffer(raw,dtype=np.uint8)
    if bpp==4:a=np.stack((a&15,a>>4),axis=1).reshape(-1)
    return a.reshape(h//8,w//8,8,8).transpose(0,2,1,3).reshape(h,w).copy()

def pack(a,bpp):
    h,w=a.shape;flat=a.reshape(h//8,8,w//8,8).transpose(0,2,1,3).reshape(-1)
    if bpp==4:flat=flat[::2]|(flat[1::2]<<4)
    return flat.tobytes()

def visible_equal(a,b):
    return np.array_equal(a[:,:,3],b[:,:,3]) and np.array_equal(a[:,:,:3][a[:,:,3]>0],b[:,:,:3][b[:,:,3]>0])

def quantize(color,pal,bpp,bank,cache):
    if color[3]<128:return 0
    key=tuple(color[:3])+(bank,)
    if key not in cache:
        start=bank*16 if bpp==4 else 0;end=start+(16 if bpp==4 else len(pal));colors=np.array(pal[start+1:end],dtype=np.int32)[:,:3]
        cache[key]=1+int(np.argmin(np.sum((colors-np.array(color[:3],dtype=np.int32))**2,axis=1)))
    return cache[key]

def prepare(root,files,rows,out):
    families=defaultdict(list)
    for r in rows:families[r['key'].split('/')[0]].append(r)
    resources={};reports=[];out.mkdir(parents=True,exist_ok=True)
    for family,targets in sorted(families.items()):
        gc=files[family+'.NCGR'];pl=palette(files[family+'.NCLR']);raw,bpp,_=characters(gc);cache={}
        if targets[0]['kind']=='tile_background':
            assert len(targets)==1 and bpp==4
            r=targets[0];src=np.array(background(files[family+'.NSCR'],raw,bpp,pl));desired=np.array(Image.open(root/r['localization']['output']).convert('RGBA'))
            sb=bytearray(blocks(files[family+'.NSCR'])[b'NRCS']);w,h,_,_,size=struct.unpack_from('<HHHHI',sb)
            tiles=[];lookup={};expected=desired.copy()
            for ty in range(h//8):
                for tx in range(w//8):
                    idx=ty*(w//8)+tx;entry=struct.unpack_from('<H',sb,12+idx*2)[0];bank=entry>>12;tile=np.zeros((8,8),dtype=np.uint8)
                    for y in range(8):
                        for x in range(8):
                            color=desired[ty*8+y,tx*8+x];q=quantize(color,pl,bpp,bank,cache);tile[y,x]=q;expected[ty*8+y,tx*8+x]=pl[bank*16+q][:3]+(255 if q else 0,)
                    data=pack(tile,bpp)
                    if data not in lookup:lookup[data]=len(tiles);tiles.append(data)
                    assert lookup[data]<1024
                    struct.pack_into('<H',sb,12+idx*2,(bank<<12)|lookup[data])
            newraw=b''.join(tiles);newgc=ncgr(gc,newraw);body=bytearray(blocks(newgc)[b'RAHC']);struct.pack_into('<HH',body,0,1,len(tiles));newgc=rebuild(newgc,{b'RAHC':bytes(body)});newscr=rebuild(files[family+'.NSCR'],{b'NRCS':bytes(sb)})
            result=background(newscr,newraw,bpp,pl);assert visible_equal(np.array(result),expected);result.save(out/(family+'-screen.png'));resources[family+'.NCGR']=newgc;resources[family+'.NSCR']=newscr
            reports.append({'family':family,'target_cells':1,'decoded_verified':True,'tiles':len(tiles),'before_bytes':len(raw),'after_bytes':len(newraw)});continue
        ce=files[family+'.NCER'];body=blocks(ce)[b'KBEC'];count,flags,offset,mapping,transfer=struct.unpack_from('<HHIII',body);assert not transfer
        stride=16 if flags else 8;base=offset+count*stride;unit=32<<mapping
        original=cells(ce,raw,bpp,pl);objects=[];patches={int(r['key'].split('/')[-1]):r for r in targets};expected={};loss=[]
        for i in range(count):
            n,attr,o=struct.unpack_from('<HHI',body,offset+i*stride);objs=[]
            for j in range(n):
                a0,a1,a2=struct.unpack_from('<HHH',body,base+o+j*6);disabled=not(a0&256) and bool(a0&512)
                x=a1&511;y=a0&255;x=x-512 if x>=256 else x;y=y-256 if y>=128 else y
                if disabled:objs.append({'attrs':[a0,a1,a2],'disabled':True});continue
                w,h=SHAPES[a0>>14][a1>>14];start=(a2&1023)*unit;length=w*h*bpp//8;data=indices(raw[start:start+length],bpp,w,h)
                flipx=not(a0&256) and bool(a1&4096);flipy=not(a0&256) and bool(a1&8192)
                if flipx:data=data[:,::-1].copy()
                if flipy:data=data[::-1].copy()
                objs.append(dict(attrs=[a0,a1,a2],disabled=False,x=x,y=y,w=w,h=h,bank=a2>>12,flipx=flipx,flipy=flipy,data=data))
            if i in patches:
                r=patches[i];desired=np.array(Image.open(root/r['localization']['output']).convert('RGBA'));src=np.array(original[i][0]);assert desired.shape==src.shape,(family,i,desired.shape,src.shape)
                changed=(desired[:,:,3]>=128)!=(src[:,:,3]>0);changed|=(desired[:,:,3]>=128)&np.any(desired[:,:,:3]!=src[:,:,:3],axis=2)
                left,top=original[i][1]['origin'];exp=src.copy()
                for yy,xx in zip(*np.where(changed)):
                    candidates=[obj for obj in objs if not obj['disabled'] and obj['x']<=xx+left<obj['x']+obj['w'] and obj['y']<=yy+top<obj['y']+obj['h']]
                    assert candidates,(family,i,xx,yy,'outside OAM coverage')
                    first=candidates[0];q=quantize(desired[yy,xx],pl,bpp,first['bank'],cache)
                    for j,obj in enumerate(candidates):
                        if j==0 or q==0:obj['data'][yy+top-obj['y'],xx+left-obj['x']]=q if j==0 else 0
                    pi=q+(first['bank']*16 if bpp==4 else 0);exp[yy,xx]=pl[pi][:3]+(255 if q else 0,)
                expected[i]=exp
                opaque=desired[:,:,3]>=128;delta=np.abs(desired[:,:,:3].astype(int)-exp[:,:,:3].astype(int))[opaque]
                loss.append({'key':r['key'],'quantized_pixels':int(np.count_nonzero(np.any(delta>0,axis=1))),'mean_channel_error':float(delta.mean()) if delta.size else 0,'max_channel_error':int(delta.max()) if delta.size else 0})
            for obj in objs:
                if obj['disabled']:continue
                data=obj.pop('data')
                if obj['flipy']:data=data[::-1]
                if obj['flipx']:data=data[:,::-1]
                obj['packed']=pack(data,bpp)
            objects.append(objs)
        # Repack every sprite with aligned substring deduplication; this isolates
        # shared original tiles, preserving all unedited cells on round-trip.
        unique=sorted({o['packed'] for objs in objects for o in objs if not o['disabled']},key=lambda v:(-len(v),v))
        packed=bytearray();positions={}
        for data in unique:
            pos=packed.find(data)
            while pos>=0 and pos%unit:pos=packed.find(data,pos+1)
            if pos<0:
                packed+=bytes((-len(packed))%unit);pos=len(packed);packed+=data
            assert pos//unit<1024,(family,len(packed),'OBJ tile index capacity')
            positions[data]=pos
        desc=bytearray(body[:base]);oams=bytearray()
        for i,objs in enumerate(objects):
            struct.pack_into('<I',desc,offset+i*stride+4,len(oams))
            for obj in objs:
                a0,a1,a2=obj['attrs']
                if not obj['disabled']:a2=(a2&0xfc00)|(positions[obj['packed']]//unit)
                oams+=struct.pack('<HHH',a0,a1,a2)
        newce=rebuild(ce,{b'KBEC':bytes(desc+oams)});newgc=ncgr(gc,bytes(packed));decoded=cells(newce,bytes(packed),bpp,pl)
        for i,((result,meta),(source,oldmeta)) in enumerate(zip(decoded,original)):
            assert meta==oldmeta and result.size==source.size
            assert visible_equal(np.array(result),expected.get(i,np.array(source))),(family,i,'decoded mismatch')
            if i in patches:result.save(out/(patches[i]['key'].replace('/','-')+'.png'))
        resources[family+'.NCGR']=newgc;resources[family+'.NCER']=newce
        reports.append({'family':family,'target_cells':len(targets),'all_cells_verified':count,'unmodified_cells_verified':count-len(targets),'before_bytes':len(raw),'after_bytes':len(packed),'mapping':mapping,'quantization':loss})
        print(f'{family}: {len(targets)} targets, {count} cells verified, tiles {len(raw)} -> {len(packed)}',flush=True)
    return resources,reports
