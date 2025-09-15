import os

# Create a single command that chains everything together
full_command = """
rm -rf ./.conda && \
conda create -p ./.conda python=3.10.18 -y && \
conda run -p ./.conda pip install -r ./requirements.txt
"""

os.system(full_command)