from __future__ import annotations

import argparse

from acacium.acquisition import fetch_documents
from acacium.catalogue import load_manifest
from acacium.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and SHA-256 verify the declared public board-paper corpus."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files even when the existing local copy passes integrity validation.",
    )
    arguments = parser.parse_args()
    settings = get_settings()
    result = fetch_documents(
        load_manifest(settings.manifest_path), settings.documents_dir, force=arguments.force
    )
    print(
        f"Downloaded: {len(result.downloaded)}; verified local copies reused: {len(result.reused)}"
    )


if __name__ == "__main__":
    main()
