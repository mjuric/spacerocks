import rebound
import pkg_resources
from astropy.time import Time
import numpy as np
import copy
from rich.progress import track

from .spice import SpiceBody
from .units import Units
from .convenience import Convenience
from .spacerock import SpaceRock

SPICE_PATH = pkg_resources.resource_filename('spacerocks', 'data/spice')

class Simulation(rebound.Simulation, Convenience):   


    def __init__(self):
        super().__init__(self)
        self.units = ('day', 'AU', 'Msun')
        self.simdata = {}
        self.perturber_names = []
        self.N_active = 0

    def add_perturbers(self, epoch, **kwargs):
        
        epoch = Time(epoch, scale='tdb', format='jd')
        self.t = epoch.jd

        if kwargs.get('spiceid') is not None:
            names = np.atleast_1d(kwargs.get('spiceid'))
            for name in names:
                self.perturber_names.append(name)
                self.N_active += 1
                   
                body = SpiceBody(spiceid=name)
                b = body.at(epoch)
                self.add(x=b.x.au, 
                         y=b.y.au, 
                         z=b.z.au,
                         vx=b.vx.value, 
                         vy=b.vy.value, 
                         vz=b.vz.value,
                         m=body.mass.value, 
                         hash=name)

        if kwargs.get('rocks') is not None:
            rocks = kwargs.get('rocks')
            for name in np.unique(rocks.name):
                self.perturber_names.append(name)
                self.N_active += 1
                r = rocks[rocks.name == name]

                self.add(x=r.x.au, 
                         y=r.y.au, 
                         z=r.z.au,
                         vx=r.vx.value, 
                         vy=r.vy.value, 
                         vz=r.vz.value,
                         m=r.mass.value, 
                         hash=name)

        for n in self.perturber_names:
            h = self.particles[n].hash
            self.simdata[h.value] = []

    def add_spacerocks(self, rocks):
        self.rocks = copy.copy(rocks)
        self.testparticle_names = rocks.name
        self.remaining_testparticles = copy.copy(rocks.name)
        self.rocks.to_bary()
        self.rocks.position
        self.rocks.velocity
        for rock in self.rocks:
            self.add(x=rock.x.au, 
                     y=rock.y.au, 
                     z=rock.z.au,
                     vx=rock.vx.value, 
                     vy=rock.vy.value, 
                     vz=rock.vz.value,
                     m=0, 
                     hash=rock.name)
        
        for n in rocks.name:
            h = self.particles[n].hash
            self.simdata[h.value] = []

    def propagate(self, epochs, units=Units(), progress=True, **kwargs):
        '''
        Numerically integrate all bodies to the desired date.
        This routine synchronizes the epochs.
        '''

        if kwargs.get('func') is not None:
            f = True
            func = kwargs.get('func')
        else:
            f = False

        units.timescale = 'tdb'

        epochs = self.detect_timescale(np.atleast_1d(epochs), units.timescale)

        self.move_to_com()

        if progress == True:
            iterator = track(np.sort(epochs.tdb.jd))
        else:
            iterator = np.sort(epochs.tdb.jd)
        
        for time in iterator:
            self.integrate(time, exact_finish_time=1)

            if f == True:
                func(self)
            
            for p in self.particles:
                h = p.hash.value
                arr = [time] + p.xyz + p.vxyz
                self.simdata[h].append(arr)

        pepoch  = []
        px      = []
        py      = []
        pz      = []
        pvx     = []
        pvy     = []
        pvz     = []
        pname   = []
        for n in self.perturber_names:
            ts, xs, ys, zs, vxs, vys, vzs = np.array(self.simdata[rebound.hash(n).value]).T
            pepoch.append(ts.tolist())
            px.append(xs.tolist())
            py.append(ys.tolist())
            pz.append(zs.tolist())
            pvx.append(vxs.tolist())
            pvy.append(vys.tolist())
            pvz.append(vzs.tolist())
            pname.append([n for _ in range(len(ts))])

        pepoch  = np.hstack(pepoch)
        px      = np.hstack(px)
        py      = np.hstack(py)
        pz      = np.hstack(pz)
        pvx     = np.hstack(pvx)
        pvy     = np.hstack(pvy)
        pvz     = np.hstack(pvz)
        pname   = np.hstack(pname)
           
        planets = SpaceRock(x=px, y=py, z=pz, vx=pvx, vy=pvy, vz=pvz, name=pname, epoch=pepoch, origin='ssb', units=units)

        if hasattr(self, 'testparticle_names'):
            epoch  = []
            x      = []
            y      = []
            z      = []
            vx     = []
            vy     = []
            vz     = []
            name   = []
            for n in self.testparticle_names:
                ts, xs, ys, zs, vxs, vys, vzs = np.array(self.simdata[rebound.hash(n).value]).T
                epoch.append(ts.tolist())
                x.append(xs.tolist())
                y.append(ys.tolist())
                z.append(zs.tolist())
                vx.append(vxs.tolist())
                vy.append(vys.tolist())
                vz.append(vzs.tolist())
                name.append([n for _ in range(len(ts))])

            epoch  = np.hstack(epoch)
            x      = np.hstack(x)
            y      = np.hstack(y)
            z      = np.hstack(z)
            vx     = np.hstack(vx)
            vy     = np.hstack(vy)
            vz     = np.hstack(vz)
            name   = np.hstack(name)

            rocks = SpaceRock(x=x, y=y, z=z, vx=vx, vy=vy, vz=vz, name=name, epoch=epoch, origin='ssb', units=units)

        else:
            rocks = ()
        
        return rocks, planets, self