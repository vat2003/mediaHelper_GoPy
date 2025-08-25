import subprocess, sys

def spawn_process(worker, cmd, cwd=None, env=None, pipe_output=True, hide_console=True):
    """Spawn tiến trình và auto register để BaseWorker.stop() kill ngay."""
    creationflags = 0
    startupinfo = None

    if sys.platform.startswith("win"):
        creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
        if hide_console:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    stdout = subprocess.PIPE if pipe_output else None
    stderr = subprocess.STDOUT if pipe_output else None

    p = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE,      # để có thể gửi "q\n" nếu là ffmpeg
        stdout=stdout,
        stderr=stderr,
        text=True,
        bufsize=1,
        creationflags=creationflags,
        startupinfo=startupinfo,
        encoding="utf-8",
        errors="replace",
    )
    # rất quan trọng: đăng ký cho BaseWorker
    worker.register_process(p)
    return p

def stream_process(worker, p, *, prefix=None):
    """Đọc stdout realtime; auto thoát khi stop. Returncode hoặc None nếu đã stop sớm."""
    try:
        if p.stdout:
            for raw in p.stdout:
                if worker.is_stopped():
                    # cố gắng thoát êm (ffmpeg): gửi "q\\n"
                    try:
                        if p.stdin and not p.stdin.closed:
                            p.stdin.write("q\n"); p.stdin.flush()
                    except Exception:
                        pass
                    break

                line = (raw or "").rstrip()
                if not line:
                    continue
                if prefix:
                    worker.log.emit(f"{prefix}{line}")
                else:
                    worker.log.emit(line)
    finally:
        # đóng pipe để tránh treo
        try:
            if p.stdout and not p.stdout.closed: p.stdout.close()
        except Exception: pass
        try:
            if p.stderr and not p.stderr.closed: p.stderr.close()
        except Exception: pass
        try:
            if p.stdin and not p.stdin.closed: p.stdin.close()
        except Exception: pass

    # nếu đã stop, không chờ vô hạn
    if worker.is_stopped():
        try:
            return p.poll()
        finally:
            return None

    return p.wait()
