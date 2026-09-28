"""
Fly JJS RL Fly Brain Package
"""
import os

# The brain simulation (numba) already uses every core. Multithreaded BLAS in the
# learner's matrix products would spin threads that starve it: a 59k-neuron readout made
# each brain step 5x slower. Single-threaded BLAS is plenty for matrix-vector products.
for _var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")

__version__ = "1.4.0"
