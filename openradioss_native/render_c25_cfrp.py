#!/usr/bin/env python3
import re, os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

vtk='C25_CFRP_final.vtk'
if not os.path.exists(vtk):
    raise SystemExit("VTK not found")

with open(vtk,'r',errors='ignore') as f:
    lines=f.readlines()

# Parse points
npts=0; points=None; cells=[]; ctypes=[]
i=0
while i < len(lines):
    s=lines[i].strip()
    if s.startswith('POINTS '):
        npts=int(s.split()[1])
        vals=[]
        i+=1
        while len(vals) < 3*npts:
            vals.extend(float(x) for x in lines[i].split())
            i+=1
        points=np.array(vals[:3*npts],dtype=float).reshape((-1,3))
        continue
    if s.startswith('CELLS '):
        nc=int(s.split()[1])
        i+=1
        for _ in range(nc):
            a=[int(x) for x in lines[i].split()]
            cells.append(a[1:1+a[0]])
            i+=1
        continue
    if s.startswith('CELL_TYPES '):
        nc=int(s.split()[1]); i+=1
        while len(ctypes)<nc:
            ctypes.extend(int(x) for x in lines[i].split()); i+=1
        continue
    i+=1

if points is None or not cells:
    raise SystemExit("Could not parse VTK geometry")

# Parse cell scalar fields
cell_scalars={}
i=0
in_cell=False
ncells=len(cells)
while i < len(lines):
    s=lines[i].strip()
    if s.startswith('CELL_DATA '):
        in_cell=True; i+=1; continue
    if in_cell and s.startswith('SCALARS '):
        parts=s.split()
        name=parts[1]
        i+=1
        if i < len(lines) and lines[i].strip().startswith('LOOKUP_TABLE'):
            i+=1
        vals=[]
        while i < len(lines) and len(vals) < ncells:
            t=lines[i].strip()
            if (t.startswith('SCALARS ') or t.startswith('VECTORS ') or
                t.startswith('FIELD ') or t.startswith('POINT_DATA ') or
                t.startswith('CELL_DATA ')):
                break
            if t:
                try: vals.extend(float(x) for x in t.split())
                except: break
            i+=1
        if len(vals)>=ncells:
            cell_scalars[name]=np.array(vals[:ncells],dtype=float)
        continue
    i+=1

# Choose a meaningful field
preferred=['ELEM_Damage_1','ELEM_Damage_2','ELEM_Damage_3',
           'ELEM_VonMises','ELEM_Von_Mises','VON_MISES','vonMises']
field=None
for p in preferred:
    if p in cell_scalars:
        field=p; break
if field is None and cell_scalars:
    # pick scalar with greatest nonzero range
    field=max(cell_scalars, key=lambda k: float(np.nanmax(cell_scalars[k])-np.nanmin(cell_scalars[k])))

vals=cell_scalars.get(field, np.zeros(ncells))

# Hexahedron faces, VTK_HEXAHEDRON=12; quad=9
hexfaces=((0,1,2,3),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
quadface=((0,1,2,3),)

polys=[]; pvals=[]
for ci,c in enumerate(cells):
    ctype=ctypes[ci] if ci < len(ctypes) else None
    if ctype==12 and len(c)>=8:
        for face in hexfaces:
            polys.append([points[c[j]] for j in face]); pvals.append(vals[ci])
    elif ctype==9 and len(c)>=4:
        polys.append([points[c[j]] for j in quadface[0]]); pvals.append(vals[ci])

pvals=np.array(pvals) if pvals else np.array([0.0])
vmin=float(np.nanmin(pvals)); vmax=float(np.nanmax(pvals))
if not math.isfinite(vmin): vmin=0.0
if not math.isfinite(vmax): vmax=1.0
if abs(vmax-vmin)<1e-12: vmax=vmin+1.0
norm=plt.Normalize(vmin,vmax)
cmap=plt.get_cmap('viridis')

fig=plt.figure(figsize=(14,7),dpi=180)
ax=fig.add_subplot(111,projection='3d')
pc=Poly3DCollection(polys, linewidths=0.05, alpha=0.98)
pc.set_facecolor(cmap(norm(pvals)))
pc.set_edgecolor((0,0,0,0.08))
ax.add_collection3d(pc)

# deformed geometry bounds
mins=points.min(axis=0); maxs=points.max(axis=0)
ctr=(mins+maxs)/2
span=max(maxs-mins)
ax.set_xlim(ctr[0]-0.52*span,ctr[0]+0.52*span)
ax.set_ylim(ctr[1]-0.28*span,ctr[1]+0.28*span)
ax.set_zlim(ctr[2]-0.28*span,ctr[2]+0.28*span)
ax.set_box_aspect((2.8,0.8,0.8))
ax.view_init(elev=22, azim=-62)
ax.set_xlabel('X (mm)')
ax.set_ylabel('Y (mm)')
ax.set_zlabel('Z (mm)')
ax.set_title('C25–CFRP Beam — Genuine OpenRadioss 3D Final State\\n'
             + (f'Contour: {field}' if field else 'Deformed geometry'))
mappable=plt.cm.ScalarMappable(norm=norm,cmap=cmap)
mappable.set_array([])
cb=fig.colorbar(mappable, ax=ax, shrink=0.65, pad=0.06)
cb.set_label(field if field else 'Scalar')
fig.tight_layout()
out='C25_CFRP_OpenRadioss_3D_visual.png'
fig.savefig(out,bbox_inches='tight')
print(f'WROTE {out}')
print('FIELD',field,'RANGE',vmin,vmax)
