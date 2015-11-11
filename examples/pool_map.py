#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, print_function

from os.path import split, dirname, abspath
import sys

import time
import numpy as np
import multiprocessing as mp

# Add parent directory to beginning of path variable
sys.path.insert(0, dirname(dirname(abspath(__file__))))

import jobmanager

def func(x):
    """Example function with only one argument"""
    time.sleep(x[0]/10)
    return np.sum(x)

# Create list of parameters
a = list()
for i in range(10):
    a.append((i,2.34))

# mp.Pool example:
p_mp = mp.Pool()
res_mp = p_mp.map(func, a)

# equivalent to mp.Pool() but with progress bar:
p_jm = jobmanager.decorators.Pool()
res_jm = p_jm.map(func, a)

assert res_mp == res_jm
print("result: ", res_jm)
