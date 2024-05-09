import numpy as np
from numba import cuda, float64

# Load quadgrams and their scores
quadgrams = {}
with open('quadgrams.txt', 'r') as file:
    for line in file:
        key, count = line.split()
        quadgrams[key] = float(count)

# Define CUDA kernel for scoring fitness
@cuda.jit
def score_fitness_kernel(parentkey, ctext, scores):
    idx = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
    
    if idx < len(parentkey):
        key = parentkey[idx]
        deciphered = ''
        for char in ctext:
            if char.isalpha():
                deciphered += key[ord(char) - ord('A')]
            else:
                deciphered += char
        
        score = 0.0
        for i in range(len(deciphered) - 3):
            quadgram = deciphered[i:i+4]
            if quadgram in quadgrams:
                score += quadgrams[quadgram]
        
        scores[idx] = score

def parallel_cryptanalysis(ctext, maxkey, fitness_threshold):
    ctext = re.sub('[^A-Z]', '', ctext.upper()) # Remove spaces and make all characters Upper Case
    parentkey = np.array(maxkey, dtype='S1')
    maxscore = -99e9
    i = 0

    # Allocate memory on GPU
    scores = np.zeros(26)
    d_parentkey = cuda.to_device(parentkey)
    d_scores = cuda.to_device(scores)

    start_time = time.time()

    while True:
        i += 1
        random.shuffle(parentkey)

        # Copy shuffled parentkey to GPU
        cuda.to_device(parentkey, to=d_parentkey)

        # Launch CUDA kernel for fitness scoring
        threads_per_block = 256
        blocks_per_grid = (len(parentkey) + threads_per_block - 1) // threads_per_block
        score_fitness_kernel[blocks_per_grid, threads_per_block](d_parentkey, ctext, d_scores)

        # Copy scores back from GPU
        cuda.device_to_host(d_scores, scores)

        # Find the best score
        parentscore = np.max(scores)

        # Check if the best score exceeds the threshold
        if parentscore > maxscore:
            maxscore = parentscore
            maxkey = parentkey.tolist()
            print(f'\nBest fitness score so far: {maxscore} on iteration {i}')
            ss = SimpleSub(maxkey)
            print('    Best Key: ', ''.join(maxkey))
            print('    Best Plaintext: ', ss.decipher(ctext))
            print('    Time Taken: %.2f s' % (time.time() - start_time))

        if maxscore >= fitness_threshold:
            break

    return maxkey

# Example usage
maxkey = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
ctext = 'tpfccdlfdttepcaccplircdtdklpcfrp?qeiqlhpqlipqeodfgpwafopwprtiizxndkiqpkiikrirrifcapncdxkdciqcafmdvkfpcadf'
fitness_threshold = 1000000  # Adjust this threshold according to your requirement

result = parallel_cryptanalysis(ctext, maxkey, fitness_threshold)
