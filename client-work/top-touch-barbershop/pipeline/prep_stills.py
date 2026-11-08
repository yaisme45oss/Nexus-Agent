import cv2, numpy as np, sys, os
S=sys.argv[1]
picks={'chairwall':12,'chairdisc':27,'corridor':37,'ceilingup':40,'corridor2':42,'chairs':46,'wide':53,'lounge':57,'loungetv':59,'window':1,'shelves':8}
for name,idx in picks.items():
    im=cv2.imread(f'{S}/shopframes/f_{idx:03d}.jpg')
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
    rows=np.where(g.mean(1)>10)[0]; cols=np.where(g.mean(0)>10)[0]
    y0,y1,x0,x1=rows[0],rows[-1]+1,cols[0],cols[-1]+1
    crop=im[y0:y1,x0:x1]
    cv2.imwrite(f'{S}/assets/stills/{name}.png',crop)
    print(name, idx, crop.shape[1],'x',crop.shape[0])
