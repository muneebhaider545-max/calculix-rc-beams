#!/usr/bin/env python3
import math, os

# Native OpenRadioss 3D model: C25-CFRP
# Units: tonne, mm, s, N, MPa
L=1219.2; B=101.6; H=203.2
xL=76.2; xM=L/2; xR=L-76.2
# nonuniform x mesh: 1 end element each side + 10 each half of span = 22 elements
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

bricks=[]; e=0
for i in range(nx):
    for j in range(ny):
        for k in range(nz):
            e+=1
            # Radioss brick node order compatible with standard hex8
            c=[nid[(i,j,k)],nid[(i+1,j,k)],nid[(i+1,j+1,k)],nid[(i,j+1,k)],
               nid[(i,j,k+1)],nid[(i+1,j,k+1)],nid[(i+1,j+1,k+1)],nid[(i,j+1,k+1)]]
            bricks.append((e,c))

# CFRP shell: shared soffit nodes -> perfect bond
shells=[]; se=10001
for i in range(nx):
    for j in range(ny):
        se+=1
        shells.append((se,[nid[(i,j,0)],nid[(i+1,j,0)],nid[(i+1,j+1,0)],nid[(i,j+1,0)]]))

def nearest_i(x):
    return min(range(len(xs)), key=lambda i:abs(xs[i]-x))
iL=nearest_i(xL); iM=nearest_i(xM); iR=nearest_i(xR)
left_nodes=[nid[(iL,j,0)] for j in range(3)]
right_nodes=[nid[(iR,j,0)] for j in range(3)]
mid_top=[nid[(iM,j,4)] for j in range(3)]
left_center=[nid[(iL,1,0)]]

# material values
fc=28.7
Ec=4700*math.sqrt(fc)
ft=0.56*math.sqrt(fc)
ftfc=ft/fc
rho_c=2.40e-9
rho_cfrp=1.50e-9
# smeared longitudinal steel ratio from two #4 tensile bars / gross area
Ast=2*math.pi*12.7**2/4
rho_rebar=Ast/(B*H)

def ints(vals):
    return "".join(f"{int(v):10d}" for v in vals)
def fl(vals):
    return "".join(f"{float(v):20.12g}" for v in vals)

starter=[]
starter += [
"#RADIOSS STARTER",
"/BEGIN",
"C25_CFRP_NATIVE_3D",
"      2025         0",
"                  Mg                  mm                   s",
"                  Mg                  mm                   s",
"/TITLE",
"C25-CFRP 3D RC beam - LAW24 concrete with smeared steel + CFRP shell",
"/DEF_SOLID",
"#  I_SOLID    ISMSTR             ISTRAIN                                  IFRAME",
"         0         0                   0                                       0",
"/NODE",
]
starter += [f"{nn:10d}{x:20.12g}{y:20.12g}{z:20.12g}" for nn,x,y,z in nodes]

# concrete LAW24
starter += [
"/MAT/LAW24/1",
"C25 concrete with smeared longitudinal reinforcement",
"#              RHO_I",
f"{rho_c:20.12g}",
"#                E_c                  NU      Icap",
f"{Ec:20.12g}{0.20:20.12g}{0:10d}",
"#                 fc            ft_on_fc            fb_on_fc            f2_on_fc            s0_on_fc",
f"{fc:20.12g}{ftfc:20.12g}{1.16:20.12g}{4.0:20.12g}{1.25:20.12g}",
"#                H_t               D_sup             EPS_max",
f"{0.0:20.12g}{0.999:20.12g}{0.01:20.12g}",
"#                k_y                 r_t                 r_c                H_bp                 ETC",
f"{0.5:20.12g}{0.0:20.12g}{0.0:20.12g}{-0.002:20.12g}{0.0:20.12g}",
"#            ALPHA_y             ALPHA_F               V_max",
f"{-0.2:20.12g}{-0.1:20.12g}{-0.35:20.12g}",
"#                f_k                 f_0                H_v0                EPS0               HVFAC",
f"{0.0:20.12g}{0.0:20.12g}{0.0:20.12g}{0.02:20.12g}{0.1:20.12g}",
"#                  E             sigma_y                 E_t",
f"{200000.0:20.12g}{413.7:20.12g}{1000.0:20.12g}",
"#             ALPHA1              ALPHA2              ALPHA3",
f"{rho_rebar:20.12g}{0.0:20.12g}{0.0:20.12g}",
"/MAT/LAW1/2",
"CFRP equivalent isotropic elastic laminate",
"#        Init. dens.          Ref. dens.",
f"{rho_cfrp:20.12g}{0.0:20.12g}",
"#                  E                  nu",
f"{165000.0:20.12g}{0.30:20.12g}",
]

# properties
starter += [
"/PROP/SOLID/1",
"Concrete solid property",
"#   Isolid    Ismstr               Icpre               Inpts    Itetra    Iframe                  dn",
"         0         0                   0                   0         0         0                   0",
"#                q_a                 q_b                   h            LAMBDA_V                MU_V",
f"{0.0:20.12g}{0.0:20.12g}{0.0:20.12g}{0.0:20.12g}{0.0:20.12g}",
"#             dt_min   istrain      IHKT",
f"{0.0:20.12g}{0:10d}{0:10d}",
"/PROP/TYPE1/2",
"CFRP shell 4 mm",
"#   Ishell    Ismstr     Ish3n    Idrill                            P_thick_fail",
"         0         0         0         0                                       0",
"#                 hm                  hf                  hr                  dm                  dn",
f"{1e-15:20.12g}{1e-15:20.12g}{1e-15:20.12g}{0.0:20.12g}{0.0:20.12g}",
"#        N   Istrain               Thick              Ashear              Ithick     Iplas",
f"{0:10d}{0:10d}{4.0:20.12g}{0.0:20.12g}{0:10d}{0:10d}",
]

# parts/elements
starter += [
"/PART/1",
"C25 reinforced concrete beam",
"         1         1         0",
"/BRICK/1",
]
starter += [f"{eid:10d}"+ints(c) for eid,c in bricks]
starter += [
"/PART/2",
"CFRP laminate - perfect bond via shared soffit nodes",
"         2         2         0",
"/SHELL/2",
]
starter += [f"{eid:10d}"+ints(c) for eid,c in shells]

# boundary node groups
starter += [
"/GRNOD/NODE/101","LEFT_SUPPORT_XZ",
]
starter += [" ".join(f"{v:10d}" for v in left_nodes)]
starter += ["/BCS/101","Left support pin XZ","#  Tra rot   skew_ID  grnod_ID",
            "   101 000         0       101"]
starter += ["/GRNOD/NODE/102","LEFT_SUPPORT_Y"]
starter += [" ".join(f"{v:10d}" for v in left_center)]
starter += ["/BCS/102","Left support transverse restraint","#  Tra rot   skew_ID  grnod_ID",
            "   010 000         0       102"]
starter += ["/GRNOD/NODE/103","RIGHT_SUPPORT_Z"]
starter += [" ".join(f"{v:10d}" for v in right_nodes)]
starter += ["/BCS/103","Right support roller Z","#  Tra rot   skew_ID  grnod_ID",
            "   001 000         0       103"]

# loading group and function: 0 to -25 mm over 0.20s
starter += ["/GRNOD/NODE/201","MIDSPAN_TOP_LOAD_LINE"]
starter += [" ".join(f"{v:10d}" for v in mid_top)]
starter += [
"/FUNCT/1",
"Midspan displacement ramp",
"#                  X                   Y",
f"{0.0:20.12g}{0.0:20.12g}",
f"{0.20:20.12g}{-25.0:20.12g}",
f"{0.25:20.12g}{-25.0:20.12g}",
"/IMPDISP/1",
"Midspan downward displacement",
"#   Ifunct       DIR     Iskew   Isensor   Gnod_id     Frame     Icoor",
"         1         Z         0         0       201         0         0",
"#             Ascale_x             Fscale_y              Tstart               Tstop",
f"{1.0:20.12g}{1.0:20.12g}{0.0:20.12g}{0.25:20.12g}",
]

# histories
starter += [
"/TH/NODE/1",
"Load line nodes",
"DZ        REACZ",
]
for v in mid_top:
    starter.append(f"{v:10d}{0:10d}")
starter += [
"/TH/PART/2",
"Concrete and CFRP part history",
"DEF",
"         1         2",
"/END",
]
open("C25_CFRP_NATIVE_0000.rad","w").write("\n".join(starter)+"\n")

engine=[
"#RADIOSS ENGINE",
"/ANIM/DT",
"0.0 0.005",
"/ANIM/VECT/DISP",
"/ANIM/VECT/VEL",
"/ANIM/VECT/FINT",
"/ANIM/ELEM/VONM",
"/ANIM/ELEM/EPSP",
"/ANIM/ELEM/DAM1",
"/ANIM/ELEM/DAM2",
"/ANIM/ELEM/DAM3",
"/ANIM/ELEM/ENER",
"/ANIM/GZIP",
"/TFILE/4",
"0.0005",
"/MON/ON",
"/PRINT/-1000/55",
"/RUN/C25_CFRP_NATIVE/1",
"0.25",
"/VERS/2025",
]
open("C25_CFRP_NATIVE_0001.rad","w").write("\n".join(engine)+"\n")

meta=f"""C25-CFRP native OpenRadioss model
nodes={len(nodes)}
brick_elements={len(bricks)}
cfrp_shell_elements={len(shells)}
fc_MPa={fc}
Ec_MPa={Ec:.4f}
ft_MPa={ft:.4f}
smeared_longitudinal_rebar_ratio={rho_rebar:.6f}
CFRP_E_MPa=165000
CFRP_thickness_mm=4
support_x_mm={xL},{xR}
load_x_mm={xM}
loading=displacement controlled to 25 mm over 0.20 s
CFRP interface=perfect bond by shared nodes
"""
open("C25_CFRP_NATIVE_metadata.txt","w").write(meta)
print(meta)
