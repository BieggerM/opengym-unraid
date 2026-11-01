#!/usr/bin/env python3
"""Resolve upstream latest images and compare them with the published package labels."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

UPSTREAM = "ghcr.io/duartesantos8/opengym-"


def inspect(reference, field):
    result = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", reference,
         "--format", "{{json ." + field + "}}"],
        check=True, text=True, capture_output=True, timeout=60)
    return json.loads(result.stdout)


def amd64_digest(manifest):
    if "manifests" in manifest:
        matches = [entry["digest"] for entry in manifest["manifests"]
                   if entry.get("platform", {}).get("os") == "linux"
                   and entry.get("platform", {}).get("architecture") == "amd64"]
        if len(matches) != 1:
            raise ValueError("Expected one upstream linux/amd64 image")
        digest = matches[0]
    else:
        digest = manifest["digest"]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Invalid upstream digest")
    return digest


def labels(reference):
    image = inspect(reference, "Image")
    # Image is a platform map for an index and a config object for a single manifest.
    image = image.get("linux/amd64", image)
    if image.get("architecture") != "amd64" or image.get("os") != "linux":
        raise ValueError("Expected linux/amd64 image configuration")
    return image.get("config", {}).get("Labels") or {}


def needs_rebuild(published, api, web, revision):
    return (published.get("io.opengym.upstream.api") != api
            or published.get("io.opengym.upstream.web") != web
            or published.get("org.opencontainers.image.revision") != revision)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published-image", default="ghcr.io/bieggerm/opengym-unraid:latest")
    parser.add_argument("--revision", default=os.environ.get("GITHUB_SHA", "local"))
    args = parser.parse_args()
    images, versions = {}, {}
    for component in ("api", "web"):
        repository = UPSTREAM + component
        digest = amd64_digest(inspect(repository + ":latest", "Manifest"))
        images[component] = repository + "@" + digest
        versions[component] = labels(images[component]).get("org.opencontainers.image.version")
    if versions["api"] and versions["web"] and versions["api"] != versions["web"]:
        raise RuntimeError(f"Upstream latest releases do not match yet: {versions}. Retry after the upstream release finishes.")
    try:
        published = labels(args.published_image)
    except subprocess.CalledProcessError:
        # No published package on first run, or temporarily inaccessible: rebuild/test rather
        # than incorrectly claiming that it is up to date. Publication still has to succeed.
        published = {}
    output = {
        "api_image": images["api"], "web_image": images["web"],
        "changed": str(needs_rebuild(published, images["api"], images["web"], args.revision)).lower(),
    }
    print(json.dumps(output, indent=2))
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as destination:
            for key, value in output.items():
                destination.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
