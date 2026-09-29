import numpy as np, trimesh, math
S=0.29  # m per pixel (20 m bar ~ 68 px)
CX,CY=1035,690
FH=3.2  # floor height
# name, cx, cy (px), L px, W px, angle deg, floors, classes
B=[
("A_Block",830,440,150,60,55,2,10),
("B_Block",1085,360,120,60,45,1,6),
("C_Block",995,415,60,28,50,1,2),
("D_Block",1065,525,70,30,55,1,3),
("E_Block",955,570,50,35,45,1,2),
("F_PinBlock",1035,690,100,60,40,2,8),
("G_Block",1160,660,90,28,55,1,4),
("H_Block",1210,740,90,30,55,1,4),
("I_Block",1290,645,170,60,47,2,12),
("J_Block",1385,565,200,70,55,2,14),
("K_Block",1462,468,50,40,50,1,2),
("L_Block",1497,522,35,25,50,1,1),
]
WALL=[235,225,205,255]; ROOF=[150,70,50,255]; DOOR=[60,40,30,255]; WIN=[110,160,200,255]; SLAB=[190,190,190,255]
def col(m,c): m.visual.face_colors=np.tile(c,(len(m.faces),1)); return m
def box(sx,sy,sz,x,y,z,c):
    m=trimesh.creation.box((sx,sy,sz)); m.apply_translation((x,y,z)); return col(m,c)
def roof(L,W,h,y0,c):
    a,b=L/2+.5,W/2+.5
    v=np.array([[-a,y0,-b],[a,y0,-b],[a,y0,b],[-a,y0,b],[-a+W/2,y0+h,0],[a-W/2,y0+h,0]],float)
    f=[[0,1,2],[0,2,3],[0,5,1],[0,4,5],[3,2,5],[3,5,4],[0,3,4],[1,5,2]]
    m=trimesh.Trimesh(v,f); m.fix_normals(); return col(m,c)
scene=trimesh.Scene()
scene.add_geometry(box(700,.2,700,0,-.1,0,[170,150,120,255]),node_name="Ground")
info=[]
for n,cx,cy,Lp,Wp,ang,fl,cl in B:
    L,W=Lp*S,Wp*S; parts=[]
    H=fl*FH
    parts.append(box(L,H,W,0,H/2,0,WALL))
    for f in range(1,fl): parts.append(box(L+.3,.25,W+.3,0,f*FH,0,SLAB))
    parts.append(roof(L,W,min(2.0,W*.18),H,ROOF))
    per=math.ceil(cl/fl); sp=L/(per+1)
    for f in range(fl):
        for i in range(per):
            if f*per+i>=cl: break
            x=-L/2+sp*(i+1); y=f*FH
            for side in (1,-1):
                parts.append(box(1.2,2.2,.15,x,y+1.1,side*(W/2+.02),DOOR))
                parts.append(box(1.0,1.0,.15,x+sp*.3,y+1.7,side*(W/2+.02),WIN))
                parts.append(box(1.0,1.0,.15,x-sp*.3,y+1.7,side*(W/2+.02),WIN))
    if fl>1: parts.append(box(L,.15,1.4,0,FH+.07,W/2+.7,SLAB))  # balcony walkway
    m=trimesh.util.concatenate(parts)
    R=trimesh.transformations.rotation_matrix(math.radians(-ang),[0,1,0])
    R[:3,3]=[(cx-CX)*S,0,(cy-CY)*S]
    scene.add_geometry(m,node_name=f"{n}_G{'+1' if fl>1 else ''}_{cl}classes",transform=R)
    info.append((n,fl,cl))
scene.export("/mnt/user-data/outputs/sos_technical_school.glb")
s=trimesh.load("/mnt/user-data/outputs/sos_technical_school.glb"); print(len(s.geometry),s.bounds)
