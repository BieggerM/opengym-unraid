# openGym for Unraid

One Docker image and one running container, using the official openGym API and web images.
This is a standalone packaging repository: it contains no openGym application source, no
exercise media, and no fork to synchronize. The app and its media are copied from upstream
images during the Docker build. Upstream project: https://github.com/DuarteSantos8/openGym.

```text
upstream opengym-api:latest ─┐
                            ├─ build and test ─ opengym-unraid:latest ─ one Unraid container
upstream opengym-web:latest ─┘
```

## Automatic upstream updates

The GitHub workflow checks daily for changes to the upstream `latest` images. It compares
their linux/amd64 digests and this packaging commit against labels on the published Unraid
image. If nothing changed, it skips building and publishing.

When either upstream image changes, it:

1. Resolves both current `latest` images to their exact digests for that build. There is no
   manually pinned release to maintain. If the API and web release version labels disagree,
   it fails and can retry at the next check after upstream finishes publishing.
2. Builds a single container from those images.
3. Tests signup, admin access, data persistence across container replacement, sessions,
   proxying, assets, URL prefixes, healthchecks, service failure and clean shutdown.
4. Publishes the **exact tested image** to `ghcr.io/bieggerm/opengym-unraid:latest` and a unique
   `sha-...` rollback tag. A failed build or test leaves the published image unchanged.

No merge of upstream source is involved. Pull requests build and test only. Main-branch
pushes also publish once automatic publication is enabled. Updating the running container
is still handled through Unraid's Docker update action or your chosen update mechanism.

Automatic publication is opt-in: set the repository Actions variable **`AUTO_PUBLISH=true`**
after testing the first image on your Unraid server. Without it, scheduled runs are skipped;
manual runs only publish when their **publish** checkbox is checked. GitHub schedules run
from the default branch and can be delayed or disabled for inactive public repositories;
see [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Build and test locally

From this directory, with Docker, Buildx, Python 3 and Bash installed:

```bash
python3 unraid/validate.py
python3 -m unittest discover -s scripts -p 'test_*.py'
bash -n unraid/entrypoint.sh
docker build --pull -f unraid/Dockerfile -t opengym-unraid:test .
python3 unraid/smoke-test.py opengym-unraid:test
```

The smoke test removes its disposable containers and volume. If your development Docker
build network cannot resolve Alpine's package server, retry the build with `--network=host`.
To inspect current upstream images and whether a published package needs updating:

```bash
python3 scripts/upstream.py --revision YOUR_PACKAGING_COMMIT
```

The build defaults to upstream `latest`. You can temporarily select a release with
`--build-arg OPENGYM_VERSION=X.Y.Z`, or supply exact `OPENGYM_API_IMAGE` and
`OPENGYM_WEB_IMAGE` references as the update workflow does.

## Test on your own Unraid server before publication

Export your local image, then copy the archive and XML to the server:

```bash
docker save -o /tmp/opengym-unraid-test.tar opengym-unraid:test
scp /tmp/opengym-unraid-test.tar root@UNRAID_IP:/mnt/user/appdata/
scp templates/opengym.xml root@UNRAID_IP:/boot/config/plugins/dockerMan/templates-user/my-opengym.xml
```

In the Unraid terminal:

```bash
docker load -i /mnt/user/appdata/opengym-unraid-test.tar
```

Open **Docker → Add Container** and select **openGym**. Change **Repository** to
`opengym-unraid:test` to use the imported image. Use a separate appdata folder such as
`/mnt/user/appdata/opengym-test` while testing, and select an unused host port.

Set **Application URL** to the exact browser address, such as `http://192.168.1.10:8085`,
without a trailing slash. Set **Passkey hostname** to the hostname or IP from that URL,
without the scheme, port or path. Apply, then open that address and create your profile.
Password login is enabled for LAN testing; the first profile becomes administrator.

## Configuration and data

The template publishes container port `8080` and maps `/data` to
`/mnt/user/appdata/opengym`. `/data` contains profiles, workouts, uploads, session secrets
and push keys; stop the container and back up that whole folder for a consistent backup.
Browser-only guest data stays on each device. Never run two APIs against the same data folder.

Set `ORIGIN` and `RP_ID` before registering passkeys. Remote passkeys require HTTPS on a
domain; use password login for ordinary HTTP LAN access. Forward your HTTPS proxy to the
chosen Web UI port and use its URL as `ORIGIN`. The Docker WebUI shortcut opens local HTTP;
edit it to your HTTPS address if using a proxy. Set `INVITE_ONLY=1` after your first profile
if later registrations should require an invitation.

`BASE_PATH=/gym` supports a reverse proxy that passes its prefix through, with no trailing
slash. Leave it empty when the proxy strips the prefix. `ORIGIN` never includes that path.
For the full application reference, see [upstream self-hosting](https://github.com/DuarteSantos8/openGym/blob/main/docs/SELF_HOSTING.md).

The API keeps upstream's root/coach privilege separation; nginx workers use the nginx user.
There is no PUID/PGID support, privileged mode, host networking or Docker socket requirement.
Internal port `3000` is not published. The entrypoint fixes internal API/proxy ports, `DATA_DIR`,
`BACKEND`, `TRUST_PROXY` and `RESOLVER`. CLI-based Claude/Codex coach runtimes are not bundled.

openGym is by Duarte Santos and contributors. Preserve [LICENSE](LICENSE) and
[NOTICE.md](NOTICE.md), also included in the image at `/usr/share/opengym/`.
Exercise media are separately licensed; the upstream notice permits a non-commercial
openGym fork to retain the unmodified 180 px media with the notice. See it for other uses.

## Development disclosure

The Unraid packaging, automation and documentation were developed with AI coding assistance.
Automated Docker integration tests pass; testing in a real Unraid Docker Manager is still
pending. The upstream openGym application is a separate project maintained by its own authors.
