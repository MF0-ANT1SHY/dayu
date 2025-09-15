from setuptools import setup, find_packages

setup(
    name="dayu",
    version="0.1.0",
    packages=find_packages(),  # 会自动找到 dayu 目录及其子包
    install_requires=[
        "leb128==1.0.8",
        "mutf8==1.0.6",
        "ordered-set==4.1.0",
        "graphviz==0.20.3",
    ],
    python_requires="==3.10.18",
)