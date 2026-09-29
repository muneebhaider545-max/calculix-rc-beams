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

def render_cell_scalar(name, filename, title, only_shell=False):
    vals=cell_scalars[name]
    ids=[i for i,t in enumerate(ctypes) if (t==9 if only_shell else t in (9,12))]
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
def find_key(d, patterns):
    for p in patterns:
        for k in d:
            if p.lower() in k.lower(): return k
    return None

disp_vec=find_key(point_vectors,['disp','displacement'])
von=find_key(cell_scalars,['von','mises'])
damage_keys=[k for k in cell_scalars if 'dam' in k.lower()]
energy=find_key(cell_scalars,['specific_energy','energy'])
epsp=find_key(cell_scalars,['epsp','plastic'])

made=[]
# 1 deformed geometry / displacement
if disp_vec:
    render_point_vector_mag(disp_vec,'Fig_A_Displacement_3D.png','C25–CFRP: OpenRadioss displacement field at final state')
    made.append('Fig_A_Displacement_3D.png')
else:
    # deformed final geometry with uniform styling
    vals=np.zeros(len(cells)); polys,pvals=cell_faces(None,vals)
    fig=plt.figure(figsize=(12,5.8),dpi=220); ax=fig.add_subplot(111,projection='3d')
    pc=Poly3DCollection(polys,facecolor='0.75',edgecolor=(0,0,0,.16),linewidths=.08); ax.add_collection3d(pc)
    setup_ax(ax); ax.set_title('C25–CFRP: OpenRadioss final deformed mesh geometry',fontsize=12,pad=12)
    fig.tight_layout(); fig.savefig(os.path.join(OUT,'Fig_A_Deformed_Mesh_3D.png'),dpi=600,bbox_inches='tight'); plt.close(fig)
    made.append('Fig_A_Deformed_Mesh_3D.png')

# 2 stress if available
if von:
    render_cell_scalar(von,'Fig_B_VonMises_3D.png','C25–CFRP: OpenRadioss von Mises stress contour')
    made.append('Fig_B_VonMises_3D.png')

# 3 each real damage field
for idx,k in enumerate(damage_keys[:3],start=1):
    fn=f'Fig_C{idx}_Damage_{idx}_3D.png'
    render_cell_scalar(k,fn,f'C25–CFRP: OpenRadioss concrete damage field — {k}')
    made.append(fn)

# 4 plastic strain/energy if available
if epsp:
    render_cell_scalar(epsp,'Fig_D_Plastic_Strain_3D.png','C25–CFRP: OpenRadioss equivalent plastic strain contour')
    made.append('Fig_D_Plastic_Strain_3D.png')
if energy:
    render_cell_scalar(energy,'Fig_E_Specific_Energy_3D.png','C25–CFRP: OpenRadioss specific-energy contour')
    made.append('Fig_E_Specific_Energy_3D.png')

# 5 CFRP shell-only real response using best available field
shell_field=von or (damage_keys[0] if damage_keys else epsp or energy)
if shell_field:
    render_cell_scalar(shell_field,'Fig_F_CFRP_Shell_Response.png',f'C25–CFRP: CFRP shell response — {shell_field}',only_shell=True)
    made.append('Fig_F_CFRP_Shell_Response.png')

# 6 load-deflection curve
if os.path.exists(CSV):
    rows=[]
    with open(CSV,newline='') as f:
        rr=csv.DictReader(f)
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
        fig.tight_layout(); fig.savefig(os.path.join(OUT,'Fig_G_Load_Deflection.png'),dpi=600,bbox_inches='tight'); plt.close(fig)
        made.append('Fig_G_Load_Deflection.png')

# 7 combined plate from generated raster files
imgs=[]
for fn in made[:6]:
    p=os.path.join(OUT,fn)
    if os.path.exists(p):
        imgs.append((fn,plt.imread(p)))
if imgs:
    n=len(imgs); cols=2; rows=math.ceil(n/cols)
    fig=plt.figure(figsize=(14,5.1*rows),dpi=180)
    for j,(fn,img) in enumerate(imgs,1):
        ax=fig.add_subplot(rows,cols,j); ax.imshow(img); ax.axis('off')
        ax.set_title(chr(96+j)+') '+fn.replace('.png','').replace('_',' '),fontsize=10)
    fig.suptitle('C25–CFRP — Genuine OpenRadioss 3D result fields',fontsize=14,y=.995)
    fig.tight_layout(); fig.savefig(os.path.join(OUT,'Fig_H_Combined_OpenRadioss_Plate.png'),dpi=450,bbox_inches='tight'); plt.close(fig)
    made.append('Fig_H_Combined_OpenRadioss_Plate.png')

with open(os.path.join(OUT,'README.txt'),'w') as f:
    f.write('These figures are rendered directly from the genuine OpenRadioss VTK/CSV outputs.\\n')
    f.write('They are diagnostic figures from the current trial model, which is not experimentally validated.\\n')
    f.write('Do not label unavailable result quantities as stress/damage if they are absent from available_fields.json.\\n\\n')
    f.write('Generated files:\\n'+'\\n'.join(made)+'\\n')

print('GENERATED',made)
