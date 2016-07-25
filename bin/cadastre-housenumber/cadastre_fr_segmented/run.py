#!/usr/bin/env python

from fr_cadastre_segmented import get_classifier_vector


a=[0, 0]
b=[1, 0]
c=[1, 1]
d=[0, 1]
e=[1, 2]
f=[0.5, 3]
g=[0, 2]

p1=[a,b,c,d,a]
p2=[f,e,c, d, g, f]
p3=[f,g,d, c, e, f]


def wkt(p):
    return "((" + ",".join(map(lambda c: " ".join(map(str, c)), p)) + "))"


p1 = wkt(p1)
p2 = wkt(p2)
p3 = wkt(p3)

print get_classifier_vector(p1, p2);
print
print
print get_classifier_vector(p1, p3);

#print status

