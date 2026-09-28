#!/usr/bin/env python3
# Reduced Abaqus Learning Edition model for C25-CFRP beam
# Target: <1000 total nodes; 3D concrete CDP + embedded rebars + cohesive surface interaction + CFRP shell
import math, os, json

# -----------------------------
# Geometry and experimental data
# -----------------------------
L = 1219.2          # mm
B = 101.6           # mm
H = 203.2           # mm
fc = 28.7           # MPa measured cylinder strength
Pu_exp = 99.5       # kN
Pcr_exp = 93.5      # kN
cover = 38.1        # mm, source states 1.5 in upper/lower
E_cfrp = 165000.0   # MPa
t_cfrp = 4.0        # mm
nu_cfrp = 0.30
fy_rebar = 413.7    # MPa = 60 ksi
Es = 200000.0       # MPa

# Reduced mesh chosen to remain safely below Abaqus LE 1000-node limit.
# 24 elements along x, 2 through width, 4 through depth.
nx, ny, nz = 24, 2, 4
xs = [L*i/nx for i in range(nx+1)]
ys = [B*i/ny for i in range(ny+1)]
zs = [H*i/nz for i in range(nz+1)]

nodes = []
node_map = {}
nid = 0
def add_node(key,x,y,z):
    global nid
    nid += 1
    node_map[key] = nid
    nodes.append((nid,x,y,z))
    return nid

# Concrete nodes
for i,x in enumerate(xs):
    for j,y in enumerate(ys):
        for k,z in enumerate(zs):
            add_node(("C",i,j,k),x,y,z)

# CFRP shell nodes, separate but geometrically coincident with concrete soffit
for i,x in enumerate(xs):
    for j,y in enumerate(ys):
        add_node(("F",i,j),x,y,0.0)

# Rebar nodes: 2 bottom #4 + 2 top #3, aligned along x, embedded
yb = [cover, B-cover]
zbot = cover
ztop = H-cover
for tag,z in [("RB",zbot),("RT",ztop)]:
    for r,y in enumerate(yb):
        for i,x in enumerate(xs):
            add_node((tag,r,i),x,y,z)

# Stirrup nodes: 7 reconstructed loops at 3 in from end then 7 in c/c.
# Use independent embedded truss loops.
stirrup_x = [76.2 + 177.8*i for i in range(7)]
for s,x in enumerate(stirrup_x):
    corners = [
        (cover,cover),
        (B-cover,cover),
        (B-cover,H-cover),
        (cover,H-cover),
    ]
    for c,(y,z) in enumerate(corners):
        add_node(("S",s,c),x,y,z)

# Three reference points for left support, right support and load line
rp_left = add_node(("RP","L"),76.2,B/2.0,0.0)
rp_right = add_node(("RP","R"),L-76.2,B/2.0,0.0)
rp_load = add_node(("RP","P"),L/2.0,B/2.0,H)

# -----------------------------
# Elements
# -----------------------------
elems_c = []
eid = 0
def C(i,j,k): return node_map[("C",i,j,k)]
for i in range(nx):
    for j in range(ny):
        for k in range(nz):
            eid += 1
            # C3D8R standard ordering
            conn = [C(i,j,k), C(i+1,j,k), C(i+1,j+1,k), C(i,j+1,k),
                    C(i,j,k+1), C(i+1,j,k+1), C(i+1,j+1,k+1), C(i,j+1,k+1)]
            elems_c.append((eid,conn))

elems_f = []
def F(i,j): return node_map[("F",i,j)]
for i in range(nx):
    for j in range(ny):
        eid += 1
        elems_f.append((eid,[F(i,j),F(i+1,j),F(i+1,j+1),F(i,j+1)]))

elems_rb = []
# longitudinal rebars
for tag,area in [("RB",math.pi*12.7**2/4.0),("RT",math.pi*9.525**2/4.0)]:
    for r in range(2):
        for i in range(nx):
            eid += 1
            elems_rb.append((eid,[node_map[(tag,r,i)],node_map[(tag,r,i+1)]],tag,area))
# stirrups #2 = 6.35 mm diameter
Ast = math.pi*6.35**2/4.0
elems_st = []
for s in range(7):
    for c in range(4):
        eid += 1
        n1=node_map[("S",s,c)]
        n2=node_map[("S",s,(c+1)%4)]
        elems_st.append((eid,[n1,n2],Ast))

# -----------------------------
# Sets and surfaces
# -----------------------------
# Concrete nodes nearest support/load x planes
def nearest_ix(x):
    return min(range(len(xs)), key=lambda i: abs(xs[i]-x))
ixL, ixR, ixP = nearest_ix(76.2), nearest_ix(L-76.2), nearest_ix(L/2.0)

supportL_nodes=[C(ixL,j,0) for j in range(ny+1)]
supportR_nodes=[C(ixR,j,0) for j in range(ny+1)]
load_nodes=[C(ixP,j,nz) for j in range(ny+1)]

# Concrete bottom element faces S1 for cohesive master surface;
# shell top SPOS is slave surface.
bottom_elems=[]
for i in range(nx):
    for j in range(ny):
        # k=0 concrete element index
        e_index = (i*ny*nz)+(j*nz)+0
        bottom_elems.append(elems_c[e_index][0])

frp_eids=[e[0] for e in elems_f]
conc_eids=[e[0] for e in elems_c]
long_eids=[e[0] for e in elems_rb]
stir_eids=[e[0] for e in elems_st]

# -----------------------------
# CDP material curves
# -----------------------------
Ec = 4700.0*math.sqrt(fc)
nu = 0.20
# Abaqus CDP parameters: commonly used starting values. These are assumptions,
# not measured properties, and must be calibrated against the control beam.
dilation=36.0
ecc=0.10
fb0fc0=1.16
Kc=0.667
visc=1.0e-5

# Compression: simplified ascending/descending law based on fc
eps0 = 0.002
epsu = 0.0035
comp_pts = [
    (0.40*fc, 0.0000),
    (0.75*fc, 0.0005),
    (1.00*fc, 0.0010),
    (0.90*fc, 0.0018),
    (0.65*fc, 0.0025),
]
# compressive damage paired to inelastic strain
comp_dmg = [
    (0.00,0.0000),
    (0.05,0.0005),
    (0.15,0.0010),
    (0.35,0.0018),
    (0.60,0.0025),
]

# Tensile strength from common normal-weight concrete estimate
ft = 0.56*math.sqrt(fc)
# tension stiffening as stress vs cracking strain
tens_pts = [
    (ft,0.0),
    (0.75*ft,0.00015),
    (0.45*ft,0.00050),
    (0.20*ft,0.00120),
    (0.05*ft,0.00250),
]
tens_dmg = [
    (0.00,0.0),
    (0.20,0.00015),
    (0.50,0.00050),
    (0.75,0.00120),
    (0.95,0.00250),
]

# Cohesive surface interaction initial calibration values.
# These were not measured in the thesis and are intentionally marked as calibration inputs.
Kn = Ks = Kt = 3000.0      # MPa/mm nominal penalty stiffness
tn0 = 2.0                  # MPa
ts0 = 2.5                  # MPa
tt0 = 2.5                  # MPa
Gc = 0.10                  # N/mm, initial fracture-energy assumption

def lines(vals):
    return "\n".join(", ".join(f"{v:.8g}" for v in row) for row in vals)

out=[]
out += ["*HEADING",
        "C25-CFRP reduced 3D Abaqus Learning Edition model",
        "** Units: N, mm, MPa",
        "** Concrete: C3D8R + CDP; rebars: T3D2 embedded; CFRP: S4R; interface: surface-based cohesive",
        "** Experimental targets: fc=28.7 MPa, Pcr=93.5 kN, Pu=99.5 kN",
        "** CDP and cohesive parameters not measured experimentally are calibration assumptions.",
        "*PREPRINT, ECHO=NO, MODEL=NO, HISTORY=NO, CONTACT=NO",
        "*NODE"]
out += [f"{n}, {x:.6f}, {y:.6f}, {z:.6f}" for n,x,y,z in nodes]

out += ["*ELEMENT, TYPE=C3D8R, ELSET=CONCRETE"]
out += [f"{e}, "+", ".join(map(str,c)) for e,c in elems_c]
out += ["*ELEMENT, TYPE=S4R, ELSET=CFRP"]
out += [f"{e}, "+", ".join(map(str,c)) for e,c in elems_f]

# split bottom and top longitudinal bars into sets
rb_bot=[e for e in elems_rb if e[2]=="RB"]
rb_top=[e for e in elems_rb if e[2]=="RT"]
out += ["*ELEMENT, TYPE=T3D2, ELSET=RBOT"]
out += [f"{e}, {c[0]}, {c[1]}" for e,c,_,_ in rb_bot]
out += ["*ELEMENT, TYPE=T3D2, ELSET=RTOP"]
out += [f"{e}, {c[0]}, {c[1]}" for e,c,_,_ in rb_top]
out += ["*ELEMENT, TYPE=T3D2, ELSET=STIRRUPS"]
out += [f"{e}, {c[0]}, {c[1]}" for e,c,_ in elems_st]

def nset(name, ids):
    out.append(f"*NSET, NSET={name}")
    # 16 ids per line
    for i in range(0,len(ids),16):
        out.append(", ".join(map(str,ids[i:i+16])))

def elset(name, ids):
    out.append(f"*ELSET, ELSET={name}")
    for i in range(0,len(ids),16):
        out.append(", ".join(map(str,ids[i:i+16])))

nset("SUPPORT_L",supportL_nodes)
nset("SUPPORT_R",supportR_nodes)
nset("LOAD_LINE",load_nodes)
nset("RP_LEFT",[rp_left]); nset("RP_RIGHT",[rp_right]); nset("RP_LOAD",[rp_load])
nset("ALL_REBAR_NODES",
     [node_map[k] for k in node_map if isinstance(k,tuple) and k[0] in ("RB","RT","S")])
elset("ALL_REBAR", long_eids+stir_eids)
elset("CONC_BOTTOM",bottom_elems)

out += [
"*SURFACE, TYPE=ELEMENT, NAME=CONC_SOFFIT",
"CONC_BOTTOM, S1",
"*SURFACE, TYPE=ELEMENT, NAME=CFRP_TOP",
"CFRP, SPOS",
"*SURFACE, TYPE=NODE, NAME=SUPPORT_L_SURF, NSET=SUPPORT_L",
"*SURFACE, TYPE=NODE, NAME=SUPPORT_R_SURF, NSET=SUPPORT_R",
"*SURFACE, TYPE=NODE, NAME=LOAD_SURF, NSET=LOAD_LINE",
]

# Materials
out += [
"*MATERIAL, NAME=CONCRETE_C25",
"*ELASTIC",
f"{Ec:.6f}, {nu}",
"*CONCRETE DAMAGED PLASTICITY",
f"{dilation}, {ecc}, {fb0fc0}, {Kc}, {visc}",
"*CONCRETE COMPRESSION HARDENING",
lines(comp_pts),
"*CONCRETE COMPRESSION DAMAGE",
lines(comp_dmg),
"*CONCRETE TENSION STIFFENING, TYPE=STRAIN",
lines(tens_pts),
"*CONCRETE TENSION DAMAGE, TYPE=STRAIN",
lines(tens_dmg),
"*SOLID SECTION, ELSET=CONCRETE, MATERIAL=CONCRETE_C25",
",",
"*MATERIAL, NAME=REBAR_STEEL",
"*ELASTIC",
f"{Es}, 0.30",
"*PLASTIC",
f"{fy_rebar}, 0.0",
"500.0, 0.02",
"*SOLID SECTION, ELSET=RBOT, MATERIAL=REBAR_STEEL",
f"{math.pi*12.7**2/4.0:.6f}",
"*SOLID SECTION, ELSET=RTOP, MATERIAL=REBAR_STEEL",
f"{math.pi*9.525**2/4.0:.6f}",
"*SOLID SECTION, ELSET=STIRRUPS, MATERIAL=REBAR_STEEL",
f"{Ast:.6f}",
"*MATERIAL, NAME=CFRP_MAT",
"*ELASTIC, TYPE=ENGINEERING CONSTANTS",
f"{E_cfrp}, 10000., 10000., {nu_cfrp}, 0.30, 0.30, 5000., 5000., 5000.",
"*SHELL SECTION, ELSET=CFRP, MATERIAL=CFRP_MAT",
f"{t_cfrp}",
]

# Embedded reinforcement
out += [
"*EMBEDDED ELEMENT, HOST ELSET=CONCRETE",
"ALL_REBAR",
]

# Cohesive surface behavior
out += [
"*SURFACE INTERACTION, NAME=COHESIVE_BOND",
"*COHESIVE BEHAVIOR",
f"{Kn}, {Ks}, {Kt}",
"*DAMAGE INITIATION, CRITERION=QUADS",
f"{tn0}, {ts0}, {tt0}",
"*DAMAGE EVOLUTION, TYPE=ENERGY, SOFTENING=LINEAR, MIXED MODE BEHAVIOR=BK, POWER=1.45",
f"{Gc}, {Gc}, {Gc}",
"*CONTACT PAIR, INTERACTION=COHESIVE_BOND, TYPE=SURFACE TO SURFACE",
"CFRP_TOP, CONC_SOFFIT",
]

# Coupling to RPs
out += [
"*COUPLING, CONSTRAINT NAME=LEFT_COUPLE, REF NODE=RP_LEFT, SURFACE=SUPPORT_L_SURF",
"*KINEMATIC",
"1, 3",
"*COUPLING, CONSTRAINT NAME=RIGHT_COUPLE, REF NODE=RP_RIGHT, SURFACE=SUPPORT_R_SURF",
"*KINEMATIC",
"1, 3",
"*COUPLING, CONSTRAINT NAME=LOAD_COUPLE, REF NODE=RP_LOAD, SURFACE=LOAD_SURF",
"*KINEMATIC",
"1, 3",
]

# Boundary conditions
out += [
"*BOUNDARY",
"RP_LEFT, 1, 3, 0.",
"RP_RIGHT, 2, 3, 0.",
"RP_RIGHT, 1, 1, 0.",
"RP_LOAD, 1, 2, 0.",
]

# Nonlinear static displacement-controlled step
out += [
"*STEP, NAME=FLEXURE, NLGEOM=YES, INC=5000",
"*STATIC, STABILIZE=0.0002",
"0.002, 1.0, 1e-08, 0.02",
"*BOUNDARY",
"RP_LOAD, 3, 3, -25.0",
"*OUTPUT, FIELD, NUMBER INTERVAL=50",
"*NODE OUTPUT",
"U, RF",
"*ELEMENT OUTPUT, ELSET=CONCRETE",
"S, E, PE, DAMAGET, DAMAGEC, SDEG",
"*ELEMENT OUTPUT, ELSET=ALL_REBAR",
"S, LE, PE",
"*ELEMENT OUTPUT, ELSET=CFRP",
"S, LE",
"*CONTACT OUTPUT",
"CSTRESS, CDISP, CSDMG",
"*OUTPUT, HISTORY, FREQUENCY=1",
"*NODE OUTPUT, NSET=RP_LOAD",
"U3, RF3",
"*ENERGY OUTPUT",
"ALLIE, ALLSE, ALLPD, ALLCD, ALLWK",
"*END STEP",
]

inp="\n".join(out)+"\n"
open("C25_CFRP_Abaqus_LE_reduced3D.inp","w").write(inp)

meta={
    "total_nodes":len(nodes),
    "concrete_nodes":(nx+1)*(ny+1)*(nz+1),
    "cfrp_nodes":(nx+1)*(ny+1),
    "rebar_nodes":4*(nx+1)+7*4,
    "reference_nodes":3,
    "concrete_elements":len(elems_c),
    "cfrp_elements":len(elems_f),
    "rebar_elements":len(rb_bot)+len(rb_top)+len(elems_st),
    "node_limit_target":"<1000",
    "beam_mm":[L,B,H],
    "experimental":{"fc_MPa":fc,"Pcr_kN":Pcr_exp,"Pu_kN":Pu_exp},
    "source_backed":{"CFRP_E_MPa":E_cfrp,"CFRP_thickness_mm":t_cfrp,"cover_mm":cover,"rebar_fy_MPa":fy_rebar},
    "calibration_assumptions":{"CDP":[dilation,ecc,fb0fc0,Kc,visc],
      "cohesive":{"Kn":Kn,"Ks":Ks,"Kt":Kt,"tn0":tn0,"ts0":ts0,"tt0":tt0,"Gc":Gc}}
}
open("C25_CFRP_Abaqus_LE_reduced3D_metadata.json","w").write(json.dumps(meta,indent=2))
print(json.dumps(meta,indent=2))
