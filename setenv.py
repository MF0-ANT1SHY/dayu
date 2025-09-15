import os

# Create a single command that chains everything together
full_command = """
rm -rf ./.conda && \
conda create -p ./.conda python=3.10.18 -y && \
conda run -p ./.conda python setup.py install
"""

os.system(full_command)