#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import collections
import time

benchmarks = collections.OrderedDict()

import logging

logger = logging.getLogger("SDMaterialX")


class Benchmark:
    def __init__(self, name):
        self.name = name
        self.start_time = 0.0
        self.end_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return 'sss111'

    def __exit__(self, type, value, traceback):
        self.end_time = time.perf_counter()
        # print('{}: {}'.format(self.name, self.end_time - self.start_time))
        global benchmarks
        runtime = (self.end_time - self.start_time)
        if self.name in benchmarks:
            old_time, call_count = benchmarks[self.name]
            benchmarks[self.name] = (old_time + runtime, call_count + 1)
        else:
            benchmarks[self.name] = (runtime, 1)
        return False


def perf_measure(func):
    def wrapper(*args, **kwargs):
        with Benchmark(str(func.__name__)):
            return func(*args, **kwargs)

    return wrapper


def dump_benchmarks():
    global benchmarks
    logger.info('Dumping Benchmarks')
    for b, (t, c) in benchmarks.items():
        logger.info('{}: Called: {}, total time {}, average: {}'.format(b, c, t, t / c))
