#!/usr/bin/env python3
import argparse
import sqlite3
from datetime import datetime

from dayu.ark.abcreader import AbcReader
from dayu.pandasm.reader import PandasmReader
from dayu.decompile.config import DecompilerConfig, DecompileGranularity, DecompileOutputLevel
from dayu.decompile.decompiler import Decompiler


LEVEL_MAP = {
    'raw': DecompileOutputLevel.RAW_IR,
    'llir': DecompileOutputLevel.LOW_LEVEL_IR,
    'mlir': DecompileOutputLevel.MEDIUM_LEVEL_IR,
    'hlir': DecompileOutputLevel.HIGH_LEVEL_IR,
}


def parse_args():
    p = argparse.ArgumentParser(description='统计反编译 IR 指令数量以及间接调用/throw/外部模块加载/依赖情况，并保存到数据库')
    p.add_argument('--abc', required=True, help='输入 abc 文件路径')
    p.add_argument('--pa', required=True, help='输入 Panda Assembly 文本文件路径')
    p.add_argument('--level', choices=list(LEVEL_MAP.keys()), default='llir',
                   help='统计到的 IR 层级（默认 llir）')
    p.add_argument('--db', default='metrics.db', help='SQLite 数据库文件（默认 metrics.db）')
    return p.parse_args()


def init_db(conn):
    cur = conn.cursor()
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            abc_file TEXT,
            pa_file TEXT,
            level TEXT,
            timestamp TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS method_metrics (
            run_id INTEGER,
            class_name TEXT,
            method_name TEXT,
            insn_count INTEGER,
            indirect_calls INTEGER,
            throw_count INTEGER,
            external_module_loads INTEGER,
            external_module_deps INTEGER,
            opaque_predicates INTEGER,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS external_dependency_metrics (
            run_id INTEGER,
            class_name TEXT,
            method_name TEXT,
            dependency_name TEXT,
            call_count INTEGER,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS summary_metrics (
            run_id INTEGER,
            total_ins INTEGER,
            total_indirect_calls INTEGER,
            methods_with_indirect INTEGER,
            total_throws INTEGER,
            methods_with_throw INTEGER,
            total_methods INTEGER,
            ratio_indirect REAL,
            ratio_throw REAL,
            total_external_module_loads INTEGER,
            total_external_module_deps INTEGER,
            total_opaque_predicates INTEGER,
            methods_with_opaque INTEGER,
            ratio_opaque REAL,
            methods_with_external INTEGER,
            ratio_external REAL,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
        """,
    ]
    for s in stmts:
        cur.execute(s)
    conn.commit()


def count_insns_in_method(method):
    return sum(len(getattr(b, 'insns', [])) for b in getattr(method, 'blocks', []))


def count_indirect_calls_in_method(method):
    return sum(
        1
        for b in getattr(method, 'blocks', [])
        for insn in getattr(b, 'insns', [])
        if getattr(insn, 'op', None) and 'callthis' in insn.op.lower()
    )


def count_throw_in_method(method):
    return sum(
        1
        for b in getattr(method, 'blocks', [])
        for insn in getattr(b, 'insns', [])
        if getattr(insn, 'op', None) and 'throw.' in insn.op.lower()
    )


def count_external_module_loads_in_method(method):
    return sum(
        1
        for b in getattr(method, 'blocks', [])
        for insn in getattr(b, 'insns', [])
        if getattr(insn, 'op', None) and 'ldexternalmodulevar' in insn.op.lower()
    )


def collect_external_module_dependency_calls_in_method(method):
    dep_calls = {}
    for b in getattr(method, 'blocks', []):
        insns = list(getattr(b, 'insns', []))
        for i, insn in enumerate(insns):
            op = getattr(insn, 'op', None)
            if not op:
                continue
            if 'ldexternalmodulevar' in op.lower():
                if i + 1 < len(insns):
                    next_insn = insns[i + 1]
                    next_op = getattr(next_insn, 'op', None)
                    if next_op and next_op.lower() == 'throw.undefinedifholewithname':
                        operands = str(next_insn.args[1])
                        dep_calls[operands] = dep_calls.get(operands, 0) + 1
    return dep_calls


def count_opaque_predicates_in_method(method):
    cnt = 0
    for b in getattr(method, 'blocks', []):
        insns = list(getattr(b, 'insns', []))
        for i, insn in enumerate(insns):
            op = getattr(insn, 'op', None)
            if op and op.lower() == "jmp":
                if i + 1 < len(insns) and not getattr(insns[i+1], 'label', None):
                    cnt += 1
    return cnt


def main():
    args = parse_args()

    conn = sqlite3.connect(args.db)
    try:
        init_db(conn)
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO runs (abc_file, pa_file, level, timestamp) VALUES (?, ?, ?, ?)",
            (args.abc, args.pa, args.level, datetime.now().isoformat())
        )
        run_id = cur.lastrowid

        module = Decompiler(DecompilerConfig({
            'abc': AbcReader.from_file(args.abc),
            'pandasm': PandasmReader.from_file(args.pa),
            'granularity': DecompileGranularity.MODULE,
            'output_level': LEVEL_MAP[args.level],
            'view_cfg': False
        })).decompile()

        total_ins = total_indirect_calls = methods_with_indirect = 0
        total_throws = methods_with_throw = total_methods = 0
        total_external_module_loads = 0
        total_opaque_predicates = methods_with_opaque = 0
        global_external_module_dep_calls = {}
        methods_with_external = 0

        for clz in module.classes:
            for m in clz.methods:
                total_methods += 1
                ins_cnt = count_insns_in_method(m)
                ind_calls = count_indirect_calls_in_method(m)
                thr_cnt = count_throw_in_method(m)
                ext_loads = count_external_module_loads_in_method(m)
                opaque_cnt = count_opaque_predicates_in_method(m)
                method_dep_calls = collect_external_module_dependency_calls_in_method(m)

                total_ins += ins_cnt
                total_indirect_calls += ind_calls
                total_throws += thr_cnt
                total_external_module_loads += ext_loads
                total_opaque_predicates += opaque_cnt

                if ind_calls > 0:
                    methods_with_indirect += 1
                if thr_cnt > 0:
                    methods_with_throw += 1
                if opaque_cnt > 0:
                    methods_with_opaque += 1
                if method_dep_calls:
                    methods_with_external += 1

                for dep_name, call_count in method_dep_calls.items():
                    global_external_module_dep_calls[dep_name] = global_external_module_dep_calls.get(dep_name, 0) + call_count

                cur.execute(
                    "INSERT INTO method_metrics (run_id, class_name, method_name, insn_count, indirect_calls, throw_count, external_module_loads, external_module_deps, opaque_predicates) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (run_id, clz.name, m.name, ins_cnt, ind_calls, thr_cnt, ext_loads, len(method_dep_calls), opaque_cnt)
                )

                for dep_name, call_count in method_dep_calls.items():
                    cur.execute(
                        "INSERT INTO external_dependency_metrics (run_id, class_name, method_name, dependency_name, call_count) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (run_id, clz.name, m.name, dep_name, call_count)
                    )

        ratio_indirect = (methods_with_indirect / total_methods) if total_methods else 0.0
        ratio_throw = (methods_with_throw / total_methods) if total_methods else 0.0
        ratio_opaque = (methods_with_opaque / total_methods) if total_methods else 0.0
        total_external_module_deps = len(global_external_module_dep_calls)
        ratio_external = (methods_with_external / total_methods) if total_methods else 0.0

        cur.execute(
            "INSERT INTO summary_metrics (run_id, total_ins, total_indirect_calls, methods_with_indirect, total_throws, methods_with_throw, total_methods, ratio_indirect, ratio_throw, total_external_module_loads, total_external_module_deps, total_opaque_predicates, methods_with_opaque, ratio_opaque, methods_with_external, ratio_external) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, total_ins, total_indirect_calls, methods_with_indirect,
             total_throws, methods_with_throw, total_methods,
             ratio_indirect, ratio_throw, total_external_module_loads, total_external_module_deps,
             total_opaque_predicates, methods_with_opaque, ratio_opaque,
             methods_with_external, ratio_external)
        )
        conn.commit()

    finally:
        conn.close()

    total_external_dependency_calls = sum(global_external_module_dep_calls.values())

    print(f'[DB={args.db}] Run {run_id} 完成。')
    print(f'Total IR instructions at {args.level}: {total_ins}')
    print(f'Total indirect calls: {total_indirect_calls}')
    print(f'Methods with indirect calls: {methods_with_indirect}/{total_methods} ({ratio_indirect:.2%})')
    print(f'Total throw instructions: {total_throws}')
    print(f'Methods with throw: {methods_with_throw}/{total_methods} ({ratio_throw:.2%})')
    print(f'Total external module loads (ldexternalmodulevar): {total_external_module_loads}')
    print(f'Total external module deps (unique names): {total_external_module_deps}')
    print(f'Total external dependency calls: {total_external_dependency_calls}')
    print(f'Methods with external deps: {methods_with_external}/{total_methods} ({ratio_external:.2%})')
    print(f'Total opaque predicates: {total_opaque_predicates}')
    print(f'Methods with opaque predicates: {methods_with_opaque}/{total_methods} ({ratio_opaque:.2%})')

    if global_external_module_dep_calls:
        print('External dependency call breakdown:')
        for dep_name, call_count in sorted(global_external_module_dep_calls.items()):
            print(f'  {dep_name}: {call_count} calls')


if __name__ == '__main__':
    main()