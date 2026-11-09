"""Fail if the working tree (and optionally Git history) contains secrets or environment identifiers.

Run before every push: `python scripts/scan_secrets.py --history`. CI runs it too.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "azure_storage_key": re.compile(r"AccountKey=[A-Za-z0-9+/=]{20,}"),
    "sas_signature": re.compile(r"[?&]sig=[A-Za-z0-9%+/=]{20,}"),
    "instrumentation_key": re.compile(r"InstrumentationKey=[0-9a-fA-F-]{36}"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\."),
    "generic_secret": re.compile(r"(?i)(?:password|client_secret|api_key)\s*[:=]\s*['\"][^'\"]{8,}"),
    # Public-repo hygiene: no tenant, subscription, or item IDs; no live hostnames; no local paths.
    "guid": re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
    "live_hostname": re.compile(r"\b[a-z0-9-]+\.(?:azurewebsites\.net|onmicrosoft\.com|vault\.azure\.net)\b"),
    "local_user_path": re.compile(r"(?i)[A-Z]:\\Users\\[^\\<\s]+\\|/home/[a-z][a-z0-9_-]+/|/Users/[A-Za-z][A-Za-z0-9_-]+/"),
}

# Azure built-in role definition IDs are public and identical in every tenant.
ALLOWED_GUIDS = {
    "4633458b-17de-408a-b874-0445c86b69e6",  # Key Vault Secrets User
    "b86a8fe4-44ce-4948-aee5-eccb2c155cd7",  # Key Vault Secrets Officer
    "b7e6dc6d-f1e8-4753-8033-0f276bb0955b",  # Storage Blob Data Owner
    "3913510d-42f4-4e42-8a64-420c390055eb",  # Monitoring Metrics Publisher
}


def scan_text(label: str, text: str) -> list[str]:
    findings = []
    for name, pattern in PATTERNS.items():
        matches = list(pattern.finditer(text))
        if name == "generic_secret":
            matches = [match for match in matches if "@Microsoft.KeyVault(" not in match.group(0)]
        if name == "guid":
            matches = [match for match in matches if match.group(0).lower() not in ALLOWED_GUIDS]
        if matches:
            findings.append(f"{label}: {name}")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    findings = []
    for path in subprocess.check_output(["git", "ls-files"], text=True).splitlines():
        if path == "scripts/scan_secrets.py":
            continue
        try:
            findings.extend(scan_text(path, Path(path).read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    if args.history:
        history = subprocess.run(
            ["git", "log", "-p", "--all", "--no-ext-diff", "--", ".", ":(exclude)scripts/scan_secrets.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout
        findings.extend(scan_text("git-history", history))
    if findings:
        raise SystemExit("potential secrets found:\n" + "\n".join(findings))
    print("secret scan passed")


if __name__ == "__main__":
    main()
