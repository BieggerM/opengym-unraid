#!/usr/bin/env python3
"""Check the local template contract before running the CA portal's own scanner."""
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent.parent
profile = ET.parse(root / "ca_profile.xml").getroot()
assert profile.tag == "CommunityApplications"
assert profile.findtext("Profile", "").strip(), "ca_profile.xml needs a non-empty Profile"
assert (root / "LICENSE").is_file()

template = ET.parse(root / "templates/opengym.xml").getroot()
assert template.tag == "Container" and template.get("version") == "2"
for field in ("Name", "Repository", "Support", "Project", "Overview", "Icon", "TemplateURL", "WebUI"):
    value = template.findtext(field, "").strip()
    assert value and "YOUR_" not in value, f"Missing or placeholder {field}"
assert template.findtext("Privileged") == "false"
assert template.findtext("Network") == "bridge"
configs = template.findall("Config")
keys = [(config.get("Type"), config.get("Target")) for config in configs]
assert len(keys) == len(set(keys)), "Duplicate template config targets"
assert ("Port", "8080") in keys and ("Path", "/data") in keys
for variable in ("ORIGIN", "RP_ID"):
    entry = next(config for config in configs if config.get("Target") == variable)
    assert entry.get("Required") == "true"
assert "[PORT:8080]" in template.findtext("WebUI")
print("Unraid XML: OK (run Validate and Scan in the CA portal before submission)")
