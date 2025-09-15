import argparse
import os
from unziphap import main
args = argparse.ArgumentParser()
args.add_argument("dir", type=str, help="Dir to the .hap file")
args = args.parse_args()
if args.dir is None or not os.path.isdir(args.dir):
    raise ValueError("Please provide a valid directory containing .hap files.")
for file in os.listdir(args.dir):
    if file.endswith(".hap"):
        hap_file = os.path.join(args.dir, file)
        abc_file, pa_file = main(hap_file)
        cmd = f"conda run -p ./.conda python script/process_abc_panda.py --abc {abc_file} --pa {pa_file} --level raw"
        print(cmd)
        os.system(cmd)