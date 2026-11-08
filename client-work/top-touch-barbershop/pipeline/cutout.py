import cv2, numpy as np, sys
import mediapipe as mp
from mediapipe.python.solutions import selfie_segmentation as ss
src, out = sys.argv[1], sys.argv[2]
im = cv2.imread(src); H,W = im.shape[:2]
with ss.SelfieSegmentation(model_selection=0) as seg:
    r = seg.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
m = r.segmentation_mask  # float 0..1, HxW
# refine with GrabCut at half res
s = 0.5; small = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
ms = cv2.resize(m, (small.shape[1], small.shape[0]))
gc = np.full(ms.shape, cv2.GC_PR_BGD, np.uint8)
gc[ms > 0.5] = cv2.GC_PR_FGD
gc[ms > 0.9] = cv2.GC_FGD
gc[ms < 0.05] = cv2.GC_BGD
bgd = np.zeros((1,65)); fgd = np.zeros((1,65))
cv2.grabCut(small, gc, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
fg = np.where((gc==cv2.GC_FGD)|(gc==cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
# keep largest component, fill holes
n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
if n > 1:
    k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); fg = np.where(lab==k, 255, 0).astype(np.uint8)
fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15,15)))
fg = cv2.resize(fg, (W,H), interpolation=cv2.INTER_LINEAR)
fg = cv2.GaussianBlur(fg, (5,5), 0)
cv2.imwrite(out, fg)
vis = im.copy(); vis[fg<128] = (vis[fg<128]*0.25).astype(np.uint8)
cv2.imwrite(out.replace('.png','_vis.jpg'), cv2.resize(vis,(W//3,H//3)))
print(out, (fg>128).mean())
