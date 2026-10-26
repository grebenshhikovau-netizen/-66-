import math,json
from pathlib import Path
P=Path(__file__).resolve().parent.parent;D=json.load(open(P/'data/source/projection.json'));C=D['projection'];M=D['mm_per_unit'];MC=math.log(math.tan(math.pi/4+math.radians(C['latmin'])/2))
def xy(lon,lat):
 if lon<0:lon+=360
 return M*(C['source_xmin']+(lon-C['lonmin'])*C['kx_per_degree']),M*(C['source_ymax']-(math.log(math.tan(math.pi/4+math.radians(lat)/2))-MC)*C['ky_per_mercator'])-1000
