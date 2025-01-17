'''
Defines a class that provides simple methods for solving the Schrödinger
equation (SE) in coordinate space.
'''
import numpy as np
import numpy.typing as npt
from scipy.integrate import solve_ivp

from .interaction import Interaction
from .free_solutions import H_minus, H_plus, H_minus_prime, H_plus_prime

# Default values for solving the SE.
DEFAULT_R_MIN = 1e-12 # fm
DEFAULT_R_MAX = 30.0 # fm
DEFAULT_R_0 = 20.0 # fm
DEFAULT_NUM_PTS = 2000
MAX_STEPS = 20000
PHI_THRESHOLD = 1e-12

def Gamow_factor(l, eta):
    if l == 0:
        return np.sqrt(2*np.pi*eta / (np.exp(2*np.pi*eta)-1))
    else:
        return np.sqrt(l**2 + eta**2) / (l*(2*l+1)) * Gamow_factor(l-1, eta)


class SchroedingerEquation:
    def __init__(self,
        interaction: Interaction
    ):
        '''
        Instantiates an object that stores the Interaction and makes it easy to
        compute solutions to the Schrödinger equation and extract phase shifts
        with that Interaction.
        '''
        self.interaction = interaction


    def solve_se(self,
        energy: float, # E_{c.m.} (MeV)
        args: np.array, # interaction parameters
        s_endpts: np.array, # s where phi(s) is calculated
        l: int = 0, # angular momentum
        rho_0 = None, # initial rho value ("effective zero")
        phi_threshold = PHI_THRESHOLD, # minimum phi value (zero below this value)
        **solve_ivp_kwargs
    ):
        '''
        Solves the Schrödinger equation at the specified center-of-mass energy.
        Returns a 2-column matrix. The first is the r values. The second is the
        reduced radial wavefunction, u(r). (The optional third - based on
        return_uprime - is u'(r).)
        '''

        C_l = Gamow_factor(l, self.interaction.eta)
        if rho_0 is None:
            rho_0 = (phi_threshold / C_l) ** (1/(l+1))
        phi_0 = C_l * rho_0**(l+1)
        phi_prime_0 = C_l * (l+1) * rho_0**l
        
        if self.interaction.is_complex:
            initial_conditions = np.array([phi_0+0j, phi_prime_0+0j])
        else:
            initial_conditions = np.array([phi_0, phi_prime_0])
        
        sol = solve_ivp(
            lambda s, phi: np.array([phi[1],
                (self.interaction.tilde(s, args) + 2*self.interaction.eta/s + l*(l+1)/s**2 - 1.0) * phi[0]]),
            s_endpts, initial_conditions, rtol=1e-12, atol=1e-30,
            dense_output=True, **solve_ivp_kwargs
        )

        return sol.sol


    def delta(self,
        energy: float, # center-of-mass energy
        args: np.array, # interaction parameters
        s_endpts: np.array, # [s_min, s_max]; phi(s) is calculated on this interval 
        l: int, # angular momentum
        s_0: float, # phaseshift is extracted at phi(s_0)
        **solve_ivp_kwargs # passed to solve_se
    ):
        '''
        Calculates the lth partial wave phase shift at the specified energy.
        solve_ivp_kwargs are passed to solve_se
        '''
        # Should s_endpts be [s_min, s_endpts[1]]?
        solution = self.solve_se(energy, args, s_endpts, l=l, **solve_ivp_kwargs)
        u = solution(s_0)
        rl = 1/s_0 * (u[0]/u[1])
        return np.log(
            (H_minus(s_0, l) - s_0*rl*H_minus_prime(s_0, l)) / 
            (H_plus(s_0, l) - s_0*rl*H_plus_prime(s_0, l))
        ) / 2j


    def phi(self,
        energy: float, # center-of-mass energy
        args: np.array, # interaction parameters
        s_mesh: np.array, # s where phi(s) in calculated
        l: int, # angular momentum
        rho_0: float = None, # What do we call "zero"?
        phi_threshold: float = PHI_THRESHOLD,
        **solve_ivp_kwargs # passed to solve_se
    ):
        '''
        Computes phi(s_mesh)
        '''
        if rho_0 is None:
            rho_0 = (phi_threshold / Gamow_factor(l, self.interaction.eta)) ** (1/(l+1))

        solution = self.solve_se(energy, args, [rho_0, s_mesh[-1]], l, rho_0=rho_0,
                                 phi_threshold=phi_threshold, **solve_ivp_kwargs)

        ii_0 = np.where(s_mesh < rho_0)[0]
        y = solution(s_mesh)[0]
        y[ii_0] = 0
        return y
    

    def phi_normalized(self,
        energy: float, # center-of-mass energy
        args: np.array, # interaction parameters
        s_mesh: np.array, # s where phi(s) in calculated
        l: int, # angular momentum
        **solve_ivp_kwargs # passed to solve_se
    ):
        '''
        Computes phi(s_mesh), but with max(phi(s_mesh)) = 1.
        '''
        phi = self.phi(energy, args, s_mesh, l, **solve_ivp_kwargs)
        return phi / np.max(np.abs(phi))

