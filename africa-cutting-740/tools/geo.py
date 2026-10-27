"""Use the source map's geographic control points without changing its projection."""
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import RBFInterpolator
P=Path(__file__).resolve().parent.parent;C=json.load(open(P/'data/source/geographic-controls.json'));D=json.load(open(P/'data/source/projection.json'));W=RBFInterpolator(np.array([[c[1],c[2]]for c in C]),np.array([[c[3],c[4]]for c in C]),kernel='thin_plate_spline',smoothing=2)
def xy(lon,lat):
 q=W(np.array([[lon,lat]]))[0];return q[0]*D['mm_per_unit'],q[1]*D['mm_per_unit']+D['svg_y_offset_mm']
