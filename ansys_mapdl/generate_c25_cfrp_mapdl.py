#!/usr/bin/env python3
from pathlib import Path
import math, zipfile

outdir=Path("ansys_output")
outdir.mkdir(exist_ok=True)

L=1219.2; B=101.6; H=203.2; cover=38.1
xL=76.2; xR=L-76.2; xM=L/2

# Mesh planes include supports, midspan, bar coordinates, and stirrup locations.
xs={0.0,L,xL,xR,xM}
x=0.0
while x<=L+1e-9:
    xs.add(round(x,6)); x+=50.8
x=xL
while x<=xR+1e-9:
    xs.add(round(x,6)); x+=101.6
xs=sorted(xs)
ys=sorted({0.0,cover,B-cover,B})
zs=sorted({0.0,cover,H-cover,H})

nid={}; nodes=[]; n=0
for i,x in enumerate(xs):
    for j,y in enumerate(ys):
        for k,z in enumerate(zs):
            n+=1; nid[(i,j,k)]=n; nodes.append((n,x,y,z))

solid=[]; eid=0
for i in range(len(xs)-1):
    for j in range(len(ys)-1):
        for k in range(len(zs)-1):
            eid+=1
            c=[nid[(i,j,k)],nid[(i+1,j,k)],nid[(i+1,j+1,k)],nid[(i,j+1,k)],
               nid[(i,j,k+1)],nid[(i+1,j,k+1)],nid[(i+1,j+1,k+1)],nid[(i,j+1,k+1)]]
            solid.append((eid,c))

# Duplicate soffit nodes for CFRP so INTER205 can separate.
cfrp={}
for i,x in enumerate(xs):
    for j,y in enumerate(ys):
        n+=1; cfrp[(i,j)]=n; nodes.append((n,x,y,0.0))

interface=[]; shell=[]
for i in range(len(xs)-1):
    for j in range(len(ys)-1):
        lo=[cfrp[(i,j)],cfrp[(i+1,j)],cfrp[(i+1,j+1)],cfrp[(i,j+1)]]
        up=[nid[(i,j,0)],nid[(i+1,j,0)],nid[(i+1,j+1,0)],nid[(i,j+1,0)]]
        eid+=1; interface.append((eid,lo+up))
        eid+=1; shell.append((eid,lo))

yi={v:i for i,v in enumerate(ys)}
zi={v:i for i,v in enumerate(zs)}
j1=yi[cover]; j2=yi[B-cover]; kb=zi[cover]; kt=zi[H-cover]

bot=[]; top=[]
for i in range(len(xs)-1):
    for j in (j1,j2):
        eid+=1; bot.append((eid,[nid[(i,j,kb)],nid[(i+1,j,kb)]]))
        eid+=1; top.append((eid,[nid[(i,j,kt)],nid[(i+1,j,kt)]]))

xidx={round(v,6):i for i,v in enumerate(xs)}
stirrups=[]; x=xL
while x<=xR+1e-9:
    i=xidx[round(x,6)]
    loop=[nid[(i,j1,kb)],nid[(i,j2,kb)],nid[(i,j2,kt)],nid[(i,j1,kt)]]
    for a,b in zip(loop,loop[1:]+loop[:1]):
        eid+=1; stirrups.append((eid,[a,b]))
    x+=101.6

# Materials
fc=28.7
Ec=4700*math.sqrt(fc)
ft=0.56*math.sqrt(fc)
fb=1.20*fc
psi=20.0
kappa_cm=0.0025-fc/Ec
kappa_cr=0.0025
omega_ci=0.33
omega_cr=0.10
kappa_tr=0.0005
omega_tr=0.20
Es=200000.0; fy=413.7; Et=1000.0
Ab=math.pi*12.7**2/4
At=math.pi*9.525**2/4
E1=165000.0; E2=12000.0; E3=12000.0
G12=5000.0; G13=5000.0; G23=4000.0
nu12=0.30; nu13=0.30; nu23=0.35; tcfrp=4.0

# CZM calibration starting values
tn0=2.0; ts0=2.5; GIc=0.10; GIIc=0.50
dn_fail=2*GIc/tn0
ds_fail=2*GIIc/ts0
alpha=0.10; beta=1.0

A=[]; ap=A.append
ap("/CLEAR")
ap("/FILNAME,C25_CFRP_MAPDL,1")
ap("/PREP7")
ap("! C25-CFRP RC beam | Units: N-mm-MPa")
ap("! SOLID185 concrete + LINK180 steel + SHELL181 CFRP + INTER205 cohesive interface")
ap("ET,1,SOLID185")
ap("ET,2,LINK180")
ap("ET,3,SHELL181")
ap("ET,4,INTER205")
ap("KEYOPT,4,2,0")

# Menetrey-Willam concrete
ap(f"MP,EX,1,{Ec:.6f}")
ap("MP,PRXY,1,0.20")
ap("TB,CONCRETE,1,,,MW")
ap(f"TBDATA,1,{fc:.6f},{ft:.6f},{fb:.6f}")
ap("TB,CONCRETE,1,,,DILA")
ap(f"TBDATA,1,{psi:.6f}")
ap("TB,CONCRETE,1,,,HSD6")
ap(f"TBDATA,1,{kappa_cm:.9f},{kappa_cr:.9f},{omega_ci:.6f},{omega_cr:.6f},{kappa_tr:.9f},{omega_tr:.6f}")

# Steel
ap(f"MP,EX,2,{Es:.6f}")
ap("MP,PRXY,2,0.30")
ap("TB,BISO,2")
ap(f"TBDATA,1,{fy:.6f},{Et:.6f}")

# Orthotropic CFRP (transverse/shear properties are assumptions)
ap(f"MP,EX,3,{E1:.6f}")
ap(f"MP,EY,3,{E2:.6f}")
ap(f"MP,EZ,3,{E3:.6f}")
ap(f"MP,PRXY,3,{nu12:.6f}")
ap(f"MP,PRXZ,3,{nu13:.6f}")
ap(f"MP,PRYZ,3,{nu23:.6f}")
ap(f"MP,GXY,3,{G12:.6f}")
ap(f"MP,GXZ,3,{G13:.6f}")
ap(f"MP,GYZ,3,{G23:.6f}")

# Bilinear cohesive law
ap("TB,CZM,4,,,BILI")
ap(f"TBDATA,1,{tn0:.6f},{dn_fail:.6f},{ts0:.6f},{ds_fail:.6f},{alpha:.6f},{beta:.6f}")

# Link areas and shell section
ap(f"R,1,{Ab:.9f}")
ap(f"R,2,{At:.9f}")
ap(f"R,3,{At:.9f}")
ap("SECTYPE,1,SHELL")
ap(f"SECDATA,{tcfrp:.6f},3,0,3")

# Nodes
for nn,x,y,z in nodes:
    ap(f"N,{nn},{x:.6f},{y:.6f},{z:.6f}")

# Elements
ap("TYPE,1"); ap("MAT,1")
for ee,c in solid: ap("EN,"+str(ee)+","+",".join(map(str,c)))
ap("TYPE,4"); ap("MAT,4")
for ee,c in interface: ap("EN,"+str(ee)+","+",".join(map(str,c)))
ap("TYPE,3"); ap("MAT,3"); ap("SECNUM,1")
for ee,c in shell: ap("EN,"+str(ee)+","+",".join(map(str,c)))
ap("TYPE,2"); ap("MAT,2"); ap("REAL,1")
for ee,c in bot: ap("EN,"+str(ee)+","+",".join(map(str,c)))
ap("REAL,2")
for ee,c in top: ap("EN,"+str(ee)+","+",".join(map(str,c)))
ap("REAL,3")
for ee,c in stirrups: ap("EN,"+str(ee)+","+",".join(map(str,c)))

ap("ALLSEL,ALL")
ap("FINISH")

# Nonlinear static solve
ap("/SOLU")
ap("ANTYPE,STATIC")
ap("NLGEOM,ON")
ap("AUTOTS,ON")
ap("NSUBST,100,1000,20")
ap("NEQIT,50")
ap("LNSRCH,ON")
ap("NROPT,FULL")
ap("OUTRES,ALL,ALL")

# Supports
ap(f"NSEL,S,LOC,X,{xL:.6f}")
ap("NSEL,R,LOC,Z,0")
ap("D,ALL,UZ,0")
ap("D,ALL,UX,0")
ap("ALLSEL,ALL")
ap(f"NSEL,S,LOC,X,{xR:.6f}")
ap("NSEL,R,LOC,Z,0")
ap("D,ALL,UZ,0")
ap("ALLSEL,ALL")
ap(f"NSEL,S,LOC,X,{xL:.6f}")
ap(f"NSEL,R,LOC,Y,{cover:.6f}")
ap("NSEL,R,LOC,Z,0")
ap("D,ALL,UY,0")
ap("ALLSEL,ALL")

# Midspan displacement control
ap(f"NSEL,S,LOC,X,{xM:.6f}")
ap(f"NSEL,R,LOC,Z,{H:.6f}")
ap("D,ALL,UZ,-25")
ap("ALLSEL,ALL")
ap("SOLVE")
ap("FINISH")

# Postprocessing
ap("/POST1")
ap("SET,LAST")
ap("ALLSEL,ALL")
ap("/EDGE,1,1")
ap("/FACET,1")
ap("/ESHAPE,1")
ap("PLDISP,2")
ap("PLNSOL,U,SUM")
ap("PLNSOL,S,EQV")
ap("FINISH")

dat=outdir/"C25_CFRP_MAPDL.dat"
dat.write_text("\n".join(A)+"\n")

readme=outdir/"README.txt"
readme.write_text(f"""C25-CFRP ANSYS MAPDL package

Run:
1. Open Mechanical APDL.
2. File > Read Input From...
3. Select C25_CFRP_MAPDL.dat.
4. Wait for the nonlinear solve to finish.
5. Review General Postproc.

Model:
Concrete: SOLID185 + Menetrey-Willam
Steel: LINK180
CFRP: SHELL181, 4 mm
Interface: INTER205 + bilinear CZM
Units: N-mm-MPa

Validation targets:
First crack = 93.5 kN
Ultimate load = 99.5 kN
Peak deflection = 20.058 mm

Important:
Cohesive parameters and CFRP transverse/shear constants are calibration/model assumptions.
They must not be described as measured RESSCHEM properties.
""")

zipf=Path("C25_CFRP_ANSYS_MAPDL_READY.zip")
with zipfile.ZipFile(zipf,"w",zipfile.ZIP_DEFLATED) as z:
    z.write(dat,dat.name)
    z.write(readme,readme.name)

print(dat)
print(zipf)
print("nodes",len(nodes),"solid",len(solid),"interface",len(interface),"shell",len(shell),"links",len(bot)+len(top)+len(stirrups))
