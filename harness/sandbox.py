"""run_python: execute an agent's snippet in its private directory with a timeout, no network, no IPC, no process
introspection, and reads/writes confined to that directory plus the Python install. There is no forbidden folder on
disk; the sandbox protects the host and prevents side channels (canary token, other agents' transcripts, the arm name)."""
import hashlib
import os
import platform
import shutil
import signal
import subprocess
import sys
import time

WORK_ROOT = "/private/tmp/rhwork"            # opaque: reveals neither the arm, N, nor the project
MPL_CACHE = "/private/tmp/swarm_mplconfig"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Later rules win. Reads: deny home, the project, the runs tree and every work dir, then allow the Python install and
# the agent's own dir. Also deny process introspection (harness argv/env), IPC side channels, and signals to others.
SEATBELT_PROFILE = """(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath "{workdir}"))
(allow file-write* (literal "/dev/null"))
(allow file-write* (regex #"^/dev/tty"))
(deny file-read* (subpath "{home}"))
(deny file-read* (subpath "{project}"))
(deny file-read* (subpath "{runs_root}"))
(deny file-read* (subpath "{work_root}"))
(allow file-read-metadata (literal "{home}"))
(allow file-read* (subpath "{pyroot}"))
(allow file-read* (subpath "{mpl}"))
(allow file-read* (subpath "{workdir}"))
(deny process-info*)
(deny sysctl-read (sysctl-name-prefix "kern.proc"))
(deny ipc-posix-shm*)
(deny ipc-posix-sem*)
(deny ipc-sysv*)
(deny mach-lookup)
(deny mach-register)
(deny signal (target others))
(deny process-fork)
"""


_MISSING_MODULE_RE = __import__("re").compile(r"No module named '(numpy|mpmath|sympy|scipy|matplotlib)")


def agent_workdir(run_id, agent_id):
    """Opaque per-agent directory outside the run tree, so os.getcwd() and tracebacks reveal nothing."""
    return os.path.join(WORK_ROOT, hashlib.sha256("{}:{}:work".format(run_id, agent_id).encode()).hexdigest()[:16])


def _py_root():
    exe = os.path.realpath(sys.executable)
    d = os.path.dirname(exe)
    for _ in range(4):
        if os.path.isdir(os.path.join(d, "lib")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(os.path.dirname(exe))


def prewarm_matplotlib():
    """Build matplotlib's font cache once, outside the sandbox; each agent gets a private writable copy."""
    os.makedirs(MPL_CACHE, exist_ok=True)
    if not any(n.startswith("fontlist") for n in os.listdir(MPL_CACHE)):
        env = dict(os.environ, MPLCONFIGDIR=MPL_CACHE, MPLBACKEND="Agg")
        subprocess.run([sys.executable, "-c", "import matplotlib.pyplot"], env=env, capture_output=True, timeout=300)


def _limits():
    if platform.system() == "Linux":
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
        except Exception:
            pass


def default_mode():
    if platform.system() == "Darwin" and os.path.exists("/usr/bin/sandbox-exec"):
        return "seatbelt"
    if platform.system() == "Linux" and shutil.which("setpriv") and os.geteuid() == 0:
        return "setpriv"
    return "none"


def _cap(text, out_max):
    if len(text) <= out_max:
        return text
    marker = "\n...[output truncated]...\n"
    head = int((out_max - len(marker)) * 0.6)
    tail = out_max - len(marker) - head
    return text[:head] + marker + text[-tail:]


def _read_capped(path, cap=200000):
    try:
        with open(path, "rb") as f:
            return f.read(cap).decode("utf-8", "replace")
    except OSError:
        return ""


def run_python(code, workdir, timeout, out_max, mode, runs_root=None, tag="snippet"):
    """Return (output_text, tool_error, elapsed_ms). tool_error is None, 'timeout', 'sandbox', or 'import'.
    The code is fed on stdin (tracebacks say <stdin>); stdout/stderr go to files in workdir (no pipe can hang)."""
    workdir = os.path.realpath(workdir)
    os.makedirs(workdir, exist_ok=True)
    mpl_dir = os.path.join(workdir, ".mplconfig")
    if not os.path.isdir(mpl_dir) and os.path.isdir(MPL_CACHE):
        shutil.copytree(MPL_CACHE, mpl_dir)
    out_path, err_path = os.path.join(workdir, ".out"), os.path.join(workdir, ".err")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": workdir, "TMPDIR": workdir,
           "MPLBACKEND": "Agg", "MPLCONFIGDIR": mpl_dir, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2"}
    base = [sys.executable, "-I", "-B", "-"]
    if mode == "seatbelt":
        home = os.path.realpath(os.path.expanduser("~"))
        profile = SEATBELT_PROFILE.format(workdir=workdir, home=home, pyroot=_py_root(), mpl=os.path.realpath(MPL_CACHE),
                                          project=os.path.realpath(PROJECT_ROOT), work_root=os.path.realpath(WORK_ROOT),
                                          runs_root=os.path.realpath(runs_root) if runs_root else os.path.join(PROJECT_ROOT, "runs"))
        cmd = ["/usr/bin/sandbox-exec", "-p", profile] + base
    elif mode == "setpriv":
        os.chmod(workdir, 0o777)
        cmd = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups"] + base
    else:
        cmd = base
    t0 = time.monotonic()
    tool_error = None
    p = None
    try:
        with open(out_path, "wb") as fo, open(err_path, "wb") as fe:
            p = subprocess.Popen(cmd, cwd=workdir, env=env, stdin=subprocess.PIPE, stdout=fo, stderr=fe,
                                 start_new_session=True, preexec_fn=_limits)
            try:
                p.communicate(code.encode("utf-8"), timeout=timeout)
            except subprocess.TimeoutExpired:
                tool_error = "timeout"
    finally:
        if p is not None:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                p.wait(timeout=5)
            except Exception:
                pass
    ms = int((time.monotonic() - t0) * 1000)
    out, err = _read_capped(out_path), _read_capped(err_path)
    for pth in (out_path, err_path):
        try:
            os.remove(pth)
        except OSError:
            pass
    text = out + (("\n[stderr]\n" + err) if err.strip() else "")
    if tool_error == "timeout":
        text = (text.rstrip() + "\n[timeout after {} s]".format(timeout)).strip()
    elif err.startswith("sandbox-exec:") or err.startswith("[sandbox]") or err.startswith("setpriv:"):
        tool_error = "sandbox"
    elif _MISSING_MODULE_RE.search(err):
        tool_error = "import"      # the environment lacks a promised module (not a hallucinated symbol)
    if p is not None and p.returncode is not None and p.returncode < 0 and tool_error is None:
        hint = " Network access is not available in this environment." if any(k in code for k in ("socket", "urllib", "requests", "http", "ssl")) else ""
        text = (text.rstrip() + "\n[process terminated by signal {}].{}".format(-p.returncode, hint)).strip()
    elif p is not None and p.returncode not in (0, None) and not text.strip():
        text = "[exit code {}]".format(p.returncode)
    return _cap(text.strip() or "[no output]", out_max), tool_error, ms
