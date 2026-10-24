"""A continuous, geographically anchored terrace field for western/central Russia."""
import numpy as np
from scipy.ndimage import gaussian_filter
import contourpy
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union


def landscape_layers(data, config, main, project, clean):
    cfg = config['composition']
    lon, lat = data['lon'], data['lat']
    xx, yy = np.meshgrid(lon, lat)
    z = gaussian_filter(np.maximum(data['z'], 0), cfg['dem_smoothing_pixels'])
    anchors = np.array(cfg['longitude_anchors'])
    thresholds = np.array([np.interp(lon, anchors, row) for row in cfg['thresholds_m']])
    # Piecewise monotonic elevation remapping. Lowland steps are deliberately
    # amplified; all neighbouring provinces share one continuous scalar field.
    field = np.ones_like(z, dtype=float)
    low = np.zeros_like(z)
    for tier, high in enumerate(thresholds, 2):
        weight = np.clip((z-low) / np.maximum(high-low, 1), 0, 1)
        field += weight
        low = high
    # Broad Ural shoulders add local prominence without parallel buffered lines.
    # Each lobe is tied to a real section; the shoulders merge into adjacent plains.
    pr = config['projection']; scale = config['mm_per_unit']
    merc0 = np.log(np.tan(np.pi/4 + np.deg2rad(pr['latmin'])/2))
    x = (pr['source_xmin']+(xx-pr['lonmin'])*pr['kx_per_degree'])*scale
    y = (pr['source_ymax']-(np.log(np.tan(np.pi/4+np.deg2rad(yy)/2))-merc0)*pr['ky_per_mercator'])*scale
    prominence = np.zeros_like(z)
    for lo, la, sx, sy, strength in cfg['ural_shoulders']:
        cx=(pr['source_xmin']+(lo-pr['lonmin'])*pr['kx_per_degree'])*scale
        cy=(pr['source_ymax']-(np.log(np.tan(np.pi/4+np.deg2rad(la)/2))-merc0)*pr['ky_per_mercator'])*scale
        prominence=np.maximum(prominence,strength*np.exp(-.5*((x-cx)**2/sx**2+(y-cy)**2/sy**2)))
    field += prominence
    # Linked Byrranga and European upland shoulders articulate the interiors of
    # broad foundations. European uplands stay below the high mountain accents.
    north = np.zeros_like(z)
    for lo, la, sx, sy, strength in cfg['byrranga_shoulders']+cfg.get('european_shoulders',[]):
        cx=(pr['source_xmin']+(lo-pr['lonmin'])*pr['kx_per_degree'])*scale
        cy=(pr['source_ymax']-(np.log(np.tan(np.pi/4+np.deg2rad(la)/2))-merc0)*pr['ky_per_mercator'])*scale
        north=np.maximum(north,strength*np.exp(-.5*((x-cx)**2/sx**2+(y-cy)**2/sy**2)))
    field += np.minimum(north, np.maximum(0, 4.4-field))
    field = gaussian_filter(field, cfg['field_smoothing_pixels'])
    cg=contourpy.contour_generator(x=lon,y=lat,z=field,fill_type='OuterOffset')
    layers=[]
    for i in range(2,7):
        points, offsets=cg.filled(i,100); geoms=[]
        for ps, os in zip(points,offsets):
            rings=[ps[a:b] for a,b in zip(os[:-1],os[1:])]
            if rings:geoms.append(Polygon(rings[0],rings[1:]))
        g=project(unary_union(geoms)).intersection(main)
        g=clean(g,area=cfg['minimum_terrain_area_mm2'][i-2],closing=cfg['joining_radius_mm'])
        parts=list(g.geoms) if isinstance(g,MultiPolygon) else [g]
        g=unary_union([Polygon(p.exterior,[r.coords for r in p.interiors if Polygon(r).area*scale**2>=cfg['min_terrain_hole_area_mm2']]) for p in parts if isinstance(p,Polygon) and not p.is_empty])
        layers.append(g)
    return layers
