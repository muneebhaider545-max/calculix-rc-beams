import math, json, os, zipfile

L=1219.2; B=101.6; H=203.2
support_offset=76.2
fc_map={"C18":19.55,"C21":26.9,"C25":28.7}
exp={
"C18-CONT":(32.5,11.686),"C18-ST":(40.0,13.082),"C18-GFRP":(54.5,9.220),"C18-CFRP":(49.0,6.368),
"C21-CONT":(39.5,9.364),"C21-ST":(50.0,5.130),"C21-GFRP":(66.0,7.245),"C21-CFRP":(73.0,9.756),
"C25-CONT":(54.5,9.290),"C25-ST":(62.5,15.012),"C25-GFRP":(85.5,4.5733),"C25-CFRP":(99.5,20.058),
}
first_crack={
"C18-CONT":21.5,"C18-ST":21.5,"C18-GFRP":42.5,"C18-CFRP":40.0,
"C21-CONT":31.0,"C21-ST":31.0,"C21-GFRP":53.0,"C21-CFRP":65.0,
"C25-CONT":42.0,"C25-ST":52.0,"C25-GFRP":68.5,"C25-CFRP":93.5,
}
strengthening={
"CONT":{"type":"none","thickness_mm":None,"width_mm":None,"length_mm":None,"E_MPa":None,"note":"Unstrengthened control beam"},
"ST":{"type":"steel sheet","thickness_mm":4.0,"width_mm":101.6,"length_mm":1219.2,"E_MPa":210000.0,"note":"Gauge No. 7 steel sheet; fy=188.9 MPa; fu=298.4 MPa"},
"GFRP":{"type":"GFRP sheet","thickness_mm":None,"width_mm":101.6,"length_mm":990.6,"E_MPa":72300.0,"note":"39 in bonded length; thickness not reported in source; executable thickness must be calibrated/defined before nonlinear solution"},
"CFRP":{"type":"CFRP laminate","thickness_mm":4.0,"width_mm":101.6,"length_mm":1219.2,"E_MPa":165000.0,"note":"4 mm thick CFRP; tensile strength 2.8 GPa"},
}

os.makedirs("twelve_case_models",exist_ok=True)

def make_mesh():
    nx,ny,nz=24,2,4
    xs=[L*i/nx for i in range(nx+1)]
    ys=[B*i/ny for i in range(ny+1)]
    zs=[H*i/nz for i in range(nz+1)]
    nodes=[]; node={}
    nid=0
    for i,x in enumerate(xs):
      for j,y in enumerate(ys):
       for k,z in enumerate(zs):
        nid+=1; node[(i,j,k)]=nid; nodes.append((nid,x,y,z))
    elems=[]; eid=0
    for i in range(nx):
      for j in range(ny):
       for k in range(nz):
        eid+=1
        c=[node[(i,j,k)],node[(i+1,j,k)],node[(i+1,j+1,k)],node[(i,j+1,k)],
           node[(i,j,k+1)],node[(i+1,j,k+1)],node[(i+1,j+1,k+1)],node[(i,j+1,k+1)]]
        elems.append((eid,c))
    return nodes,elems

nodes,elems=make_mesh()

def abaqus_deck(case):
    grade,sys=case.split("-")
    fc=fc_map[grade]; Pu,d=exp[case]; Pcr=first_crack[case]
    Ec=4700*math.sqrt(fc)
    s=strengthening[sys]
    out=["*HEADING",f"{case} reduced 3D RC beam model","** Units: N, mm, MPa",
         f"** Experimental targets: fc={fc} MPa, Pcr={Pcr} kN, Pu={Pu} kN, delta_u={d} mm",
         "** Geometry source-backed. Concrete CDP/cohesive parameters require calibration before predictive use.",
         "*NODE"]
    out += [f"{n}, {x:.6f}, {y:.6f}, {z:.6f}" for n,x,y,z in nodes]
    out += ["*ELEMENT, TYPE=C3D8R, ELSET=CONCRETE"]
    out += [f"{e}, "+", ".join(map(str,c)) for e,c in elems]
    out += ["*MATERIAL, NAME=CONCRETE","*ELASTIC",f"{Ec:.4f}, 0.2",
            "*CONCRETE DAMAGED PLASTICITY","36., 0.1, 1.16, 0.667, 1e-5",
            "*SOLID SECTION, ELSET=CONCRETE, MATERIAL=CONCRETE",","]
    if sys!="CONT":
        out += [f"** Strengthening system: {s['type']}",
                f"** Length={s['length_mm']} mm; Width={s['width_mm']} mm; Thickness={s['thickness_mm']}; E={s['E_MPa']} MPa",
                f"** NOTE: {s['note']}"]
        if sys=="GFRP":
            out += ["** GFRP thickness intentionally NOT invented. Define shell/solid thickness before execution."]
    out += ["** Supports: x=76.2 mm and x=1143.0 mm; centre load x=609.6 mm.",
            "** Reinforcement/source details and cohesive interface are documented in accompanying metadata.",
            "** This deck is a model-definition package; final nonlinear execution requires validated material/interface data."]
    return "\n".join(out)+"\n"

manifest=[]
for case,(Pu,du) in exp.items():
    grade,sys=case.split("-")
    meta={
      "case":case,"beam_mm":[L,B,H],"support_offset_mm":support_offset,
      "fc_MPa":fc_map[grade],"first_crack_kN":first_crack[case],
      "ultimate_load_kN":Pu,"ultimate_deflection_mm":du,
      "strengthening":strengthening[sys],
      "mesh":{"concrete_nodes":375,"concrete_elements":192,"scheme":"24 x 2 x 4 C3D8R"},
      "status":"3D model definition generated; nonlinear solver validation not yet completed"
    }
    manifest.append(meta)
    open(f"twelve_case_models/{case}.inp","w").write(abaqus_deck(case))
    open(f"twelve_case_models/{case}.json","w").write(json.dumps(meta,indent=2))

open("twelve_case_models/manifest.json","w").write(json.dumps(manifest,indent=2))

section = """# 4. Three-dimensional finite-element model matrix

A twelve-model numerical matrix was established to reproduce the experimental program across three concrete strength levels and four strengthening configurations. The matrix comprised unstrengthened controls (C18-CONT, C21-CONT and C25-CONT), steel-sheet strengthened beams (C18-ST, C21-ST and C25-ST), GFRP-strengthened beams (C18-GFRP, C21-GFRP and C25-GFRP), and CFRP-strengthened beams (C18-CFRP, C21-CFRP and C25-CFRP). All models retained the experimental beam geometry of 1219.2 x 101.6 x 203.2 mm and used the measured concrete strengths of 19.55, 26.90 and 28.70 MPa for the nominal 18, 21 and 25 MPa series, respectively.

The reduced three-dimensional mesh uses 24 divisions along the beam axis, two divisions across the width and four through the depth, giving 192 C3D8R concrete elements and 375 concrete nodes before reinforcement and strengthening entities are introduced. The support centrelines are located 76.2 mm from each beam end, corresponding to a 1066.8 mm centre-to-centre support span, while the load is applied at midspan.

The external strengthening geometry follows the source experiments where dimensions were reported. CFRP is represented by a 4 mm thick, 101.6 mm wide laminate with a longitudinal elastic modulus of 165 GPa. Steel strengthening uses a 4 mm sheet with E = 210 GPa, fy = 188.9 MPa and fu = 298.4 MPa. The GFRP bonded length is 990.6 mm (39 in.), leaving 114.3 mm at each beam end. Because the source thesis does not report the GFRP laminate thickness, no experimental thickness has been invented in the numerical definition; that parameter must be established by product documentation or calibration before the GFRP nonlinear runs are presented as predictive simulations.

The experimental first-cracking load, ultimate load and corresponding peak-deflection values are retained as validation targets for each numerical case. Constitutive and interface parameters that were not measured experimentally, including post-peak concrete damage parameters and cohesive traction-separation properties, are treated as calibration variables rather than experimental inputs. Consequently, the present twelve-case package should be described as the three-dimensional numerical model matrix and validation framework until the nonlinear solver runs are completed and mesh/objective-response checks have been satisfied.
"""
open("twelve_case_models/Manuscript_Section_4_12_Case_Model_Matrix.md","w").write(section)

with zipfile.ZipFile("RC_Beam_12_Case_3D_Model_Matrix_REAL.zip","w",zipfile.ZIP_DEFLATED) as z:
    for root,dirs,files in os.walk("twelve_case_models"):
        for fn in files:
            fp=os.path.join(root,fn)
            z.write(fp,arcname=os.path.relpath(fp,"twelve_case_models"))
print("created",os.path.getsize("RC_Beam_12_Case_3D_Model_Matrix_REAL.zip"))
