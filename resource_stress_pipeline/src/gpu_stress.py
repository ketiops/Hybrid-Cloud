import time
import threading
import numpy as np
import pycuda.autoinit
import pycuda.driver as cuda
from pycuda.compiler import SourceModule

def gpu_stress(duration: int, device_id: int):

    cuda.Device(device_id).make_context()
    
    mod = SourceModule("""
    __global__ void stress_test(float *a, float *b, float *c)
    {
        int idx = threadIdx.x + blockIdx.x * blockDim.x;
        c[idx] = a[idx] + b[idx];
    }
    """)

    stress_test = mod.get_function("stress_test")

    # Set Test data size
    N = 1024 * 1024 * 10  # 10M elements

    a = np.random.randn(N).astype(np.float32)
    b = np.random.randn(N).astype(np.float32)
    c = np.empty_like(a)

    a_gpu = cuda.mem_alloc(a.nbytes)
    b_gpu = cuda.mem_alloc(b.nbytes)
    c_gpu = cuda.mem_alloc(c.nbytes)

    cuda.memcpy_htod(a_gpu, a)
    cuda.memcpy_htod(b_gpu, b)

    # Set size of block & grid
    block_size = 1024
    grid_size = (N + block_size - 1) // block_size

    # stress test start
    end_time = time.time() + duration

    print(f"GPU {device_id} memory load. (Duration: {duration} s)")

    start = time.time()

    while time.time() < end_time:
        stress_test(a_gpu, b_gpu, c_gpu, block=(block_size, 1, 1), grid=(grid_size, 1))

    cuda.memcpy_dtoh(c, c_gpu)

    end = time.time()
    print(f"GPU {device_id} stress test done. (Duration:  {end - start:.2f}s)")

    # VRAM allocation reset
    a_gpu.free()
    b_gpu.free()
    c_gpu.free()

    # CUDA Context quit
    cuda.Context.pop()

def gpu_stress_all(duration: int):

    num_gpus = cuda.Device.count()

    threads = []
    
    for device_id in range(num_gpus):
        thread = threading.Thread(target=gpu_stress, args=(duration, device_id))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()