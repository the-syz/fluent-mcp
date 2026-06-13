from __future__ import annotations

import argparse
import json

from .fluent_tools import run_solver


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 Fluent case，并生成可审计输出。")
    parser.add_argument("project_dir")
    parser.add_argument("case_file")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--data-file", default=None)
    parser.add_argument("--fluent-path", default=None)
    parser.add_argument("--backend", choices=["pyfluent", "batch"], default="pyfluent")
    parser.add_argument("--fluent-dimension", default="3ddp")
    parser.add_argument("--processor-count", type=int, default=1)
    parser.add_argument("--batch-timeout", type=int, default=1800)
    args = parser.parse_args()
    result = run_solver(
        project_dir=args.project_dir,
        case_file=args.case_file,
        data_file=args.data_file,
        iterations=args.iterations,
        fluent_path=args.fluent_path,
        backend=args.backend,
        fluent_dimension=args.fluent_dimension,
        processor_count=args.processor_count,
        batch_timeout=args.batch_timeout,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
