import time
import requests
import argparse
import subprocess
from pystress import pystress
from gpu_stress import gpu_stress_all

parser = argparse.ArgumentParser(description="Workload Stress Test")
parser.add_argument("--time",type=int,default=300,help="Time for stress test (Unit=minute)")
parser.add_argument("--cpu_stress",type=bool,default=False,help="Activate CPU Stress [True,False]")
parser.add_argument("--memory_stress",type=bool,default=False,help="Activate Memory Stress [True,False]")
parser.add_argument("--gpu_stress",type=bool,default=False,help="Activate GPU Stress [True,False]")
parser.add_argument("--disk_stress",type=bool,default=False,help="Activate disk I/O Stress [True,False]")
parser.add_argument("--network_stress",type=bool,default=False,help="Activate network I/O Stress [True,False]")
parser.add_argument("--cpu_num",type=int,default=12,help="Define CPU core nums (Default: 12)")
parser.add_argument("--mem_amount",type=str,default=2000,help="Amount of Memory Stress (default=2000)")
parser.add_argument("--size_mb",type=int,default=500,help="Amount of Disk Stress (default=500)")
parser.add_argument("--net_url",type=str,default='http://localhost',help="Address of Network I/O Test(ex: http://localhost)")
parser.add_argument("--net_port",type=str,default='5000',help="Port of Network I/O Test Destination")
parser.add_argument("--network_mode",type=str,default='preprocess', help="Test mode for Network I/O [preprocess, inference]")
args = parser.parse_args()

cuda_kernel_code = """
__global__ void gpu_load_kernel(int *data, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        for (int i = 0; i < 10000; ++i) {
            data[idx] += 1; 
        }
    }
}
"""

def test_info(total_time:int):
    print(f"\n\nTest information : \n Total Test Time : {round(total_time/60,4)}m \
          \n each test duration : {args.time}m \
          \n cpu stress test : {args.cpu_stress} \
          \n memory stress test : {args.memory_stress} \
          \n disk I/O test : {args.disk_stress} \
          \n network I/O test : {args.network_stress} \
          \n ")
    
def cpu_stress(duration:int):
    print(f"\n cpu cores using cpu stress test : {args.cpu_num}")
    print(f"Generating CPU load. (Duration: {duration} s)")
    pystress(exec_time=duration,proc_num=args.cpu_num) # pystress CPU 부하 테스트
    print(f"CPU Stress Process created. (Duration: {duration} m)")
    
def memory_stress(duration:int):
    print(f"\n memory amount using memory stress test : {args.mem_amount}")
    mem_amount=args.mem_amount
    print(f"Generating memory load. (Duration: {duration} s)")
    command = ["stressapptest", "-s", str(duration), "-M", str(mem_amount)]
    subprocess.run(command)
    print(f"Memory Stress test done. (Duration: {duration} s)")
    
def disk_stress(duration:int):
    print(f"\n amount of disk stress : {args.size_mb}")
    print(f"Generating disk I/O load. (Duration: {duration} s)")
    #file write
    with open('tmp','wb') as f:
        f.write(b'\0' * (args.size_mb * 1024 * 1024))
        time.sleep(duration//2)
    #file read
    with open('tmp','rb') as f:
        data= f.read()
        time.sleep(duration//2)
        
def send_large_post_request():
    # Create large data
    if args.mode=="preprocess":
        large_data = 'x' * 10**8  # 10MB data
    else:
        large_data = 'x' * 10**4
    url = f"{args.net_url}:{args.net_port}/post"
    response = requests.post(url, data=large_data)
    print(f"Sent {len(large_data)} bytes to {url}, received {len(response.content)} bytes")

def send_large_get_request():
    url = f"{args.net_url}:{args.net_port}/get"
    response = requests.get(url)
    print(f"Received {len(response.content)} bytes from {url}")

def network_stress(duration):
    print(f"Network I/O Test mode : {args.network_mode}")
    print(f"Generating network I/O load. (Duration: {duration} s)")
    end_time = time.time() + duration
    while time.time() < end_time:
        send_large_post_request()
        send_large_get_request()
        time.sleep(1)

def main():
    test_num = args.cpu_stress + args.mem_stress + args.gpu_stress + args.disk_stress + args.network_stress
    total_time = args.time * 60 * test_num
    test_time = args.time * 60
    test_info(total_time)
    if args.cpu_stress:
        cpu_stress(test_time)
    if args.memory_stress:
        memory_stress(test_time)
    if args.gpu_stress:
        gpu_stress_all(test_time)
    if args.disk_stress:
        disk_stress(test_time)
    if args.network_stress:
        network_stress(test_time)

if __name__== "__main__":
    main()