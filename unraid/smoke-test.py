#!/usr/bin/env python3
"""Exercise the packaged image with disposable containers and a Docker volume."""
import http.cookiejar
import json
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


def docker(*args, check=True):
    return subprocess.run(["docker", *args], check=check, text=True, capture_output=True)


def main():
    image = sys.argv[1] if len(sys.argv) > 1 else "opengym-unraid:test"
    name = "opengym-smoke-" + secrets.token_hex(5)
    volume = name + "-data"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(path, body=None, method=None, prefix=""):
        headers = {"Origin": origin, "Content-Type": "application/json"}
        req = urllib.request.Request(origin + prefix + path,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers=headers, method=method)
        with client.open(req, timeout=10) as response:
            data = response.read()
            if "application/json" in response.headers.get("Content-Type", ""):
                data = json.loads(data)
            return data, response.headers

    def start(prefix=""):
        docker("run", "-d", "--name", name, "-p", f"127.0.0.1:{port}:8080",
               "-v", f"{volume}:/data", "-e", f"ORIGIN={origin}",
               "-e", "RP_ID=127.0.0.1", "-e", f"BASE_PATH={prefix}", image)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                request("/api/health", prefix=prefix)
                return
            except (OSError, urllib.error.URLError):
                if docker("inspect", "-f", "{{.State.Running}}", name).stdout.strip() != "true":
                    raise RuntimeError("container exited during startup")
                time.sleep(0.5)
        raise RuntimeError("API did not become ready")

    def remove():
        docker("rm", "-f", name, check=False)

    def stopped_cleanly():
        docker("stop", "-t", "10", name)
        assert docker("inspect", "-f", "{{.State.ExitCode}}", name).stdout.strip() == "0"

    docker("volume", "create", volume)
    try:
        start()
        page, headers = request("/")
        assert b"<html" in page.lower()
        assert "script-src" in headers["Content-Security-Policy"]
        icon, _ = request("/icon-512.png")
        assert icon.startswith(b"\x89PNG")
        config, _ = request("/api/config")
        assert config["password_login"] is True
        password = secrets.token_urlsafe(24)
        account, _ = request("/api/register/password", {"name": "Unraid smoke test", "password": password})
        uid = account["user"]["id"]
        me, _ = request("/api/me")
        assert me["user"]["id"] == uid
        # Ensure FIRST_USER_ADMIN works through the real proxy, not just an env assertion.
        request("/api/admin/users")
        state = {"workouts": [], "routines": [], "settings": {"unraidSmokeTest": name}}
        request("/api/data", {"state": state, "baseRev": 0}, method="PUT")
        before, _ = request("/api/data")
        assert before["state"]["settings"]["unraidSmokeTest"] == name
        print("PASS: web UI, static assets, CSP, API proxy, password signup, admin and data write", flush=True)

        # Replacing the container models an Unraid image upgrade: only /data survives.
        stopped_cleanly()
        remove()
        start("/gym")
        me, _ = request("/api/me", prefix="/gym")
        assert me["user"]["id"] == uid  # same session secret and account
        after, _ = request("/api/data", prefix="/gym")
        assert after["state"] == before["state"]
        page, _ = request("/", prefix="/gym")
        assert b"<html" in page.lower()
        # Run Docker's actual healthcheck for this prefix too.
        probe = docker("image", "inspect", "-f", "{{json .Config.Healthcheck.Test}}", image)
        command = json.loads(probe.stdout)
        assert command[0] == "CMD-SHELL"
        docker("exec", name, "sh", "-c", command[1])
        print("PASS: data and session survive replacement; /gym and image healthcheck work", flush=True)
        stopped_cleanly()
        remove()

        for service, command in [
            ("API", 'kill -KILL "$(pgrep -x node)"'),
            ("nginx", 'kill -KILL "$(cat /run/nginx/nginx.pid)"'),
        ]:
            start()
            docker("exec", name, "bash", "-c", command)
            result = docker("wait", name).stdout.strip()
            assert result != "0", f"{service} failure did not fail the container"
            remove()
            print(f"PASS: {service} failure stops the container with nonzero status", flush=True)

        invalid = docker("run", "--rm", "-e", "BASE_PATH=gym", image, check=False)
        assert invalid.returncode != 0 and 'does not start with' in invalid.stderr
        print("PASS: invalid URL prefix is rejected; SIGTERM shuts down cleanly", flush=True)
    except BaseException:
        print(docker("logs", name, check=False).stdout, file=sys.stderr)
        print(docker("logs", name, check=False).stderr, file=sys.stderr)
        raise
    finally:
        remove()
        docker("volume", "rm", volume, check=False)


if __name__ == "__main__":
    main()
