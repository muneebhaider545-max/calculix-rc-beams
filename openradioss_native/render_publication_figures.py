#!/usr/bin/env python3
import csv, os, math, re, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

VTK='C25_CFRP_final.vtk'
CSV='C25_CFRP_load_deflection.csv'
OUT='publication_figures'
os.makedirs(OUT, exist_ok=True)

# ---------- VTK parser ----------
with open(VTK,'r',errors='ignore') as f:
    lines=f.readlines()

points=None; cells=[]; ctypes=[]; npts=0; ncells=0
point_scalars={}; point_vectors={}; cell_scalars={}; cell_vectors={}
i=0
while i < len(lines):
    s=lines[i].strip()
    if s.startswith('POINTS '):
        npts=int(s.split()[1]); vals=[]; i+=1
        while len(vals)<3*npts and i<len(lines):
            vals.extend(float(x) for x in lines[i].split()); i+=1
        points=np.array(vals[:3*npts],float).reshape(-1,3); continue
    if s.startswith('CELLS '):
        ncells=int(s.split()[1]); i+=1
        for _ in range(ncells):
            a=[int(x) for x in lines[i].split()]
            cells.append(a[1:1+a[0]]); i+=1
        continue
    if s.startswith('CELL_TYPES '):
        n=int(s.split()[1]); i+=1
        while len(ctypes)<n:
            ctypes.extend(int(x) for x in lines[i].split()); i+=1
        continue
    i+=1

if points is None or not cells:
    raise SystemExit('Failed to parse VTK geometry')

# Find POINT_DATA/CELL_DATA sections and parse arrays
section=None; expected=0; i=0
while i < len(lines):
    s=lines[i].strip()
    if s.startswith('POINT_DATA '):
        section='point'; expected=int(s.split()[1]); i+=1; continue
    if s.startswith('CELL_DATA '):
        section='cell'; expected=int(s.split()[1]); i+=1; continue
    if section and s.startswith('SCALARS '):
        parts=s.split(); name=parts[1]; comps=int(parts[3]) if len(parts)>3 and parts[3].isdigit() else 1
        i+=1
        if i<len(lines) and lines[i].strip().startswith('LOOKUP_TABLE'): i+=1
        vals=[]
        need=expected*comps
        while i<len(lines) and len(vals)<need:
            t=lines[i].strip()
            if re.match(r'^(SCALARS|VECTORS|POINT_DATA|CELL_DATA|FIELD)\b',t): break
            if t:
                try: vals.extend(float(x) for x in t.split())
                except: break
            i+=1
        if len(vals)>=need:
            arr=np.array(vals[:need],float)
            if comps>1: arr=arr.reshape(expected,comps)
            (point_scalars if section=='point' else cell_scalars)[name]=arr
        continue
    if section and s.startswith('VECTORS '):
        name=s.split()[1]; i+=1; vals=[]; need=expected*3
        while i<len(lines) and len(vals)<need:
            t=lines[i].strip()
            if re.match(r'^(SCALARS|VECTORS|POINT_DATA|CELL_DATA|FIELD)\b',t): break
            if t:
                try: vals.extend(float(x) for x in t.split())
                except: break
            i+=1
        if len(vals)>=need:
            arr=np.array(vals[:need],float).reshape(expected,3)
            (point_vectors if section=='point' else cell_vectors)[name]=arr
        continue
    i+=1

print('POINT_SCALARS', [(k,float(np.nanmin(v)),float(np.nanmax(v))) for k,v in point_scalars.items()])
print('POINT_VECTORS', [(k,float(np.nanmin(np.linalg.norm(v,axis=1))),float(np.nanmax(np.linalg.norm(v,axis=1)))) for k,v in point_vectors.items()])
print('CELL_SCALARS', [(k,float(np.nanmin(v)),float(np.nanmax(v))) for k,v in cell_scalars.items()])
print('CELL_VECTORS', [(k,float(np.nanmin(np.linalg.norm(v,axis=1))),float(np.nanmax(np.linalg.norm(v,axis=1)))) for k,v in cell_vectors.items()])

with open(os.path.join(OUT,'available_fields.json'),'w') as f:
    json.dump({
        'point_scalars':list(point_scalars),
        'point_vectors':list(point_vectors),
        'cell_scalars':list(cell_scalars),
        'cell_vectors':list(cell_vectors),
        'npoints':len(points),'ncells':len(cells)
    },f,indent=2)

hexfaces=((0,1,2,3),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
def cell_faces(cell_ids=None, cell_values=None):
    polys=[]; vals=[]
    ids=range(len(cells)) if cell_ids is None else cell_ids
    for ci in ids:
        c=cells[ci]; ct=ctypes[ci] if ci<len(ctypes) else None
        cv=(cell_values[ci] if cell_values is not None else 0.0)
        if ct==12 and len(c)>=8:
            for face in hexfaces:
                polys.append([points[c[j]] for j in face]); vals.append(cv)
        elif ct==9 and len(c)>=4:
            polys.append([points[c[j]] for j in (0,1,2,3)]); vals.append(cv)
    return polys,np.array(vals,float)

def setup_ax(ax):
    mins=points.min(axis=0); maxs=points.max(axis=0); ctr=(mins+maxs)/2; span=max(maxs-mins)
    ax.set_xlim(ctr[0]-0.52*span,ctr[0]+0.52*span)
    ax.set_ylim(ctr[1]-0.20*span,ctr[1]+0.20*span)
    ax.set_zlim(ctr[2]-0.22*span,ctr[2]+0.22*span)
    ax.set_box_aspect((3.2,0.8,0.8)); ax.view_init(elev=18,azim=-62)
    ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)'); ax.set_zlabel('Z (mm)')
    ax.grid(False)

def render_cell_scalar(name, filename, title, only_shell=False, only_solid=False):
    vals=cell_scalars[name]
    if only_shell:
        ids=[i for i,t in enumerate(ctypes) if t==9]
    elif only_solid:
        ids=[i for i,t in enumerate(ctypes) if t==12]
    else:
        ids=[i for i,t in enumerate(ctypes) if t in (9,12)]
    polys,pvals=cell_faces(ids,vals)
    vmin=float(np.nanmin(pvals)); vmax=float(np.nanmax(pvals))
    if not math.isfinite(vmin): vmin=0
    if not math.isfinite(vmax) or abs(vmax-vmin)<1e-14: vmax=vmin+1
    norm=plt.Normalize(vmin,vmax); cmap=plt.get_cmap('viridis')
    fig=plt.figure(figsize=(12,5.8),dpi=220); ax=fig.add_subplot(111,projection='3d')
    pc=Poly3DCollection(polys,linewidths=.05); pc.set_facecolor(cmap(norm(pvals))); pc.set_edgecolor((0,0,0,.08)); ax.add_collection3d(pc)
    setup_ax(ax); ax.set_title(title,fontsize=12,pad=12)
    sm=plt.cm.ScalarMappable(norm=norm,cmap=cmap); sm.set_array([])
    cb=fig.colorbar(sm,ax=ax,shrink=.72,pad=.04); cb.set_label(name.replace('_',' '))
    fig.tight_layout(); fig.savefig(os.path.join(OUT,filename),dpi=600,bbox_inches='tight'); plt.close(fig)

def render_point_vector_mag(name, filename, title):
    vec=point_vectors[name]; mag=np.linalg.norm(vec,axis=1)
    # assign cell mean nodal magnitude
    cvals=np.array([np.mean(mag[np.array(c,dtype=int)]) for c in cells])
    polys,pvals=cell_faces(None,cvals)
    vmin=float(np.nanmin(pvals)); vmax=float(np.nanmax(pvals))
    if abs(vmax-vmin)<1e-14: vmax=vmin+1
    norm=plt.Normalize(vmin,vmax); cmap=plt.get_cmap('viridis')
    fig=plt.figure(figsize=(12,5.8),dpi=220); ax=fig.add_subplot(111,projection='3d')
    pc=Poly3DCollection(polys,linewidths=.05); pc.set_facecolor(cmap(norm(pvals))); pc.set_edgecolor((0,0,0,.08)); ax.add_collection3d(pc)
    setup_ax(ax); ax.set_title(title,fontsize=12,pad=12)
    sm=plt.cm.ScalarMappable(norm=norm,cmap=cmap); sm.set_array([])
    cb=fig.colorbar(sm,ax=ax,shrink=.72,pad=.04); cb.set_label(f'{name} magnitude')
    fig.tight_layout(); fig.savefig(os.path.join(OUT,filename),dpi=600,bbox_inches='tight'); plt.close(fig)

# Candidate real result fields
# IMPORTANT: 3DELEM fields belong to the concrete brick part; 2DELEM fields belong to the CFRP shell part.
disp_vec='Displacement' if 'Displacement' in point_vectors else None
concrete_von='3DELEM_Von_Mises' if '3DELEM_Von_Mises' in cell_scalars else None
concrete_damage=[k for k in ['3DELEM_Damage_1','3DELEM_Damage_2','3DELEM_Damage_3'] if k in cell_scalars]
concrete_energy='3DELEM_Specific_Energy' if '3DELEM_Specific_Energy' in cell_scalars else None
cfrp_von='2DELEM_Von_Mises' if '2DELEM_Von_Mises' in cell_scalars else None
cfrp_energy='2DELEM_Specific_Energy' if '2DELEM_Specific_Energy' in cell_scalars else None

made=[]

# A: displacement
if disp_vec:
    render_point_vector_mag(disp_vec,'Fig_A_Displacement_3D.png','C25–CFRP: OpenRadioss displacement magnitude at final state')
    made.append('Fig_A_Displacement_3D.png')

# B: concrete 3D von Mises
if concrete_von:
    render_cell_scalar(concrete_von,'Fig_B_Concrete_VonMises_3D.png','C25–CFRP: concrete von Mises stress — OpenRadioss 3D bricks',only_solid=True)
    made.append('Fig_B_Concrete_VonMises_3D.png')

# C1-C3: genuine concrete LAW24 damage variables
for idx2,k in enumerate(concrete_damage,start=1):
    fn=f'Fig_C{idx2}_Concrete_Damage_{idx2}_3D.png'
    render_cell_scalar(k,fn,f'C25–CFRP: concrete LAW24 damage variable {idx2} — OpenRadioss',only_solid=True)
    made.append(fn)

# D: CFRP shell von Mises
if cfrp_von:
    render_cell_scalar(cfrp_von,'Fig_D_CFRP_VonMises_Shell.png','C25–CFRP: CFRP shell von Mises stress — OpenRadioss',only_shell=True)
    made.append('Fig_D_CFRP_VonMises_Shell.png')
elif cfrp_energy:
    render_cell_scalar(cfrp_energy,'Fig_D_CFRP_Specific_Energy_Shell.png','C25–CFRP: CFRP shell specific energy — OpenRadioss',only_shell=True)
    made.append('Fig_D_CFRP_Specific_Energy_Shell.png')

# E: concrete energy (optional supporting diagnostic)
if concrete_energy:
    render_cell_scalar(concrete_energy,'Fig_E_Concrete_Specific_Energy_3D.png','C25–CFRP: concrete specific energy — OpenRadioss 3D bricks',only_solid=True)
    made.append('Fig_E_Concrete_Specific_Energy_3D.png')

# F: load–deflection curve
if os.path.exists(CSV):
    rows=[]
    with open(CSV,newline='') as fcsv:
        rr=csv.DictReader(fcsv)
        for r in rr:
            try: rows.append((abs(float(r['midspan_DZ_mm'])),float(r['load_kN'])))
            except: pass
    if rows:
        x=np.array([r[0] for r in rows]); y=np.array([r[1] for r in rows])
        fig=plt.figure(figsize=(7.2,5.2),dpi=220); ax=fig.add_subplot(111)
        ax.plot(x,y,linewidth=1.6,label='OpenRadioss trial')
        ax.scatter([20.058],[99.5],s=34,marker='o',label='Experimental ultimate point')
        ax.set_xlabel('Midspan deflection (mm)'); ax.set_ylabel('Load (kN)')
        ax.set_title('C25–CFRP load–deflection response')
        ax.grid(True,alpha=.25); ax.legend(frameon=False)
        fig.tight_layout(); fig.savefig(os.path.join(OUT,'Fig_F_Load_Deflection.png'),dpi=600,bbox_inches='tight'); plt.close(fig)
        made.append('Fig_F_Load_Deflection.png')

# Combined six-panel plate: displacement, concrete stress, three concrete damage variables, CFRP stress
preferred_plate=[
    'Fig_A_Displacement_3D.png',
    'Fig_B_Concrete_VonMises_3D.png',
    'Fig_C1_Concrete_Damage_1_3D.png',
    'Fig_C2_Concrete_Damage_2_3D.png',
    'Fig_C3_Concrete_Damage_3_3D.png',
    'Fig_D_CFRP_VonMises_Shell.png'
]
imgs=[]
for fn in preferred_plate:
    p=os.path.join(OUT,fn)
    if os.path.exists(p):
        imgs.append((fn,plt.imread(p)))
if imgs:
    n=len(imgs); cols=2; rows=math.ceil(n/cols)
    fig=plt.figure(figsize=(14,5.1*rows),dpi=180)
    for j,(fn,img) in enumerate(imgs,1):
        ax=fig.add_subplot(rows,cols,j); ax.imshow(img); ax.axis('off')
        label=chr(96+j)+')'
        pretty=fn.replace('.png','').replace('_',' ')
        ax.set_title(label+' '+pretty,fontsize=10)
    fig.suptitle('C25–CFRP — genuine OpenRadioss 3D result fields',fontsize=14,y=.995)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT,'Fig_G_Combined_OpenRadioss_Plate.png'),dpi=450,bbox_inches='tight')
    plt.close(fig)
    made.append('Fig_G_Combined_OpenRadioss_Plate.png')

with open(os.path.join(OUT,'README.txt'),'w') as ftxt:
    ftxt.write('These figures are rendered directly from the genuine OpenRadioss VTK/CSV outputs.\n')
    ftxt.write('3DELEM fields are used for concrete brick results; 2DELEM fields are used for the CFRP shell.\n')
    ftxt.write('The current solver model is a diagnostic trial and is not experimentally validated.\n')
    ftxt.write('Peak reaction in this trial remains approximately 0.995 kN versus 99.5 kN experimental.\n')
    ftxt.write('Therefore the figures are real solver outputs but should not yet be used as validated manuscript evidence.\n\n')
    ftxt.write('Generated files:\n'+'\n'.join(made)+'\n')

print('GENERATED',made)
