import zipfile
import os
import tempfile
import shutil
import json
import subprocess
import argparse

class HapFileError(Exception):
    """Custom exception for .hap parser errors."""
    pass


def get_bundle_name(file_path):
    """
    从 .hap 中读取并解析根目录下的 pack.info, 返回 bundleName

    Args:
        file_path (str): Path to the .hap file.

    Returns:
        str: bundleName
    
    Raises:
        HapFileError: 如果文件不是合法.hap文件或 pack.info 不存在.
    """
    if not zipfile.is_zipfile(file_path):
        raise HapFileError(f"{file_path} is not a valid compressed .hap file")

    with zipfile.ZipFile(file_path, "r") as hap:
        if "pack.info" not in hap.namelist():
            raise HapFileError(f"'pack.info' not found in {file_path}")

        with hap.open("pack.info") as f:
            try:
                data = json.load(f)
                return data["summary"]["app"]["bundleName"]
            except Exception as e:
                raise HapFileError(f"Failed to parse pack.info in {file_path}: {e}")


def parse_hap(file_path):
    """
    Parse a .hap file, extract ets/modules.abc into a temp dir
    and rename it to <bundleName>.abc.
    
    Args:
        file_path (str): Path to the .hap file.
    
    Returns:
        str: Path to the extracted renamed abc file (temporary).
    """
    if not zipfile.is_zipfile(file_path):
        raise HapFileError(f"{file_path} is not a valid compressed .hap file")

    with zipfile.ZipFile(file_path, "r") as hap:
        target_path = "ets/modules.abc"
        
        if target_path not in hap.namelist():
            raise HapFileError(f"Required file '{target_path}' not found in {file_path}")
        
        # 获取 bundleName
        bundle_name = get_bundle_name(file_path)

        # 建立临时目录
        temp_dir = tempfile.mkdtemp(prefix="hap_extract_")
        hap.extract(target_path, temp_dir)

        extracted_path = os.path.join(temp_dir, target_path)
        renamed_path = os.path.join(temp_dir, f"{bundle_name}.abc")

        # 重命名
        os.rename(extracted_path, renamed_path)

        return renamed_path

def disasm_abc(abc_file):
    """
    调用 `ark_disasm <abc_file> <output_pa_file>`,
    生成的 .pa 文件路径在临时目录中返回。

    Args:
        abc_file (str): 输入 .abc 文件路径

    Returns:
        str: 生成的临时 .pa 文件路径

    Raises:
        HapFileError: 如果 ark_disasm 执行失败
    """
    if not os.path.isfile(abc_file):
        raise HapFileError(f"abc file not found: {abc_file}")

    # 建立临时文件
    file_name = os.path.basename(abc_file)
    prefix = os.path.splitext(file_name)[0]
    fd, pa_path = tempfile.mkstemp(prefix=f"{prefix}.", suffix=".pa")
    os.close(fd)

    try:
        result = subprocess.run(
            ["ark_disasm", abc_file, pa_path],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise HapFileError(
            f"ark_disasm failed: {e}\nstdout: {e.stdout}\nstderr: {e.stderr}"
        )

    return pa_path

def parse_args():
    parser = argparse.ArgumentParser(description="Extract and disassemble .hap files.")
    parser.add_argument("hap_file", type=str, help="Path to the .hap file")
    return parser.parse_args()

def main(hap_file: str) -> [str,str]:
    """
    解析 .hap 文件，提取并反汇编 .abc 文件。

    Args:
        hap_file (str): 输入 .hap 文件路径

    Returns:
        tuple: (abc_path, pa_path)
            abc_path (str): 提取并重命名后的 .abc 文件路径
            pa_path (str): 反汇编生成的 .pa 文件路径
    """
    abc_path = parse_hap(hap_file)
    pa_path = disasm_abc(abc_path)
    return abc_path, pa_path

# Example usage:
if __name__ == "__main__":
    args = parse_args()
    hap_file = args.hap_file
    try:
        abc_path, panda_path = main(hap_file)
        print(f"Extracted .abc file: {abc_path}")
        print(f"Generated .pa file: {panda_path}")
    except HapFileError as e:
        print(f"Error: {e}")