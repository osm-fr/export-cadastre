#!/usr/bin/env python
# -*- coding: utf-8 -*- 
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with it. If not, see <http://www.gnu.org/licenses/>.


"""
Fonction de transformation entre différentes projections liées au cadastre.
"""

import sys
import math

#sys.path.append(os.path.dirname(os.path.dirname(__file__)))


from .geometry import Point, BoundingBox
try:
    from osgeo import osr    # apt-get install python-gdal
except:
    sys.stderr.write("ERROR: osgeo.osr python lib not found; do \n")
    sys.stderr.write("    sudo apt-get install python-gdal\n")
    sys.exit(-1)
    
from .globals import EARTH_CIRCUMFERENCE_IN_METER


class Transform(object):
    def __init__(self):
        pass
    def transform_point(self, point):
        raise Exception("not implemented")
    def transform_points(self, points):
        return [self.transform_point(p) for p in points]
    def transform_bbox(self, bbox):
        p1 = self.transform_point(bbox.p1())
        p2 = self.transform_point(bbox.p2())
        return BoundingBox.of_points([p1,p2])


class CadastreToOSMTransform(Transform):
    """Transformation from IGNF coordinates used by the cadastre
       into coordinates used by OSM"""
    def __init__(self, cadastre_IGNF_code):
        Transform.__init__(self)
        source = osr.SpatialReference();
        target = osr.SpatialReference();
        source.ImportFromProj4(
            "+init=IGNF:" + cadastre_IGNF_code + " +wktext");
        target.ImportFromEPSG(4326);
        self.transformation = osr.CoordinateTransformation(
            source, target)
    def transform_point(self, point):
        x,y,z = self.transformation.TransformPoint(point[0], point[1], 0.0)
        return Point(x,y)


class OSMToCadastreTransform(Transform):
    """Transformation from cordinates used by OSM 
       to IGNF coordinates used by the cadastre"""
    def __init__(self, cadastre_IGNF_code):
        Transform.__init__(self)
        source = osr.SpatialReference();
        target = osr.SpatialReference();
        target.ImportFromProj4(
            "+init=IGNF:" + cadastre_IGNF_code + " +wktext");
        source.ImportFromEPSG(4326);
        self.transformation = osr.CoordinateTransformation(
            source, target)
    def transform_point(self, point):
        x,y,z = self.transformation.TransformPoint(point[0], point[1], 0.0)
        return Point(x,y)


class LinearTransform(Transform):
    """Linear Transformation"""
    def __init__(self, input_bbox,output_bbox):
        Transform.__init__(self)
        ix1, iy1, ix2, iy2 = input_bbox
        ox1, oy1, ox2, oy2 = output_bbox
        self.xfactor = (ox2 - ox1) / (ix2 - ix1)
        self.yfactor = (oy2 - oy1) / (iy2 - iy1)
        self.ix1 = ix1
        self.iy1 = iy1
        self.ox1 = ox1
        self.oy1 = oy1
    def transform_point(self, point):
        return Point(
            self.ox1 + (point[0] - self.ix1) * self.xfactor,
            self.oy1 + (point[1] - self.iy1) * self.yfactor)


class PDFToCadastreTransform(LinearTransform):
    """Transformation from the coordinates used inside a PDF, into the coordinate of the cadastre"""
    def __init__(self, pdf_bbox, cadastre_bbox):
        LinearTransform.__init__(self, pdf_bbox, cadastre_bbox)


class CompositeTransform(Transform):
    """Composition of many transformations"""
    def __init__(self, *transforms):
        Transform.__init__(self)
        self.transforms = transforms
    def transform_point(self, point):
        for t in self.transforms:
            point = t.transform_point(point)
        return point


def get_centered_metric_equirectangular_transformation_from_osm(osm_data):
  """ return a Transform from OSM data WSG84 lon/lat coordinate system
      to an equirectangular projection centered on the center of the data,
      with a unit ~ 1 meter at the center
  """
  bbox = BoundingBox(*osm_data.bbox())
  center = bbox.center()
  bb1 = (center.x, center.y, center.x + 360, center.y + 360)
  bb2 = (0, 0, EARTH_CIRCUMFERENCE_IN_METER*math.cos(center.y*math.pi/180), EARTH_CIRCUMFERENCE_IN_METER)
  inputTransform = LinearTransform(bb1, bb2)
  outputTransform = LinearTransform(bb2, bb1)
  return inputTransform, outputTransform


