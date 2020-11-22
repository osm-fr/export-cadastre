#!/usr/bin/env python3
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


import sys
import math
import rtree.index
from .tools import peek

try:
    from shapely.geometry.point import Point as ShapelyPoint
except:
    import traceback
    traceback.print_exc()
    sys.stderr.write("Please install Shapely (pip install shapely)\n")
    sys.exit(-1)


def orthoprojection_on_segment_ab_of_point_c(a,b,c):
    """ Retourne la projection orthogonale du point c sur le segment [a,b],
        ou None si c n'est pas en face."""
    # http://www.codeguru.com/forum/printthread.php?t=194400
    xa,ya = a
    xb,yb = b
    xc,yc = c
    r_numerator = (xc-xa)*(xb-xa) + (yc-ya)*(yb-ya)
    r_denomenator = (xb-xa)*(xb-xa) + (yb-ya)*(yb-ya)
    if r_denomenator == 0:
        return a;
    r = r_numerator / r_denomenator;
    if r<0 or r>1:
        return None
    elif r == 0:
        return a
    elif r==1:
        return b
    else:
        x = xa + r*(xb-xa)
        y = ya + r*(yb-ya)
        return (x,y)

def angle_projection_on_segment_ab_of_point_c(a,b,c,angle):
    """ Retourne la projection du point c sur le segment [a,b]
        en suivant la direction angle, ou None si le segment
        n'est pas en face."""
    if a == b:
        return None
    #http://scalion.free.fr/getinter.htm#paulbourke
    x1,y1 = a
    x2,y2 = b
    x3,y3 = c
    x4,y4 = x3 + math.cos(angle), y3 + math.sin(angle)
    r_numerator = (x4-x3)*(y1-y3) - (y4-y3)*(x1-x3)
    r_denomenator = (y4-y3)*(x2-x1) - (x4-x3)*(y2-y1)
    if r_denomenator == 0:
        return None
    r = r_numerator / r_denomenator;
    if r<0 or r>1:
        return None
    elif r == 0:
        return a
    elif r==1:
        return b
    else:
        x = x1 + r*(x2-x1)
        y = y1 + r*(y2-y1)
        return (x,y)


def cartesien_2_polaire(x,y):
    r = math.sqrt(x*x+y*y)
    if r == 0:
        t = 0
    elif x > 0:
        t = math.atan(y/x)
    elif x < 0 and y >= 0:
        t = math.atan(y/x) + math.pi
    elif x < 0 and y < 0:
        t = math.atan(y/x) - math.pi
    elif x == 0 and y > 0:
        t = math.pi/2
    elif x == 0 and y < 0:
        t = - math.pi/2
    return (r,t)

def incidence(a, b, angle):
    """retourne l'incidence de l'angle par rapport au segment ab"""
    ax,ay = a
    bx,by = b
    _, ab_angle = cartesien_2_polaire(bx - ax, by - ay)
    incidence = abs(math.pi/2 - ((angle - ab_angle) % math.pi))
    return incidence



class Point(object):
    __zero__ = ShapelyPoint(0,0)
    __slots__  = ("x","y")
    def __init__(self, x,y):
        self.x = x
        self.y = y
    def __len__(self):
        return 2
    def __getitem__(self, key):
        if key == 0: return self.x
        if key == 1: return self.y
        raise IndexError()
    def minus(self, p):
        x,y = p
        return Point(self.x - x, self.y - y)
    def norm(self):
      return self.distance(Point.__zero__)
    def square_norm(self):
      return (self.x * self.x) + (self.y * self.y)
    def distance(self, other):
        if type(other) in [tuple, list]:
            other=Point(*other)
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx*dx + dy*dy)
    def square_distance(self, other):
        if type(other) in [tuple, list]:
            other=Point(*other)
        dx = other.x - self.x
        dy = other.y - self.y
        return dx*dx + dy*dy
    def dot_product(self, p):
        x,y = p
        return self.x*x + self.y*y
    def angle(p1, p2):
      if type(p2) != Point: p2 = Point(p2)
      d = p1.norm() * p2.norm()
      if d == 0:
          return 0
      else:
          v = p1.dot_product(p2) / d
          if v > 1: v = 1
          if v <-1: v =-1
          return math.acos(v)
    def area(p1, p2):
      if type(p2) != Point: p2 = Point(p2)
      return 0.5 * abs(p1.x * p2.y - p2.x * p1.y)

def maxdiff(points1, points2):
    return max(
        [ max((abs(points1[i][0] - points2[i][0]),
               abs(points1[i][1] - points2[i][1])))
          for i in range(len(points1))])


class SimilarGeometryDetector(object):
    def __init__(self, precision_decimal=0.5):
        self.index= rtree.index.Index()
        self.precision = precision_decimal
        self.geometries = []
    def contains(self, geometry):
        center = tuple(BoundingBox(*geometry.bounds).center())
        for i in self.index.intersection(center):
            if geometry.almost_equals(self.geometries[i], self.precision):
                return True
        return False
    def test_and_add(self, geometry):
        if self.contains(geometry):
            return True
        else:
            i = len(self.geometries)
            self.geometries.append(geometry)
            self.index.insert(i, geometry.bounds)
            return False



class BoundingBox(object):
    __slots__  = ("x1","y1","x2","y2")
    def __init__(self, x1, y1, x2, y2):
        self.x1 = min(x1, x2)
        self.y1 = min(y1, y2)
        self.x2 = max(x1, x2)
        self.y2 = max(y1, y2)
    def extend_to_bbox(self, bbox):
        x1 ,y1, x2, y2 = bbox
        nx1 = min (self.x1, x1)
        ny1 = min (self.y1, y1)
        nx2 = max (self.x2, x2)
        ny2 = max (self.y2, y2)
        return BoundingBox(nx1,ny1,nx2,ny2)
    def p1(self):
        return Point(self.x1, self.y1)
    def p2(self):
        return Point(self.x2, self.y2)
    def __getitem__(self, key):
        if key == 0: return self.x1
        if key == 1: return self.y1
        if key == 2: return self.x2
        if key == 3: return self.y2
        raise IndexError()
    def width(self):
        return self.x2 - self.x1
    def height(self):
        return self.y2 - self.y1
    def center(self):
        return Point((self.x1+self.x2)/2,
                     (self.y1+self.y2)/2)
    def is_point_inside(self, point):
        return (point.x >= self.x1) and (point.x <= self.x2) and \
               (point.y >= self.y1) and (point.y <= self.y2)
    def __str__(self):
        return "(" + str(self.x1) + ", " + str(self.y1) + ", "+ str(self.x2) + ", " + str(self.y2) + ")"
    def __repr__(self):
        return "Position(" + repr(self.x1) + ", " + repr(self.y1) + ", "+ repr(self.x2) + ", " + repr(self.y2) + ")"
    @staticmethod
    def of_points(points):
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        return BoundingBox( min(xs), min(ys), max(xs), max(ys))






class Path(object):
    """ Un path tel qu'utilisé dans le format SVG ou PDF.
    La représentation est destinée a faciliter la reconnaisance.
    Nous représentons avec deux champs:
     - une chaîne représentant une liste de commandes
     - une liste de points (x,y) (positions absolues)
    Les commandes peuvent être:
         M : move (1 argument)
         L : line (1 argument)
         C : curve  (3 arguments)
         Q : quadratic  (2 arguments)
         Z : close  (0 argument)
    """
    __slots__ = ('commands','points','most_distant_point_index', 'angle_and_points_for_path_recognition', 'style', 'd')
    commands_argument_count = { 'M': 1, 'L':1, 'C':3, 'Q':2,'Z':0}
    def __init__(self, commands, points, style="", d=None):
        self.commands = commands
        self.points = points
        self.most_distant_point_index = None
        self.angle_and_points_for_path_recognition = {}
        self.style = style
        self.d = d
    def __str__(self):
        result = []
        i = 0
        for c in self.commands:
            result.append(c)
            for foo in range(Path.commands_argument_count[c]):
                result.append(str(self.points[i]))
                i = i + 1
        return "\n".join(result)
    def __repr__(self):
        return "Path(" + str(self) + ")"
    def bbox(self, i=None):
        # aproximation
        if i == None:
            return BoundingBox.of_points(self.points)
        else:
            return BoundingBox.of_points(self.points[:i])
    def p0_distance(self, i=None):
        if i == None: i = self.get_p0_most_distant_point_index()
        (x1, y1), (x2, y2) =  self.points[0], self.points[i]
        return math.sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1))
    def get_angle_and_points_for_path_recognition(self, i):
        """
            Move, rotate and scale the list of points in order to facilitate
            recognition.

            The following transformations are applied:
            - We first move the points so that the first one be in (0,0),
            i.e. we move everypoints by (-x1,-y1)
            - Then we rotate and scale the points so that the i commes
              at position (1,0)
        """
        if i not in self.angle_and_points_for_path_recognition:
            x1,y1 = self.points[0] # le premier point
            x2, y2 = self.points[i] # le second point
            # le rayon =
            r = math.sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1))
            if (r == 0.0):
                self.points_for_path_recognition[i] = 0, self.points
            else:
                # l'angle:
                t = math.atan2( (y2-y1), (x2-x1))
                cosTbyR = math.cos(-t) / r
                sinTbyR = math.sin(-t) / r
                self.angle_and_points_for_path_recognition[i] = t, [
                    Point(
                        # move rotate and scale the coordinates:
                        cosTbyR * (x-x1) - sinTbyR * (y-y1),
                        sinTbyR * (x-x1) + cosTbyR * (y-y1))
                    for x,y in self.points ]
        return self.angle_and_points_for_path_recognition[i]

    def get_p0_most_distant_point_index(self):
        """ retourne l'index du point le plus distant du premier"""
        if self.most_distant_point_index == None:
            max_squaredist = 0
            max_i = 0
            x0,y0 = self.points[0]
            for i in range(1,len(self.points)):
                xi, yi =  self.points[i]
                squaredist = (xi-x0)*(xi-x0) + (yi-y0)*(yi-y0)
                if squaredist > max_squaredist:
                    max_squaredist = squaredist
                    max_i = i
            self.most_distant_point_index = max_i
        return self.most_distant_point_index


    #def almost_equals(self, other, tolerance = 0.05):
    #    i = self.get_p0_most_distant_point_index()
    #    return self.commands == other.commands and \
    #        maxdiff(self.get_points_for_path_recognition(i),
    #                other.get_points_for_path_recognition(i)) \
    #            <= tolerance

    def startswith(self, other, tolerance = 0.05, min_scale = 0.9, max_scale=1.1):
        if self.commands.startswith(other.commands):
            i = other.get_p0_most_distant_point_index()
            scale_factor = self.p0_distance(i) / other.p0_distance(i)
            if scale_factor >= min_scale and scale_factor <= max_scale:
              other_angle, other_points = other.get_angle_and_points_for_path_recognition(i)
              self_angle, self_points = self.get_angle_and_points_for_path_recognition(i)
              if maxdiff(self_points[:len(other.points)], other_points) < tolerance:
                  result = self_angle - other_angle
                  if result <= -math.pi:
                      result += 2*math.pi
                  elif result > math.pi:
                      result -= 2*math.pi
                  elif result == 0.0:
                      # renvoie quelque chose d'evalué à True proche de 0:
                      result = sys.float_info.min
                  return result
        return False

    @staticmethod
    def from_svg(d):
        """ Create a Path from a svg d string"""
        commands = []
        points = []
        tokens = [ t for t in Path.__svg_path_tokenizer(d)]
        tokens.reverse()
        current_point = Point(0.0, 0.0)
        while tokens:
            t = tokens.pop()
            if t in ['M','L']:
                while True:
                    points.append(Point(tokens.pop(), tokens.pop()))
                    commands.append(t)
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
                    t = 'L' # M subsequent values becomes L
            elif t in ['m', 'l']:
                while True:
                    # convert to absolute:
                    points.append(Point(current_point.x + tokens.pop(), current_point.y + tokens.pop()))
                    commands.append(t.upper())
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
                    t = 'L' # M subsequent values becomes L
            elif t in ['H','h','V','v']:
                while True:
                    # convert to 'L'
                    if t == 'H':
                        points.append(Point(tokens.pop(), current_point.y))
                    elif t == 'h':
                        points.append(Point(current_point.x + tokens.pop(), current_point.y))
                    elif t == 'V':
                        points.append(Point(current_point.x, tokens.pop()))
                    elif t == 'v':
                        points.append(Point(current_point.x, current_point.y + tokens.pop()))
                    commands.append('L')
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
            elif t == 'C':
                while True:
                    for i in range(3):
                        points.append(Point(tokens.pop(), tokens.pop()))
                    commands.append('C')
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
            elif t == 'c':
                while True:
                    # convert to absolute
                    for i in range(3):
                        points.append(Point(current_point.x + tokens.pop(), current_point.y + tokens.pop()))
                    commands.append('C')
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
            elif t in ['S', 's']:
                while True:
                    if peek(commands) == 'C':
                        # the control point is the reflextion of the previous control point
                        previous_control_point = points[-2]
                        points.append(Point(
                            current_point.x - previous_control_point.x + current_point.x,
                            current_point.y - previous_control_point.y + current_point.y))
                    else:
                        # no previous control point, use the current point
                        points.append(Point(current_point.x, current_point.y))
                    for i in range(2):
                        if t == 'S':
                            points.append(Point(tokens.pop(), tokens.pop()))
                        else:
                            # Convert to absolute:
                            points.append(Point(
                                current_point.x + tokens.pop(),
                                current_point.y + tokens.pop()))
                    commands.append('C')
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
            elif t == 'Q':
                while True:
                    for i in range(2):
                        points.append(Point(tokens.pop(), tokens.pop()))
                    commands.append('Q')
                    #Path.__convert_last_quadratic_command_to_cubic(commands,points)
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
            elif t == 'q':
                while True:
                    for i in range(2):
                        # Convert to absolute:
                        points.append(Point(
                            current_point.x + tokens.pop(),
                            current_point.y + tokens.pop()))
                    commands.append('Q')
                    #Path.__convert_last_quadratic_command_to_cubic(commands,points)
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
            elif t in ['T', 't']:
                while True:
                    if peek(commands) == 'Q':
                        # the control point is the refextion of the previous control point
                        previous_control_point = points[-2]
                        points.append(Point(
                            current_point.x - previous_control_point.x + current_point.x,
                            current_point.y - previous_control_point.y + current_point.y))
                    else:
                        # no previous control point, use the current point
                        points.append(Point(current_point.x, current_point.y))
                    if t == 'T':
                        points.append(Point(tokens.pop(), tokens.pop()))
                    else:
                        # Convert to absolute:
                        points.append(Point(
                            current_point.x + tokens.pop(),
                            current_point.y + tokens.pop()))
                    commands.append('Q')
                    #Path.__convert_last_quadratic_command_to_cubic(commands,points)
                    current_point = points[-1]
                    if type(peek(tokens)) != float: break
            elif t in ['A','a']:
                raise Exception("unsuported svg path command: " + str(t) + " : " + d)
            elif t in ['Z','z']:
                commands.append('Z')
                #pass
            else:
                raise Exception("invalid path " + str(t) + " : " + d)
        return Path("".join(commands), points, d=d)

    #@staticmethod
    #def __convert_last_quadratic_command_to_cubic(commands, points):
    #    """ inkscape utilisé pour éditer les paths à reconnaître transforme
    #        malheureusement toute les commandes quadratic en cubic
    #        on fait donc de même pour pour pouvoir reconnaitre les path.
    #        Formule trouvée ici:
    #        http://fontforge.org/bezier.html
    #    """
    #    assert(commands[-1] == 'Q')
    #    commands[-1] = 'C'
    #    QP0 = points[-3]
    #    QP1 = points[-2]
    #    QP2 = points[-1]
    #    CP0 = QP0
    #    CP1 = Point(QP0[0] + (QP1[0] - QP0[0]) * 2 / 3, QP0[1] + (QP1[1] - QP0[1]) * 2 / 3) # QP0 + 2/3 *(QP1-QP0)
    #    CP2 = Point(QP2[0] + (QP1[0] - QP2[0]) * 2 / 3, QP2[1] + (QP1[1] - QP2[1]) * 2 / 3) # QP2 + 2/3 *(QP1-QP2)
    #    CP3 = QP2
    #    #points[-3] = CP0
    #    points[-2] = CP1
    #    points[-1] = CP2
    #    points.append(CP3)

    @staticmethod
    def __svg_path_tokenizer(d):
        i = 0
        while i < len(d):
            c = d[i]
            o = ord(c)
            if o in (32, 9, 10, 13,44):
                i = i + 1
            elif o >= 45 and o <= 57:
                j = i+1
                while j < len(d):
                    oj = ord(d[j])
                    if ((oj < 45) or (oj > 57)) and (oj != ord('e')):
                        break
                    j = j + 1
                yield float(d[i:j])
                i = j
            elif c in ['M','L','H','V','C','S','Q','T','A','Z', 'm','l','h','v','c','s','q','t','a','z']:
                yield c
                i = i + 1
            else:
                raise Exception("invalid character in path data: chr("
                    + str(ord(d[i])) + ") = '" + d[i] + "' :  " + d)


