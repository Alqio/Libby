from difflib import SequenceMatcher
from math import cos, sin, pi, atan2, sqrt


def _to_radians(degs):
    return degs * pi / 180


def distance(lat1, lon1, lat2, lon2):
    earth_radius = 6371000
    delta_lat = _to_radians(lat2 - lat1)
    delta_lon = _to_radians(lon2 - lon1)
    
    a = sin(delta_lat / 2) ** 2
    b = cos(_to_radians(lat1)) * cos(_to_radians(lat2))
    c = sin(delta_lon / 2) ** 2
    d = a + b * c

    e = 2 * atan2(sqrt(d), sqrt(1 - d))

    f = earth_radius * e
    return f


def angle(lat1, lon1, lat2, lon2):

    lat1, lon1, lat2, lon2 = map(_to_radians, (lat1, lon1, lat2, lon2))

    delta_lon = lon2 - lon1

    y = sin(delta_lon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(delta_lon)

    brng = atan2(y, x)
    brng = brng * 180 / pi
    brng = (brng + 360) % 360
    return brng


def ratio(s1, s2):
    if s1 is None or s2 is None:
        return 0
    if len(s1) == 0 or len(s2) == 0:
        return 0
    if isinstance(s1, str) and isinstance(s2, str):
        pass
    elif isinstance(s1, unicode) and isinstance(s2, unicode):
        pass
    else:
        s1 = unicode(s1)
        s2 = unicode(s2)
    m = SequenceMatcher(None, s1, s2)
    return int(round(100 * m.ratio()))

