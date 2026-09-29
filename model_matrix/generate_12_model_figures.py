#!/usr/bin/env python3
import os, math, csv, json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT="model_matrix_outputs"
os.makedirs(OUT, exist_ok=True)

L=1219.2; B=101.6; H=203.2
support_left=76.2; support_right=L-76.2
cover=38.1
fc_measured={18:19.55,21:26.90,25:28.70}

specs=[]
for grade in [18,21,25]:
    specs += [
        dict(label=f"C{grade}-CONT", grade=grade, system="Control", thickness=0.0, bond_start=None, bond_end=None),
        dict(label=f"C{grade}-ST", grade=grade, system="Steel", thickness=4.0, bond_start=0.0, bond_end=L),
        dict(label=f"C{grade}-GFRP", grade=grade, system="GFRP", thickness=None, bond_start=114.3, bond_end=L-114.3),
        dict(label=f"C{grade}-CFRP", grade=grade, system="CFRP", thickness=4.0, bond_start=0.0, bond_end=L),
    ]

experimental = {
"C18-CONT": (32.5,11.686), "C18-ST":(40.0,13.082), "C18-GFRP":(54.5,9.220), "C18-CFRP":(49.0,6.368),
"C21-CONT": (39.5,9.364), "C21-ST":(50.0,5.130), "C21-GFRP":(66.0,7.245), "C21-CFRP":(73.0,9.756),
"C25-CONT": (54.5,9.290), "C25-ST":(62.5,15.012), "C25-GFRP":(85.5,4.5733), "C25-CFRP":(99.5,20.058),
}
first_crack = {
"C18-CONT":21.5, "C18-ST":21.5, "C18-GFRP":42.5, "C18-CFRP":40.0,
"C21-CONT":31.0, "C21-ST":31.0, "C21-GFRP":53.0, "C21-CFRP":65.0,
"C25-CONT":42.0, "C25-ST":52.0, "C25-GFRP":68.5, "C25-CFRP":93.5,
}

def box_faces(x0,x1,y0,y1,z0,z1):
    p=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
                [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]])
    return [[p[i] for i in idx] for idx in
            [(0,1,2,3),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]]

def draw_model(ax, spec):
    # concrete translucent solid
    pc=Poly3DCollection(box_faces(0,L,0,B,0,H), linewidths=.35, edgecolors='0.45', alpha=.16)
    pc.set_facecolor('0.72'); ax.add_collection3d(pc)

    # coarse FE grid: 24 x 2 x 4
    for x in np.linspace(0,L,25):
        for y in [0,B]:
            ax.plot([x,x],[y,y],[0,H],lw=.25,color='0.6')
        for z in [0,H]:
            ax.plot([x,x],[0,B],[z,z],lw=.25,color='0.6')
    for z in np.linspace(0,H,5):
        ax.plot([0,L],[0,0],[z,z],lw=.25,color='0.6')
        ax.plot([0,L],[B,B],[z,z],lw=.25,color='0.6')
    for y in np.linspace(0,B,3):
        ax.plot([0,L],[y,y],[0,0],lw=.25,color='0.6')
        ax.plot([0,L],[y,y],[H,H],lw=.25,color='0.6')

    # longitudinal steel: 2 bottom, 2 top
    ys=[cover,B-cover]
    for y in ys:
        ax.plot([0,L],[y,y],[cover,cover],lw=2.2,color='0.2')
        ax.plot([0,L],[y,y],[H-cover,H-cover],lw=1.7,color='0.2')
    # stirrups schematic
    for x in [76.2,254,431.8,609.6,787.4,965.2,1143]:
        yy=[cover,B-cover,B-cover,cover,cover]
        zz=[cover,cover,H-cover,H-cover,cover]
        xx=[x]*5
        ax.plot(xx,yy,zz,lw=1.0,color='0.25')

    # strengthening layer
    if spec["system"]!="Control":
        x0=spec["bond_start"]; x1=spec["bond_end"]
        z=-5
        system=spec["system"]
        if system=="Steel": fc='0.35'
        elif system=="CFRP": fc='0.05'
        else: fc='0.50'
        ps=Poly3DCollection(box_faces(x0,x1,0,B,z-2,z+2),linewidths=.5,edgecolors='0.05',alpha=.9)
        ps.set_facecolor(fc); ax.add_collection3d(ps)

    # supports
    ax.scatter([support_left,support_right],[B/2,B/2],[-25,-25],marker='^',s=80,c='0.1',depthshade=False)
    # loading arrow
    ax.quiver(L/2,B/2,H+95,0,0,-75,arrow_length_ratio=.22,linewidth=2.0,color='0.1')
    ax.text(L/2,B/2,H+115,"P",ha="center",va="bottom",fontsize=9,fontweight='bold')

    pu, d=experimental[spec["label"]]
    ttxt = "not reported" if spec["thickness"] is None else f'{spec["thickness"]:.1f} mm'
    ax.set_title(f'{spec["label"]}\n{spec["system"]}; f′c={fc_measured[spec["grade"]]:.2f} MPa; Pu={pu:g} kN',fontsize=8.5,pad=3)
    ax.set_xlim(0,L); ax.set_ylim(-20,B+20); ax.set_zlim(-60,H+130)
    ax.set_box_aspect((L,230,260))
    ax.view_init(elev=18,azim=-58)
    ax.set_axis_off()

# individual figures
for s in specs:
    fig=plt.figure(figsize=(9,3.6),dpi=220)
    ax=fig.add_subplot(111,projection='3d')
    draw_model(ax,s)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT,f'{s["label"]}_3D_model.png'),bbox_inches='tight',pad_inches=.05)
    plt.close(fig)

# combined 12-panel plate
fig=plt.figure(figsize=(14,10.8),dpi=220)
for i,s in enumerate(specs,1):
    ax=fig.add_subplot(3,4,i,projection='3d')
    draw_model(ax,s)
fig.suptitle("Three-dimensional finite-element model matrix for the 12 experimental configurations",fontsize=14,fontweight='bold',y=.995)
fig.tight_layout(rect=[0,0,1,.98])
fig.savefig(os.path.join(OUT,"Figure_15_12_case_3D_model_matrix.png"),bbox_inches='tight',pad_inches=.08)
plt.close(fig)

# metadata matrix
rows=[]
for s in specs:
    pu,d=experimental[s["label"]]
    rows.append({
        "Specimen":s["label"],"System":s["system"],"Nominal_fc_MPa":s["grade"],
        "Measured_fc_MPa":fc_measured[s["grade"]],"First_crack_kN":first_crack[s["label"]],
        "Ultimate_kN":pu,"Peak_deflection_mm":d,
        "Beam_L_mm":L,"Beam_B_mm":B,"Beam_H_mm":H,
        "Support_left_mm":support_left,"Support_right_mm":support_right,
        "Strengthening_thickness_mm":("" if s["thickness"] is None else s["thickness"]),
        "Bond_start_mm":("" if s["bond_start"] is None else s["bond_start"]),
        "Bond_end_mm":("" if s["bond_end"] is None else s["bond_end"]),
        "Note":("GFRP thickness not reported in source; visualization uses schematic layer only." if s["system"]=="GFRP" else "")
    })
with open(os.path.join(OUT,"12_case_model_matrix.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

meta={
 "figure":"Figure_15_12_case_3D_model_matrix.png",
 "status":"pre-solver model architecture only; not numerical result contours",
 "mesh_visualization":"24 x 2 x 4 concrete cells shown schematically",
 "source_supported_geometry":{"beam_mm":[L,B,H],"support_offsets_mm":[76.2,76.2],"CFRP_thickness_mm":4.0,"steel_thickness_mm":4.0,"GFRP_bond_length_mm":990.6},
 "source_gap":"GFRP laminate thickness not reported; no numerical thickness is asserted in the figure."
}
open(os.path.join(OUT,"model_matrix_metadata.json"),"w").write(json.dumps(meta,indent=2))
print(json.dumps(meta,indent=2))
