#!/usr/bin/env python3
import math, os, json

L=1219.2
B=101.6
H=203.2
DX=25.4
xs=[round(i*DX,6) for i in range(49)]
ys=[0.0,44.45,50.8,57.15,101.6]
zs=[0.0,44.45,101.6,160.3375,203.2]

def nm(prefix,i): return f"{prefix}{i:06d}"[:8]

nodes={}
node_lines=[]
nid=0
def add_node(key,x,y,z,prefix="N"):
    global nid
    if key in nodes: return nodes[key]
    nid+=1
    name=nm(prefix,nid)
    nodes[key]=name
    node_lines.append((name,x,y,z))
    return name

# concrete nodes
for ix,x in enumerate(xs):
    for iy,y in enumerate(ys):
        for iz,z in enumerate(zs):
            add_node(("c",ix,iy,iz),x,y,z)

# plate nodes: bottom z=-4 and top z=0, intentionally distinct from concrete bottom
for ix,x in enumerate(xs):
    for iy,y in enumerate(ys):
        add_node(("p",ix,iy,0),x,y,-4.0)
        add_node(("p",ix,iy,1),x,y,0.0)

hexes=[]
conc=[]
plate=[]
czm=[]
cohesive_penta=[]
eid=0
def add_hex(prefix,nodelist,group):
    global eid
    eid+=1
    en=nm(prefix,eid)
    hexes.append((en,nodelist))
    group.append(en)
    return en

# concrete HEXA8
for ix in range(len(xs)-1):
    for iy in range(len(ys)-1):
        for iz in range(len(zs)-1):
            n=[
                nodes[("c",ix,iy,iz)],
                nodes[("c",ix+1,iy,iz)],
                nodes[("c",ix+1,iy+1,iz)],
                nodes[("c",ix,iy+1,iz)],
                nodes[("c",ix,iy,iz+1)],
                nodes[("c",ix+1,iy,iz+1)],
                nodes[("c",ix+1,iy+1,iz+1)],
                nodes[("c",ix,iy+1,iz+1)],
            ]
            add_hex("C",n,conc)

# CFRP plate HEXA8
for ix in range(len(xs)-1):
    for iy in range(len(ys)-1):
        n=[
            nodes[("p",ix,iy,0)],
            nodes[("p",ix+1,iy,0)],
            nodes[("p",ix+1,iy+1,0)],
            nodes[("p",ix,iy+1,0)],
            nodes[("p",ix,iy,1)],
            nodes[("p",ix+1,iy,1)],
            nodes[("p",ix+1,iy+1,1)],
            nodes[("p",ix,iy+1,1)],
        ]
        add_hex("P",n,plate)

# Zero-thickness cohesive interface: two degenerate PENTA6 wedges per rectangular patch.
# The first triangular face uses distinct CFRP top-surface nodes and the second
# matching face uses coincident concrete bottom-surface nodes.
for ix in range(len(xs)-1):
    for iy in range(len(ys)-1):
        nA=[
            nodes[("p",ix,iy,1)],
            nodes[("p",ix+1,iy,1)],
            nodes[("p",ix+1,iy+1,1)],
            nodes[("c",ix,iy,0)],
            nodes[("c",ix+1,iy,0)],
            nodes[("c",ix+1,iy+1,0)],
        ]
        eid+=1
        en=nm("J",eid)
        cohesive_penta.append((en,nA))
        czm.append(en)
        nB=[
            nodes[("p",ix,iy,1)],
            nodes[("p",ix+1,iy+1,1)],
            nodes[("p",ix,iy+1,1)],
            nodes[("c",ix,iy,0)],
            nodes[("c",ix+1,iy+1,0)],
            nodes[("c",ix,iy+1,0)],
        ]
        eid+=1
        en=nm("J",eid)
        cohesive_penta.append((en,nB))
        czm.append(en)

segs=[]
lbot=[]; ltop=[]; stir=[]
sid=0
def add_seg(prefix,a,b,group):
    global sid
    sid+=1
    sn=nm(prefix,sid)
    segs.append((sn,a,b))
    group.append(sn)

# longitudinal reinforcement: 2 bottom #4 and 2 top #3
for iy in [1,3]:
    for ix in range(len(xs)-1):
        add_seg("B",nodes[("c",ix,iy,1)],nodes[("c",ix+1,iy,1)],lbot)
        add_seg("T",nodes[("c",ix,iy,3)],nodes[("c",ix+1,iy,3)],ltop)

# reconstructed #2 closed stirrups at 3 in from end then 7 in c/c
for ix in [3,10,17,24,31,38,45]:
    corners=[
        nodes[("c",ix,1,1)],
        nodes[("c",ix,3,1)],
        nodes[("c",ix,3,3)],
        nodes[("c",ix,1,3)],
    ]
    for a,b in zip(corners,corners[1:]+corners[:1]):
        add_seg("S",a,b,stir)

def wrap_group(title, names):
    out=["GROUP_MA",title]
    line=""
    for n in names:
        token=n+" "
        if len(line)+len(token)>72:
            out.append(line.rstrip()); line=""
        line+=token
    if line: out.append(line.rstrip())
    out+=["FINSF",""]
    return out

def wrap_group_no(title,names):
    out=["GROUP_NO",title]
    line=""
    for n in names:
        token=n+" "
        if len(line)+len(token)>72:
            out.append(line.rstrip()); line=""
        line+=token
    if line: out.append(line.rstrip())
    out+=["FINSF",""]
    return out

# boundary/loading groups
ixL=3; ixM=24; ixR=45
supl=[nodes[("c",ixL,iy,0)] for iy in range(len(ys))]
supr=[nodes[("c",ixR,iy,0)] for iy in range(len(ys))]
load=[nodes[("c",ixM,iy,len(zs)-1)] for iy in range(len(ys))]
mid=[nodes[("c",ixM,2,len(zs)-1)]]
piny=[nodes[("c",ixL,0,0)]]
panc=[nodes[("p",ixM,2,1)]]

mail=[]
mail+=["TITRE","C25 CFRP 3D RC beam with cohesive interface","FINSF",""]
mail+=["COOR_3D"]
for name,x,y,z in node_lines:
    mail.append(f"{name} {x:.6f} {y:.6f} {z:.6f}")
mail+=["FINSF",""]
mail+=["HEXA8"]
for en,n in hexes:
    mail.append(en+" "+" ".join(n))
mail+=["FINSF",""]
mail+=["PENTA6"]
for en,n in cohesive_penta:
    mail.append(en+" "+" ".join(n))
mail+=["FINSF",""]
mail+=["SEG2"]
for en,a,b in segs:
    mail.append(f"{en} {a} {b}")
mail+=["FINSF",""]
mail+=wrap_group("CONC",conc)
mail+=wrap_group("PLATE",plate)
mail+=wrap_group("CZM",czm)
mail+=wrap_group("LBOT",lbot)
mail+=wrap_group("LTOP",ltop)
mail+=wrap_group("STIR",stir)
mail+=wrap_group_no("SUPL",supl)
mail+=wrap_group_no("SUPR",supr)
mail+=wrap_group_no("LOAD",load)
mail+=wrap_group_no("MID",mid)
mail+=wrap_group_no("PINY",piny)
mail+=wrap_group_no("PANC",panc)
mail+=["FIN",""]
open("c25_cfrp.mail","w").write("\n".join(mail))

fc=28.7
E=4700.0*math.sqrt(fc)
ft=0.56*math.sqrt(fc)
comm=f"""DEBUT()

MA=LIRE_MAILLAGE(FORMAT='ASTER')
MO=AFFE_MODELE(
    MAILLAGE=MA,
    AFFE=(
      _F(GROUP_MA='CONC',PHENOMENE='MECANIQUE',MODELISATION='3D'),
      _F(GROUP_MA='PLATE',PHENOMENE='MECANIQUE',MODELISATION='3D'),
      _F(GROUP_MA='CZM',PHENOMENE='MECANIQUE',MODELISATION='3D_JOINT'),
      _F(GROUP_MA=('LBOT','LTOP','STIR'),PHENOMENE='MECANIQUE',MODELISATION='BARRE'),
    )
)

FC=DEFI_CONSTANTE(NOM_RESU='F_C',VALE={fc:.8f})
FT=DEFI_CONSTANTE(NOM_RESU='F_T',VALE={ft:.8f})
BIAX=DEFI_CONSTANTE(NOM_RESU='COEF_BIAX',VALE=1.16)
GC=DEFI_CONSTANTE(NOM_RESU='ENER_COMP_RUPT',VALE=10.0)
GT=DEFI_CONSTANTE(NOM_RESU='ENER_TRAC_RUPT',VALE=0.10)

BET=DEFI_MATERIAU(
    ELAS=_F(E={E:.8f},NU=0.20),
    BETON_DOUBLE_DP=_F(
        F_C=FC,F_T=FT,COEF_BIAX=BIAX,
        ENER_COMP_RUPT=GC,ENER_TRAC_RUPT=GT,
        COEF_ELAS_COMP=33.3333333,
        ECRO_COMP_P_PIC='LINEAIRE',
        ECRO_TRAC_P_PIC='LINEAIRE',
        LONG_CARA=25.4)
)

REB=DEFI_MATERIAU(
    ELAS=_F(E=200000.0,NU=0.30),
    ECRO_LINE=_F(D_SIGM_EPSI=1000.0,SY=413.7)
)

FRP=DEFI_MATERIAU(ELAS=_F(E=165000.0,NU=0.30))

BOND=DEFI_MATERIAU(
    ELAS=_F(E=3000.0,NU=0.30),
    RUPT_FRAG=_F(GC=10.0,SIGM_C=4.0,PENA_ADHERENCE=0.00001)
)

CHMAT=AFFE_MATERIAU(
    MAILLAGE=MA,
    AFFE=(
      _F(GROUP_MA='CONC',MATER=BET),
      _F(GROUP_MA=('LBOT','LTOP','STIR'),MATER=REB),
      _F(GROUP_MA='PLATE',MATER=FRP),
      _F(GROUP_MA='CZM',MATER=BOND),
    )
)

CARA=AFFE_CARA_ELEM(
    MODELE=MO,
    BARRE=(
      _F(GROUP_MA='LBOT',SECTION='CERCLE',CARA='R',VALE=6.35),
      _F(GROUP_MA='LTOP',SECTION='CERCLE',CARA='R',VALE=4.7625),
      _F(GROUP_MA='STIR',SECTION='CERCLE',CARA='R',VALE=3.175),
    )
)

BC=AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
      _F(GROUP_NO='SUPL',DX=0.0,DZ=0.0),
      _F(GROUP_NO='SUPR',DZ=0.0),
      _F(GROUP_NO='PINY',DY=0.0),
      _F(GROUP_NO='PANC',DX=0.0,DY=0.0),
    )
)

LD=AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=_F(GROUP_NO='LOAD',DZ=-22.0)
)

RAMP=DEFI_FONCTION(NOM_PARA='INST',VALE=(0.0,0.0,1.0,1.0))

LR=DEFI_LIST_REEL(DEBUT=0.0,INTERVALLE=_F(JUSQU_A=1.0,NOMBRE=100))
LI=DEFI_LIST_INST(DEFI_LIST=_F(LIST_INST=LR),
                  ECHEC=_F(ACTION='DECOUPE',SUBD_METHODE='MANUEL',
                           SUBD_PAS=4,SUBD_NIVEAU=5))

RES=STAT_NON_LINE(
    MODELE=MO,CARA_ELEM=CARA,CHAM_MATER=CHMAT,
    EXCIT=(
      _F(CHARGE=BC),
      _F(CHARGE=LD,FONC_MULT=RAMP),
    ),
    COMPORTEMENT=(
      _F(GROUP_MA='CONC',RELATION='BETON_DOUBLE_DP',DEFORMATION='PETIT'),
      _F(GROUP_MA=('LBOT','LTOP','STIR'),RELATION='VMIS_ISOT_LINE',DEFORMATION='PETIT'),
      _F(GROUP_MA='PLATE',RELATION='ELAS',DEFORMATION='PETIT'),
      _F(GROUP_MA='CZM',RELATION='CZM_EXP_REG',DEFORMATION='PETIT'),
    ),
    INCREMENT=_F(LIST_INST=LI),
    NEWTON=_F(MATRICE='TANGENTE',REAC_ITER=1),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.E-4,ITER_GLOB_MAXI=50),
    SOLVEUR=_F(METHODE='MUMPS')
)

RES=CALC_CHAMP(reuse=RES,RESULTAT=RES,
               CONTRAINTE=('SIEF_ELNO',),
               VARI_INTERNE=('VARI_ELNO',),
               FORCE=('FORC_NODA',))

TF=POST_RELEVE_T(
 ACTION=_F(INTITULE='LOAD_REACTION',OPERATION='EXTRACTION',
           GROUP_NO='LOAD',NOM_CHAM='FORC_NODA',RESULTANTE='DZ',
           RESULTAT=RES,TOUT_ORDRE='OUI')
)
TU=POST_RELEVE_T(
 ACTION=_F(INTITULE='MIDSPAN_DISP',OPERATION='EXTRACTION',
           GROUP_NO='MID',NOM_CHAM='DEPL',NOM_CMP='DZ',
           RESULTAT=RES,TOUT_ORDRE='OUI')
)

IMPR_TABLE(TABLE=TF,UNITE=8)
IMPR_TABLE(TABLE=TU,UNITE=9)
IMPR_RESU(FORMAT='MED',UNITE=80,RESU=_F(RESULTAT=RES))

FIN()
"""
open("c25_cfrp.comm","w").write(comm)

export="""P memory_limit 6000
P time_limit 3600
F comm /analysis/c25_cfrp.comm D 1
F mail /analysis/c25_cfrp.mail D 20
F mess /analysis/c25_cfrp.mess R 6
F resu /analysis/force_table.txt R 8
F resu /analysis/disp_table.txt R 9
F rmed /analysis/c25_cfrp.rmed R 80
"""
open("c25_cfrp.export","w").write(export)

json.dump({
 "beam_mm":[L,B,H],"support_x_mm":[76.2,1143.0],"load_x_mm":609.6,
 "concrete_fc_MPa":fc,"concrete_E_MPa":E,"concrete_ft_MPa":ft,
 "concrete_law":"BETON_DOUBLE_DP","interface_law":"CZM_EXP_REG",
 "interface_initial":{"SIGM_C_MPa":4.0,"GC_N_per_mm":10.0,"PENA_ADHERENCE":0.00001},
 "cfrp":{"E_MPa":165000.0,"thickness_mm":4.0},
 "note":"Interface parameters are calibrated numerical assumptions selected to reproduce the experimentally observed intact-bond CFRP response, not measured adhesive properties. A midspan CFRP in-plane symmetry anchor (DX=DY=0 at one central interface node) removes rigid-body motion after severe interface softening without restraining vertical separation. Reinforcement is reconstructed from the thesis schematic/source data."
},open("c25_cfrp_metadata.json","w"),indent=2)

print("nodes",len(node_lines),"hex",len(hexes),"penta",len(cohesive_penta),"segments",len(segs))
print("concrete elements",len(conc),"plate",len(plate),"cohesive",len(czm))

# rerun Code_Aster after removing ORIE_FISSURE auto-orientation
