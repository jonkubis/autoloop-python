#!/usr/bin/env python

import sys
import soundfile as sf #pip install pysoundfile
import struct
import numpy as np
from multiprocessing import Pool
import time

start_time = time.time()

JAVA_Integer_MAX_VALUE = (2^31)-1
JAVA_Integer_MAX_VALUE_as_float = float(JAVA_Integer_MAX_VALUE)

def findloop(samples, skip, step, minLength, tailLength):
	maxlen = len(samples[0]) - tailLength
	best = None
	besterr = sys.float_info.max #python Double.MAX_VALUE;
	channels = len(samples)
	
	for start in range(skip,maxlen,step):
		print (start)

		for end in range (start + minLength,maxlen):
			error = estimate2(samples, start, end, tailLength, channels)
			if (best is None) or (error < besterr):
				best = (start, end, error);
				besterr = error	
				print("Best error so far: " + str(besterr))
	if (best is None):
		return None, None, None
	else:
		return best[0], best[1], best[2]
		
def findloopthreaded(samples, skip, step, minLength, tailLength, threadcnt):
	maxlen = len(samples[0]) - tailLength
	channels = len(samples)
	
	print ("Starting search with %d threads" %(threadcnt))
	pool = Pool(threadcnt)
	
	results = []
	
	for start in range(skip,maxlen,step):
		results.append(pool.apply_async(findloopworker, args=(samples,start,minLength,maxlen,tailLength,channels)))
	
	pool.close()
	pool.join()
	results = [r.get() for r in results]
	
	best = None
	besterr = sys.float_info.max #python Double.MAX_VALUE;
	
	for r in results:
		if r[0] is not None:
			print (r)
			if r[2] < besterr:
				best = r
				besterr = r[2]
	return best
		
def findloopworker(samples,start,minLength,maxlen,tailLength,channels):
	print (start)
	startplustaillength = start+tailLength
	
	best = None
	besterr = sys.float_info.max #python Double.MAX_VALUE;
	
	for end in range (start + minLength,maxlen):
		error = float(0.0)
		for ch in range(channels):
			error += np.sum((samples[ch][start:startplustaillength]-samples[ch][end:end+tailLength])**2)

		if (best is None) or (error < besterr):
			best = (start, end, error)
			besterr = error	
			#print("Best error so far: " + str(besterr))
	if (best is None):
		return None, None, None
	else:
		return best[0], best[1], best[2]
	
def estimate(samples, start, end, tailLength, channels):
	error = float(0.0)
	for ch in range(channels):
		for i in range(tailLength):
			a = samples[ch][start + i]
			b = samples[ch][end + i]
			diff = (a - b) * (a - b)
			error += diff
	return error

def estimate2(samples, start, end, tailLength, channels):
	error = float(0.0)
	for ch in range(channels):
		error += np.sum((samples[ch][start:start+tailLength]-samples[ch][end:end+tailLength])**2)
		#error += np.sum((samples[ch][start:start+tailLength]-samples[ch][end:end+tailLength])*(samples[ch][start:start+tailLength]-samples[ch][end:end+tailLength]))
	return error

if (len(sys.argv) < 6):
	print("Usage: Autoloop file.wav skip step minlen tail [threadcnt]")
	sys.exit(0)

samples, samplerate = sf.read(sys.argv[1],always_2d=True) #
samples = np.swapaxes(samples,0,1)

normalized = np.empty(shape=(np.shape(samples)))

for ch in range(len(normalized)):
	for i in range(len(normalized[ch])):
		normalized[ch][i] = float(samples[ch][i]) / JAVA_Integer_MAX_VALUE_as_float

skip   = int(sys.argv[2])
step   = int(sys.argv[3])
minlen = int(sys.argv[4])
tail   = int(sys.argv[5])
if len(sys.argv) >= 7: #thread count argument passed
	threadcnt = int(sys.argv[6])
else:
	threadcnt = 1

if len(samples) == 1:
	print("%d channel, %d samples" % (len(samples), len(samples[0])))
else:
	print("%d channels, %d samples" % (len(samples), len(samples[0])))
	
if (threadcnt == 1):
	loopstart, loopend, looperror = findloop(normalized, skip, step, minlen, tail)
else:
	loopstart, loopend, looperror = findloopthreaded(normalized, skip, step, minlen, tail, threadcnt)

if (loopstart is not None):
	duration = (loopend - loopstart) / float(samplerate);
	print("best match: %d - %d [%1.2f sec]" %(loopstart, loopend, duration))
	channels = len(samples)
	err = estimate(normalized, loopstart, loopend, tail, len(samples))
	print("error: %s\n" % err)
else:
	print("failed to find loop")
	
print("--- %s seconds ---" % (time.time() - start_time))