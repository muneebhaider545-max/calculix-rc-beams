#!/usr/bin/env python3
import math, os, sys

# Native OpenRadioss 3D C25-CFRP model with explicit adhesive cohesive layer.
# Units: Mg, mm, s, N, MPa.
# IMPORTANT: LAW169 bond parameters below are calibration parameters because
# the source experiments identify RESSCHEM resin/hardener but do not report
# cohesive stiffness, bond strengths, or fracture energies.

L=1219.2; B=101.6; H=203.2
xL=76.2; xM=L/2; xR=L-76.2
adh_t=1.0

# Calibration candidate. E is traction-separation normal stiffness in MPa/mm for LAW169.
KN=float(os.getenv("COH_KN","3000.0"))
NU=float(os.getenv("COH_NU","0.35"))
TENMAX=float(os.getenv("COH_TENMAX","2.0"))
GCTEN=float(os.getenv("COH_GCTEN","0.10"))  # N/mm
SHRMAX=float(os.getenv("COH_SHRMAX","2.5"))
GCSHR=float(os.getenv("COH_GCSHR","0.50"))  # N/mm
PWRT=int(os.getenv("COH_PWRT","2"))
PWRS=int(os.getenv("COH_PWRS","2"))
SHT_SL=float(os.getenv("COH_SHT_SL","0.0"))
SHRP=float(os.getenv("COH_SHRP","0.0"))

# Nonuniform x mesh with exact support and midspan planes.
left=[xL + (xM-xL)*i/10.0 for i in range(11)]
right=[xM + (xR-xM)*i/10.0 for i in range(1,11)]
xs=[0.0]+left+right+[L]
ys=[0.0,B/2,B]
zs=[0.0,H/4,H/2,3*H/4,H]
nx=len(xs)-1; ny=2; nz=4

nodes=[]; nid={}; n=0
for i,x in enumerate(xs):
    for j,y in enumerate(ys):
        for k,z in enumerate(zs):
            n+=1; nid[(i,j,k)]=n; nodes.append((n,x,y,z))

# Concrete bricks
bricks=[]; e=0
for i in range(nx):
    for j in range(ny):
        for k in range(nz):
            e+=1
            c=[nid[(i,j,k)],nid[(i+1,j,k)],nid[(i+1,j+1,k)],nid[(i,j+1,k)],
               nid[(i,j,k+1)],nid[(i+1,j,k+1)],nid[(i+1,j+1,k+1)],nid[(i,j+1,k+1)]]
            bricks.append((e,c))

# Independent CFRP/adhesive lower-face nodes at z=-adh_t.
cnid={}; cfrp_nodes=[]
for i,x in enumerate(xs):
    for j,y in enumerate(ys):
        n+=1; cnid[(i,j)]=n; cfrp_nodes.append((n,x,y,-adh_t))
nodes += cfrp_nodes

# Cohesive connection bricks: bottom face = CFRP nodes; top face = concrete soffit nodes.
coh=[]; ce=20001
for i in range(nx):
    for j in range(ny):
        ce+=1
        # Local t-axis from face 1-4 (CFRP side) to face 5-8 (concrete side).
        c=[cnid[(i,j)],cnid[(i+1,j)],cnid[(i+1,j+1)],cnid[(i,j+1)],
           nid[(i,j,0)],nid[(i+1,j,0)],nid[(i+1,j+1,0)],nid[(i,j+1,0)]]
        coh.append((ce,c))

# CFRP shells on adhesive lower face.
shells=[]; se=10001
for i in range(nx):
    for j in range(ny):
        se+=1
        shells.append((se,[cnid[(i,j)],cnid[(i+1,j)],cnid[(i+1,j+1)],cnid[(i,j+1)]]))

def nearest_i(x):
    return min(range(len(xs)), key=lambda i:abs(xs[i]-x))
iL=nearest_i(xL); iM=nearest_i(xM); iR=nearest_i(xR)
left_nodes=[nid[(iL,j,0)] for j in range(3)]
right_nodes=[nid[(iR,j,0)] for j in range(3)]
mid_top=[nid[(iM,j,4)] for j in range(3)]
left_center=[nid[(iL,1,0)]]

# Materials
fc=28.7
Ec=4700*math.sqrt(fc)
ft=0.56*math.sqrt(fc); ftfc=ft/fc
rho_c=2.40e-9
rho_cfrp=1.50e-9
rho_adh=1.20e-9
Ast=2*math.pi*12.7**2/4
rho_rebar=Ast/(B*H)

def ints(vals): return "".join(f"{int(v):10d}" for v in vals)

starter=[
"#RADIOSS STARTER","/BEGIN","C25_CFRP_COHESIVE_3D","      2025         0",
"                  Mg                  mm                   s",
"                  Mg                  mm                   s",
"/TITLE","C25-CFRP 3D RC beam - LAW24 concrete + LAW169 adhesive cohesive layer + CFRP shell",
"/DEF_SOLID","#  I_SOLID    ISMSTR             ISTRAIN                                  IFRAME",
"         0         0                   0                                       0",
"/NODE",
]
starter += [f"{nn:10d}{x:20.12g}{y:20.12g}{z:20.12g}" for nn,x,y,z in nodes]

starter += [
"/MAT/LAW24/1","C25 concrete with smeared longitudinal reinforcement",
"#              RHO_I",f"{rho_c:20.12g}",
"#                E_c                  NU      Icap",f"{Ec:20.12g}{0.20:20.12g}{0:10d}",
"#                 fc            ft_on_fc            fb_on_fc            f2_on_fc            s0_on_fc",
f"{fc:20.12g}{ftfc:20.12g}{1.16:20.12g}{4.0:20.12g}{1.25:20.12g}",
"#                H_t               D_sup             EPS_max",f"{0.0:20.12g}{0.999:20.12g}{0.01:20.12g}",
"#                k_y                 r_t                 r_c                H_bp                 ETC",
f"{0.5:20.12g}{0.0:20.12g}{0.0:20.12g}{-0.002:20.12g}{0.0:20.12g}",
"#            ALPHA_y             ALPHA_F               V_max",f"{-0.2:20.12g}{-0.1:20.12g}{-0.35:20.12g}",
"#                f_k                 f_0                H_v0                EPS0               HVFAC",
f"{0.0:20.12g}{0.0:20.12g}{0.0:20.12g}{0.02:20.12g}{0.1:20.12g}",
"#                  E             sigma_y                 E_t",f"{200000.0:20.12g}{413.7:20.12g}{1000.0:20.12g}",
"#             ALPHA1              ALPHA2              ALPHA3",f"{rho_rebar:20.12g}{0.0:20.12g}{0.0:20.12g}",
"/MAT/LAW1/2","CFRP equivalent isotropic elastic laminate",
"#        Init. dens.          Ref. dens.",f"{rho_cfrp:20.12g}{0.0:20.12g}",
"#                  E                  nu",f"{165000.0:20.12g}{0.30:20.12g}",
"/MAT/LAW169/3","RESSCHEM adhesive - calibrated cohesive candidate",
"#              Rho_I",f"{rho_adh:20.12g}",
"#                  E                  PR              SHT_SL              TENMAX               GCTEN",
f"{KN:20.12g}{NU:20.12g}{SHT_SL:20.12g}{TENMAX:20.12g}{GCTEN:20.12g}",
"#             SHRMAX               GCSHR      PWRT      PWRS                SHRP",
f"{SHRMAX:20.12g}{GCSHR:20.12g}{PWRT:10d}{PWRS:10d}{SHRP:20.12g}",
]

starter += [
"/PROP/SOLID/1","Concrete solid property",
"#   Isolid    Ismstr               Icpre               Inpts    Itetra    Iframe                  dn",
"         0         0                   0                   0         0         0                   0",
"#                q_a                 q_b                   h            LAMBDA_V                MU_V",
f"{0.0:20.12g}{0.0:20.12g}{0.0:20.12g}{0.0:20.12g}{0.0:20.12g}",
"#             dt_min   istrain      IHKT",f"{0.0:20.12g}{0:10d}{0:10d}",
"/PROP/TYPE1/2","CFRP shell 4 mm",
"#   Ishell    Ismstr     Ish3n    Idrill                            P_thick_fail",
"         0         0         0         0                                       0",
"#                 hm                  hf                  hr                  dm                  dn",
f"{1e-15:20.12g}{1e-15:20.12g}{1e-15:20.12g}{0.0:20.12g}{0.0:20.12g}",
"#        N   Istrain               Thick              Ashear              Ithick     Iplas",
f"{0:10d}{0:10d}{4.0:20.12g}{0.0:20.12g}{0:10d}{0:10d}",
"/PROP/TYPE43/3","Adhesive connection property",
"#   Ismstr                                                                            True_thickness",
f"{4:10d}{adh_t:80.12g}",
]

starter += ["/PART/1","C25 reinforced concrete beam","         1         1         0","/BRICK/1"]
starter += [f"{eid:10d}"+ints(c) for eid,c in bricks]
starter += ["/PART/2","CFRP laminate","         2         2         0","/SHELL/2"]
starter += [f"{eid:10d}"+ints(c) for eid,c in shells]
starter += ["/PART/3","RESSCHEM cohesive adhesive layer","         3         3         0","/BRICK/3"]
starter += [f"{eid:10d}"+ints(c) for eid,c in coh]

# supports
starter += ["/GRNOD/NODE/101","LEFT_SUPPORT_XZ"," ".join(f"{v:10d}" for v in left_nodes),
"/BCS/101","Left support pin XZ","#  Tra rot   skew_ID  grnod_ID","   101 000         0       101",
"/GRNOD/NODE/102","LEFT_SUPPORT_Y"," ".join(f"{v:10d}" for v in left_center),
"/BCS/102","Left support transverse restraint","#  Tra rot   skew_ID  grnod_ID","   010 000         0       102",
"/GRNOD/NODE/103","RIGHT_SUPPORT_Z"," ".join(f"{v:10d}" for v in right_nodes),
"/BCS/103","Right support roller Z","#  Tra rot   skew_ID  grnod_ID","   001 000         0       103"]

# Quasi-static displacement ramp slowed from 0.20 to 2.00 s.
starter += ["/GRNOD/NODE/201","MIDSPAN_TOP_LOAD_LINE"," ".join(f"{v:10d}" for v in mid_top),
"/FUNCT/1","Midspan displacement ramp","#                  X                   Y",
f"{0.0:20.12g}{0.0:20.12g}",f"{2.0:20.12g}{-25.0:20.12g}",f"{2.2:20.12g}{-25.0:20.12g}",
"/IMPDISP/1","Midspan downward displacement",
"#   Ifunct       DIR     Iskew   Isensor   Gnod_id     Frame     Icoor",
"         1         Z         0         0       201         0         0",
"#             Ascale_x             Fscale_y              Tstart               Tstop",
f"{1.0:20.12g}{1.0:20.12g}{0.0:20.12g}{2.2:20.12g}"]

starter += ["/TH/NODE/1","Load line nodes","DZ        REACZ"]
for v in mid_top: starter.append(f"{v:10d}{0:10d}")
starter += ["/TH/PART/2","Parts history","DEF","         1         2         3","/END"]

open("C25_CFRP_COHESIVE_0000.rad","w").write("\n".join(starter)+"\n")

engine=[
"#RADIOSS ENGINE","/ANIM/DT","0.0 0.02",
"/ANIM/VECT/DISP","/ANIM/VECT/VEL","/ANIM/VECT/FINT",
"/ANIM/ELEM/VONM","/ANIM/ELEM/EPSP","/ANIM/ELEM/DAM1","/ANIM/ELEM/DAM2","/ANIM/ELEM/DAM3","/ANIM/ELEM/ENER",
"/ANIM/GZIP","/TFILE/4","0.002","/MON/ON","/PRINT/-1000/55",
"/RUN/C25_CFRP_COHESIVE/1","2.2","/VERS/2025",
]
open("C25_CFRP_COHESIVE_0001.rad","w").write("\n".join(engine)+"\n")

G=KN/(2*(1+NU))
dft=2*GCTEN/TENMAX
dfs=2*GCSHR/((1+SHRP)*SHRMAX)
meta=f"""C25-CFRP OpenRadioss cohesive-interface model
Source adhesive identification: RESSCHEM resin/hardener.
Source does NOT provide cohesive mechanical properties; values below are calibration parameters.
LAW169 normal stiffness E = {KN:.6g} MPa/mm
Poisson ratio = {NU:.6g}
Shear stiffness G = {G:.6g} MPa/mm
TENMAX = {TENMAX:.6g} MPa
GCTEN = {GCTEN:.6g} N/mm
SHRMAX = {SHRMAX:.6g} MPa
GCSHR = {GCSHR:.6g} N/mm
PWRT = {PWRT}
PWRS = {PWRS}
SHT_SL = {SHT_SL:.6g}
SHRP = {SHRP:.6g}
Derived pure-tension failure displacement = {dft:.6g} mm
Derived pure-shear failure displacement = {dfs:.6g} mm
Adhesive geometric thickness = {adh_t} mm
Connection = LAW169 + PROP/TYPE43 cohesive solid layer, not perfect bond.
Experimental calibration targets: Pu = 99.5 kN; delta_u = 20.058 mm; first crack = 93.5 kN.
"""
open("C25_CFRP_COHESIVE_metadata.txt","w").write(meta)
print(meta)

# workflow trigger
