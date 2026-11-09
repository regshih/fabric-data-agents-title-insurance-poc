from __future__ import annotations

import argparse
from pathlib import Path

from azure.identity import AzureCliCredential
from azure.storage.filedatalake import DataLakeServiceClient

from title_iq.fabric_api import read_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload generated parquet into the POC Lakehouse Files/source area")
    parser.add_argument("--data-dir", type=Path, default=Path("local-output/data"))
    args = parser.parse_args()
    state = read_state()
    if not state.get("workspace_id") or not state.get("lakehouse_id"):
        raise RuntimeError("run scripts/provision_workspace.py first")
    client = DataLakeServiceClient("https://onelake.dfs.fabric.microsoft.com", credential=AzureCliCredential())
    filesystem = client.get_file_system_client(state["workspace_id"])
    uploaded = 0
    for local_path in sorted(args.data_dir.glob("*.parquet")):
        remote = f"{state['lakehouse_id']}/Files/source/{local_path.name}"
        filesystem.get_file_client(remote).upload_data(local_path.read_bytes(), overwrite=True)
        print(f"uploaded {local_path.name}")
        uploaded += 1
    if not uploaded:
        raise RuntimeError(f"no parquet files found under {args.data_dir}")


if __name__ == "__main__":
    main()

