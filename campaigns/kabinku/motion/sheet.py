import sys,glob
from PIL import Image,ImageDraw,ImageFont
d=sys.argv[1]; out=sys.argv[2]; cols=int(sys.argv[3]) if len(sys.argv)>3 else 4
fs=sorted(glob.glob(d+'/t*.jpg'),key=lambda f:float(f.split('/t')[-1][:-4]))
w,h=360,640; rows=(len(fs)+cols-1)//cols
W=Image.new('RGB',(cols*w,rows*(h+30)),(0,0,0)); dr=ImageDraw.Draw(W)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',22)
for i,f in enumerate(fs):
    im=Image.open(f).resize((w,h)); x=(i%cols)*w; y=(i//cols)*(h+30)
    W.paste(im,(x,y+30)); dr.text((x+5,y+3),f.split('/t')[-1][:-4]+'s',fill=(255,255,0),font=font)
W.save(out,quality=88)
