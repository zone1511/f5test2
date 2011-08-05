from __future__ import division
import math
import time

class ResultStats(object):
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.total_wall_time = -1

    def stop(self):
        self.total_wall_time = time.time() - self.start_time

    def add(self, result):
        if result is not None:
            self.results.append(result)

    @property
    def failed_requests(self):
        return sum(1 for r in self.results if r.status != 200)

    @property
    def total_req_time(self):
        return sum(r.time for r in self.results)

    @property
    def avg_req_time(self):
        if len(self.results) > 0:
            return self.total_req_time / len(self.results)
        else:
            return 0

    @property
    def total_req_length(self):
        return sum(r.size for r in self.results)

    @property
    def avg_req_length(self):
        return self.total_req_length / len(self.results)

    def distribution(self):
        results = sorted(r.time for r in self.results)
        dist = []
        n = len(results)
        for p in (50, 66, 75, 80, 90, 95, 98, 99):
            i = p/100 * n - 0.001 #return right time if matched
            if i >= n:
                i = n-1
            else:
                i = int(i)
            dist.append((p, results[i]))
        dist.append((100, results[-1]))
        return dist

    def connection_times(self):
        if self.results[0].detail_time is None:
            return None
        connect = [r.detail_time[0] for r in self.results]
        process = [r.detail_time[1] for r in self.results]
        wait = [r.detail_time[2] for r in self.results]
        total = [r.time for r in self.results]

        results = []
        for data in (connect, process, wait, total):
            results.append((min(data), mean(data), std_deviation(data),
                            median(data), max(data)))
        return results

square_sum = lambda l: sum(x*x for x in l)
mean = lambda l: sum(l)/len(l)
deviations = lambda l, mean: [x-mean for x in l]
def std_deviation(l):
    n = len(l)
    if n == 1:
        return 0
    return math.sqrt(square_sum(deviations(l, mean(l)))/(n-1))
median = lambda l: sorted(l)[int(len(l)//2)]
