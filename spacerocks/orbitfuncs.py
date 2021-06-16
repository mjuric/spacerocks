from numpy import pi, sqrt, cbrt, sin, cos, tan, sinh, tanh, exp, log10, zeros_like, arccos, arctan2, array, any
import numpy as np
from astropy import units as u
from astropy.coordinates import Angle, Distance
from astropy.time import Time
from scipy.optimize import newton
from .constants import *

from .vector import Vector

from skyfield.api import Topos, Loader
# Load in planets for ephemeride calculation.
load = Loader('./Skyfield-Data', expire=False, verbose=False)
ts = load.timescale()
planets = load('de440.bsp')
sun = planets['sun']

class OrbitFuncs:


    def to_bary(self):
        '''
        Method to convert heliocentric coordinates to barycentric coordinates.
        '''
        if self.__class__.frame == 'heliocentric':

            t = ts.tt(jd=self.epoch.tt.jd)

            x_sun, y_sun, z_sun = sun.at(t).ecliptic_xyz().au * u.au
            vx_sun, vy_sun, vz_sun = sun.at(t).ecliptic_velocity().au_per_d * u.au / u.day

            # calculate the barycentric xyz postion
            self.x += x_sun
            self.y += y_sun
            self.z += z_sun
            self.vx += vx_sun
            self.vy += vy_sun
            self.vz += vz_sun


            # clear the keplerian variables because they need to be recomputed
            self.clear_kep()

            self.position = Vector(self.x, self.y, self.z)
            self.velocity = Vector(self.vx, self.vy, self.vz)

            self.__class__.frame = 'barycentric'
            self.__class__.mu = mu_bary

        return self


    def to_helio(self):
        '''
        Method to convert barycentric coordinates to heliocentric coordinates.
        '''
        if self.__class__.frame == 'barycentric':

            t = ts.tt(jd=self.epoch.tt.jd)

            x_sun, y_sun, z_sun = sun.at(t).ecliptic_xyz().au * u.au
            vx_sun, vy_sun, vz_sun = sun.at(t).ecliptic_velocity().au_per_d * u.au / u.day

            #x_sun, y_sun, z_sun = sun.at(t).position.au * u.au
            #vx_sun, vy_sun, vz_sun = sun.at(t).velocity.au_per_d * u.au / u.day


            # calculate the heliocentric xyz postion
            self.x -= x_sun
            self.y -= y_sun
            self.z -= z_sun
            self.vx -= vx_sun
            self.vy -= vy_sun
            self.vz -= vz_sun

            # clear the keplerian variables because they need to be recomputed
            self.clear_kep()

            self.position = Vector(self.x, self.y, self.z)
            self.velocity = Vector(self.vx, self.vy, self.vz)

            self.__class__.frame = 'heliocentric'
            self.__class__.mu = mu_helio

        return self

    def clear_kep(self):

        to_delete = ['_a', '_e', '_inc', '_arg', '_node', '_varpi', '_M', '_E',
                     '_true_anomaly', '_true_longitude', '_mean_longitude',
                     '_q', '_t_peri', '_b', '_p', '_n', '_Q', '_hill_radius', '_r',
                     '_ovec', '_vovec', '_nvec', '_hvec', '_evec', '_position', '_velocity', '_rrdot']

        for attr in to_delete:
            self.__dict__.pop(attr, None)

        #del self.a
        #del self.e
        #del self.inc
        #del self.arg
        #del self.node
        #del self.M
        #del self.E
        #del self.varpi
        #del self.true_anomaly
        #del self.true_longitude
        #del self.mean_longitude
        #del self.q
        #del self.t_peri
        #del self.b
        #del self.p
        #del self.n
        #del self.Q
        #del self.hill_radius
        #del self.r
        #del self.ovec
        #del self.vovec
        #del self.nvec
        #del self.hvec
        #del self.evec
        #del self.position
        #del self.velocity


    ''' Vector Quantities '''

    @property
    def ovec(self):
        if not hasattr(self, '_ovec'):
            self.ovec =  Vector(self.r * cos(self.true_anomaly), self.r * sin(self.true_anomaly), zeros_like(self.true_anomaly))
        return self._ovec

    @ovec.setter
    def ovec(self, value):
        self._ovec = value

    @ovec.deleter
    def ovec(self):
        del self._ovec

    @property
    def vovec(self):
        if not hasattr(self, '_vovec'):
            a = sqrt(self.mu / u.rad**2 * self.a) / self.r
            self.vovec = Vector(- a * sin(self.E.rad), a * sqrt(1 - self.e**2) * cos(self.E.rad), a * zeros_like(self.E.rad))
        return self._vovec

    @vovec.setter
    def vovec(self, value):
        self._vovec = value

    @vovec.deleter
    def vovec(self):
        del self._vovec

    @property
    def nvec(self):
        if not hasattr(self, '_nvec'):
            self.nvec = Vector(-self.hvec.y, self.hvec.x, zeros_like(self.hvec.z))
        return self._nvec

    @nvec.setter
    def nvec(self, value):
        self._nvec = value

    @nvec.deleter
    def nvec(self):
        del self._nvec

    @property
    def evec(self):
        if not hasattr(self, '_evec'):
            self.evec = self.velocity.cross(self.hvec) / (self.mu / u.rad**2)  - self.position / self.position.norm
        return self._evec

    @evec.setter
    def evec(self, value):
        self._evec = value

    @evec.deleter
    def evec(self):
        del self._evec

    @property
    def hvec(self):
        if not hasattr(self, '_hvec'):
            self.hvec = self.position.cross(self.velocity)
        return self._hvec

    @hvec.setter
    def hvec(self, value):
        self._hvec = value

    @hvec.deleter
    def hvec(self):
        del self._hvec

    @property
    def position(self):
        if not hasattr(self, '_position'):
            if hasattr(self, '_x') and hasattr(self, '_y') and hasattr(self, '_z'):
                self.position = Vector(self.x, self.y, self.z)
            else:
                self.position = self.ovec.euler_rotation(self.arg, self.inc, self.node)
        return self._position

    @position.setter
    def position(self, value):
        self._position = value

    @position.deleter
    def position(self):
        del self._position

    @property
    def velocity(self):
        if not hasattr(self, '_velocity'):
            if hasattr(self, '_vx') and hasattr(self, '_vy') and hasattr(self, '_vz'):
                self.velocity = Vector(self.vx, self.vy, self.vz)
            else:
                self.velocity = self.vovec.euler_rotation(self.arg, self.inc, self.node)
        return self._velocity

    @velocity.setter
    def velocity(self, value):
        self._velocity = value

    @velocity.deleter
    def velocity(self):
        del self._velocity

    ''' Cartesian Elements '''

    @property
    def x(self):
        if not hasattr(self, '_x'):
            self.x = self.position.x
        return self._x

    @x.setter
    def x(self, value):
        self._x = value

    @x.deleter
    def x(self):
        del self._x

    @property
    def y(self):
        if not hasattr(self, '_y'):
            self.y = self.position.y
        return self._y

    @y.setter
    def y(self, value):
        self._y = value

    @y.deleter
    def y(self):
        del self._y

    @property
    def z(self):
        if not hasattr(self, '_z'):
            self.z = self.position.z
        return self._z

    @z.setter
    def z(self, value):
        self._z = value

    @z.deleter
    def z(self):
        del self._z

    @property
    def vx(self):
        if not hasattr(self, '_vx'):
            self.vx = self.velocity.x
        return self._vx

    @vx.setter
    def vx(self, value):
        self._vx = value

    @vx.deleter
    def vx(self):
        del self._vx

    @property
    def vy(self):
        if not hasattr(self, '_vy'):
            self.vy = self.velocity.y
        return self._vy

    @vy.setter
    def vy(self, value):
        self._vy = value

    @vy.deleter
    def vy(self):
        del self._vy

    @property
    def vz(self):
        if not hasattr(self, '_vz'):
            self.vz = self.velocity.z
        return self._vz

    @vz.setter
    def vz(self, value):
        self._vz = value

    @vz.deleter
    def vz(self):
        del self._vz



    ''' Required Keplerian Elements '''

    @property
    def a(self):
        if not hasattr(self, '_a'):
            self.a = Distance(1 / (2 / self.position.norm - self.velocity.dot(self.velocity) / self.mu * u.rad**2), u.au, allow_negative=True)
        return self._a

    @a.setter
    def a(self, value):
        self._a = value

    @a.deleter
    def a(self):
        del self._a


    @property
    def e(self):
        if not hasattr(self, '_e'):
            self.e = self.evec.norm.value
        return self._e

    @e.setter
    def e(self, value):
        self._e = value

    @e.deleter
    def e(self):
        del self._e


    @property
    def inc(self):
        if not hasattr(self, '_inc'):
            self.inc = Angle(arccos(self.hvec.z / self.hvec.norm), u.rad)
        return self._inc

    @inc.setter
    def inc(self, value):
        self._inc = value

    @inc.deleter
    def inc(self):
        del self._inc


    ''' Keplerian choice-of-three '''


    @property
    def node(self):
        if not hasattr(self, '_node'):
            if hasattr(self, '_varpi') and hasattr(self, '_arg'):
                self.node = Angle((self.varpi.rad - self.arg.rad) % (2 * pi), u.rad)
            elif hasattr(self, '_position') and hasattr(self, '_velocity'):
                node = zeros_like(self.inc.rad * u.rad)
                node[self.inc == 0] = 0
                node[self.inc != 0] = arccos(self.nvec[self.inc != 0].x / self.nvec[self.inc != 0].norm)
                node[self.nvec.y < 0] = 2 * pi * u.rad - node[self.nvec.y < 0]
                self.node = Angle(node, u.rad)
        return self._node

    @node.setter
    def node(self, value):
        self._node = value

    @node.deleter
    def node(self):
        del self._node


    @property
    def arg(self):
        if not hasattr(self, '_arg'):

            if hasattr(self, '_varpi') and hasattr(self, 'node'):
                self.arg = Angle((self.varpi.rad - self.node.rad) % (2 * pi), u.rad)

            elif hasattr(self, '_position') and hasattr(self, '_velocity'):
                n = self.nvec.norm
                arg = zeros_like(self.e * u.rad)
                arg[(self.e == 0) | (n == 0)] = 0
                arg[(self.e != 0) & (n != 0)] = arccos(self.nvec[(self.e != 0) & (n != 0)].dot(self.evec[(self.e != 0) & (n != 0)]) / (n[(self.e != 0) & (n != 0)] * self.e[(self.e != 0) & (n != 0)]))
                arg[self.evec.z < 0] = 2 * pi * u.rad - arg[self.evec.z < 0]
                self.arg = Angle(arg, u.rad)

        return self._arg

    @arg.setter
    def arg(self, value):
        self._arg = value

    @arg.deleter
    def arg(self):
        del self._arg


    @property
    def varpi(self):
        if not hasattr(self, '_varpi'):
            self.varpi = Angle((self.node.rad + self.arg.rad) % (2 * pi), u.rad)
        return self._varpi

    @varpi.setter
    def varpi(self, value):
        self._varpi = value

    @varpi.deleter
    def varpi(self):
        del self._varpi


    '''

    Keplerian choice-of-six

    There are several options for describing the location of a rock on its orbit:
    - mean anomaly
    - true anomaly
    - eccentric anomaly
    - mean longitude
    - true longitude
    - time of pericenter

    As long as you know the longitude of pericenter, you can get any of these
    quantities from any of the others.

    '''

    @property
    def M(self):
        if not hasattr(self, '_M'):

            if hasattr(self, '_mean_longitude'):
                M = (self.mean_longitude.rad - self.varpi.rad) % (2 * pi)
                self.M = Angle(M, u.rad)

            elif hasattr(self, '_true_anomaly') or hasattr(self, '_true_longitude') or hasattr(self, '_E') or (hasattr(self, '_position') and hasattr(self, '_velocity')):
                M = np.zeros(len(self))
                M[self.e < 1] = (self.E.rad[self.e < 1] - self.e[self.e < 1] * sin(self.E.rad[self.e < 1])) % (2 * pi)
                M[self.e >= 1] = (self.e[self.e >= 1] * sinh(self.E.rad[self.e >= 1]) - self.E.rad[self.e >= 1]) % (2 * pi)
                self.M = Angle(M, u.rad)

            elif hasattr(self, '_t_peri'):
                M = self.n * (self.epoch - self.t_peri)
                M = M % (2 * pi * u.rad)
                self.M = Angle(M, u.rad)

        return self._M

    @M.setter
    def M(self, value):
        self._M = value

    @M.deleter
    def M(self):
        del self._M



    @property
    def E(self):
        if not hasattr(self, '_E'):

            if hasattr(self, '_true_anomaly') or hasattr(self, '_true_longitude') or (hasattr(self, '_position') and hasattr(self, '_velocity')):
                E = 2 * arctan2(sqrt(1 - self.e) * sin(self.true_anomaly.rad/2), sqrt(1 + self.e) * cos(self.true_anomaly.rad/2))
                self.E = Angle(E, u.rad)

            elif hasattr(self, '_M') or hasattr(self, '_mean_longitude') or hasattr(self, '_t_peri'):
                E = np.zeros(len(self))


                M = array(self.M.rad)[self.e < 1]
                e = self.e[self.e < 1]
                M[M > pi] -= 2 * pi
                alpha = (3 * pi**2 + 1.6 * (pi**2 - pi * abs(M))/(1 + e))/(pi**2 - 6)
                d = 3 * (1 - e) + alpha * e
                q = 2 * alpha * d * (1 - e) - M**2
                r = 3 * alpha * d * (d - 1 + e) * M + M**3
                w = (abs(r) + sqrt(q**3 + r**2))**(2/3)
                E1 = (2 * r * w / (w**2 + w*q + q**2) + M)/d
                f2 = e * sin(E1)
                f3 = e * cos(E1)
                f0 = E1 - f2 - M
                f1 = 1 - f3
                d3 = -f0 / (f1 - f0 * f2 / (2 * f1))
                d4 = -f0 / (f1 + f2 * d3 / 2 + d3**2 * f3 / 6)
                d5 = -f0 / (f1 + d4 * f2 / 2 + d4**2 * f3 / 6 - d4**3 * f2 / 24)
                E[self.e < 1] = (E1 + d5) % (2 * pi)

                if np.any(self.e >= 1):
                    M = array(self.M.rad)[self.e >= 1]
                    e = self.e[self.e >= 1]
                    f = lambda E, M, e: e * sinh(E) - E - M
                    E0 = M
                    E[self.e >= 1] = np.array([newton(f, E0[idx], args=(M[idx], e[idx]), maxiter=10000) for idx in range(len(M))])

                self.E = Angle(E, u.rad)

        return self._E

    @E.setter
    def E(self, value):
        self._E = value

    @E.deleter
    def E(self):
        del self._E


    @property
    def true_anomaly(self):
        if not hasattr(self, '_true_anomaly'):

            if hasattr(self, '_true_longitude'):
                self.true_anomaly = Angle(self.true_longitude.rad - self.varpi.rad, u.rad)

            elif hasattr(self, '_E') or hasattr(self, '_M') or hasattr(self, '_mean_longitude') or hasattr(self, '_t_peri'):
                true_anomaly = np.zeros(len(self))
                true_anomaly[self.e < 1] = 2 * arctan2(sqrt(1 + self.e[self.e < 1]) * sin(self.E.rad[self.e < 1] / 2), sqrt(1 - self.e[self.e < 1]) * cos(self.E.rad[self.e < 1] / 2))
                #if np.any(self.e >= 1):
                true_anomaly[self.e >= 1] = 2 * arctan2(sqrt(self.e[self.e >= 1] + 1) * tanh(self.E[self.e >= 1] / 2), sqrt(self.e[self.e >= 1] - 1))
                #self.true_anomaly = Angle(2 * arctan2(sqrt(1 + self.e) * sin(self.E.rad / 2), sqrt(1 - self.e) * cos(self.E.rad / 2)), u.rad)
                self.true_anomaly = Angle(true_anomaly, u.rad)

            elif hasattr(self, '_position') and hasattr(self, '_velocity'):
                true_anomaly = zeros_like(self.e * u.rad)
                true_anomaly[self.e == 0] = arccos(self.position[self.e == 0].x / self.position[self.e == 0].norm)
                true_anomaly[self.e != 0] = arccos(self.evec[self.e != 0].dot(self.position[self.e != 0]) / (self.evec[self.e != 0].norm * self.position[self.e != 0].norm))

                true_anomaly[self.position.dot(self.velocity).value < 0] = 2 * pi * u.rad - true_anomaly[self.position.dot(self.velocity).value < 0]
                self.true_anomaly = Angle(true_anomaly.value, u.rad) # compute true anomaly from cartesian vectors. Other properties can be computed lazily.

        return self._true_anomaly

    @true_anomaly.setter
    def true_anomaly(self, value):
        self._true_anomaly = value

    @true_anomaly.deleter
    def true_anomaly(self):
        del self._true_anomaly


    @property
    def true_longitude(self):
        if not hasattr(self, '_true_longitude') or (hasattr(self, '_position') and hasattr(self, '_velocity')):
            self.true_longitude = Angle((self.true_anomaly.rad + self.varpi.rad) % (2 * pi), u.rad)
        return self._true_longitude

    @true_longitude.setter
    def true_longitude(self, value):
        self._true_longitude = value

    @true_longitude.deleter
    def true_longitude(self):
        del self._true_longitude

    @property
    def mean_longitude(self):
        if not hasattr(self, '_mean_longitude'):
            self.mean_longitude = Angle((self.M.rad + self.varpi.rad) % (2 * pi), u.rad)
        return self._mean_longitude

    @mean_longitude.setter
    def mean_longitude(self, value):
        self._mean_longitude = value

    @mean_longitude.deleter
    def mean_longitude(self):
        del self._mean_longitude


    @property
    def t_peri(self):
        if not hasattr(self, '_t_peri'):
            self.t_peri = Time(self.epoch.jd * u.day - self.M / self.n, format='jd', scale='utc')
        return self._t_peri

    @t_peri.setter
    def t_peri(self, value):
        self._t_peri = value

    @t_peri.deleter
    def t_peri(self):
        del self._t_peri



    ''' Physical Properties '''

    #@property
    #def mass(self):
    #    if not hasattr(self, '_mass'):
    #        self.mass = 0
    #    return self._mass

    #@mass.setter
    #def mass(self, value):
    #    self._mass = value


    #@property
    #def radius(self):
    #    if not hasattr(self, '_radius'):
    #        self.radius = 1e-16
    #    return self._radius

    #@radius.setter
    #def radius(self, value):
    #    self._radius = value


    #@property
    #def density(self):
    #    if not hasattr(self, '_density'):
    #        self.density = 1e-16
    #    return self._density

    #@density.setter
    #def density(self, value):
    #    self._density = value


    ''' Derived Quantities '''

    @property
    def b(self):
        if not hasattr(self, '_b'):
            self.b = self.a * sqrt(1 - self.e**2)
        return self._b

    @b.setter
    def b(self, value):
        self._b = value

    @b.deleter
    def b(self):
        del self._b


    @property
    def p(self):
        if not hasattr(self, '_p'):
            self.p = self.a * (1 - self.e**2)
        return self._p

    @p.setter
    def p(self, value):
        self._p = value

    @p.deleter
    def p(self):
        del self._p


    @property
    def q(self):
        if not hasattr(self, '_q'):
            self.q = self.a * (1 - self.e)
        return self._q

    @q.setter
    def q(self, value):
        self._q = value

    @q.deleter
    def q(self):
        del self._q


    @property
    def Q(self):
        if not hasattr(self, '_Q'):
            self.Q = self.a * (1 + self.e)
        return self._Q

    @Q.setter
    def Q(self, value):
        self._Q = value

    @Q.deleter
    def Q(self):
        del self._Q


    @property
    def n(self):
        if not hasattr(self, '_n'):
            self.n = sqrt(self.mu / abs(self.a)**3)
        return self._n

    @n.setter
    def n(self, value):
        self._n = value

    @n.deleter
    def n(self):
        del self._n

    @property
    def rrdot(self):
        '''Calculate the dot product of the position and velocity vectors'''
        return self.position.dot(self.velocity)

    @property
    def r(self):
        '''Compute the distance of the rock from the center of the coordinate system'''
        if not hasattr(self, '_r'):
            if hasattr(self, '_position'):
                self.r = Distance(self.position.norm)
            else:
                self.r = self.a * (1 - self.e * cos(self.E.rad))
        return self._r

    @r.setter
    def r(self, value):
        self._r = value

    @r.deleter
    def r(self):
        del self._r



    #@property
    #def hill_radius(self):
    #    if not hasattr(self, '_hill_radius'):
    #        self.hill_radius = self.a * (1 - self.e) * cbrt(self.m / 3)
    #    return self._hill_radius

    #@hill_radius.setter
    #def hill_radius(self, value):
    #    self._hill_radius = value

    #@hill_radius.deleter
    #def hill_radius(self):
    #    del self._hill_radius

    @property
    def TisserandJ(self):
        aJ = 5.2 * u.au
        return aJ / self.a * 2 * cos(self.inc) * sqrt(self.p / aJ)
