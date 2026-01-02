import os
import subprocess
import re
import glob
import multiprocessing
import json

# Configuration
BIN_DIR = "bin"
TRACES_DIRS = ["traces/GAP", "traces/charlie"]
WARMUP_INSTS = 10000000 # 10 Million
SIM_INSTS = 50000000    # 50 Million (Reduced for faster turnaround, adjust as needed)
JOBS = 4

CONFIGS = [
    "1C.fullBW.nopref",
    "1C.fullBW.mypref",
    "1C.limitBW.nopref",
    "1C.limitBW.mypref",
    "1C.fullBW.custom",
    "1C.limitBW.custom",
    "1C.fullBW.pythia",
    "1C.limitBW.pythia"
]

def get_traces():
    traces = []
    for d in TRACES_DIRS:
        # Get all files ending in .gz or .xz
        for ext in ["*.gz", "*.xz"]:
            traces.extend(glob.glob(os.path.join(d, ext)))
    return sorted(traces)

def run_simulation(args):
    config, trace = args
    binary = os.path.join(BIN_DIR, config)
    cmd = [
        binary,
        "--warmup-instructions", str(WARMUP_INSTS),
        "--simulation-instructions", str(SIM_INSTS),
        trace
    ]
    
    print(f"Starting: {config} on {os.path.basename(trace)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout
        
        # Parse IPC
        # Search for "CPU 0 cumulative IPC: 1.011" or similar
        match = re.search(r"CPU 0 cumulative IPC: ([\d\.]+)", output)
        if match:
            ipc = float(match.group(1))
            return (config, trace, ipc)
        else:
            print(f"Error parsing output for {config} {trace}")
            return (config, trace, None)
    except Exception as e:
        print(f"Exception running {config} {trace}: {e}")
        return (config, trace, None)

def main():
    traces = get_traces()
    print(f"Found {len(traces)} traces.")
    
    tasks = []
    for config in CONFIGS:
        for trace in traces:
            tasks.append((config, trace))
            
    print(f"Running {len(tasks)} simulations with {JOBS} threads...")
    
    with multiprocessing.Pool(JOBS) as pool:
        results = pool.map(run_simulation, tasks)
        
    # Organize Results
    data = {}
    for config, trace, ipc in results:
        trace_name = os.path.basename(trace)
        if trace_name not in data:
            data[trace_name] = {}
        data[trace_name][config] = ipc

    # Print Summary Table
    print("\n\n=== RESULTS SUMMARY ===")
    header = f"{'Trace':<40}" + "".join([f"{c:<20}" for c in CONFIGS])
    print(header)
    print("-" * len(header))
    
    for trace in sorted(data.keys()):
        row = f"{trace:<40}"
        for config in CONFIGS:
            val = data[trace].get(config)
            val_str = f"{val:.4f}" if val is not None else "N/A"
            row += f"{val_str:<20}"
        print(row)
        
    # Save to JSON
    with open("lab_results.json", "w") as f:
        json.dump(data, f, indent=2)
    print("\nResults saved to lab_results.json")

if __name__ == "__main__":
    main()
