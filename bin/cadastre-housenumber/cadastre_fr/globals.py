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


import time
import math

SOURCE_TAG = u"cadastre-dgi-fr source : Direction Générale des Finances Publiques - Cadastre. Mise à jour : " + time.strftime("%Y")
VERBOSE = False

EARTH_RADIUS_IN_METTER = 6371000
EARTH_CIRCUMFERENCE_IN_METTER = 2*math.pi*EARTH_RADIUS_IN_METTER

