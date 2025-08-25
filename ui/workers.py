# base_worker.py (PyQt6)
from PyQt6.QtCore import QThread, pyqtSignal
import threading, sys, signal, subprocess, psutil

class BaseWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, task_func):
        super().__init__()
        self.task_func = task_func
        self._cancel = threading.Event()
        self._procs_lock = threading.Lock()
        self._procs: list[subprocess.Popen] = []

    def register_process(self, proc: subprocess.Popen):
        with self._procs_lock:
            self._procs.append(proc)

    def _clear_process(self, proc: subprocess.Popen):
        with self._procs_lock:
            try:
                self._procs.remove(proc)
            except ValueError:
                pass

    def stop(self):
        if self._cancel.is_set():
            return
        self._cancel.set()
        self.log.emit("🛑 Yêu cầu dừng — đang hạ sát tiến trình con...")

        with self._procs_lock:
            popens = list(self._procs)

        for p in popens:
            try:
                proc = psutil.Process(p.pid)

                # (A) cố gắng thoát êm nếu có stdin (ffmpeg)
                try:
                    if p.stdin and not p.stdin.closed:
                        try:
                            p.stdin.write("q\n")
                            p.stdin.flush()
                        except Exception:
                            pass
                except Exception:
                    pass

                # (B) gửi tín hiệu mềm
                if sys.platform.startswith("win"):
                    try:
                        # có thể không hiệu lực trong GUI, nên chỉ best-effort
                        p.send_signal(signal.CTRL_BREAK_EVENT)
                    except Exception:
                        pass

                # (C) terminate cả cây
                procs = [proc] + proc.children(recursive=True)
                for pr in procs:
                    try:
                        pr.terminate()
                    except Exception:
                        pass

                # (D) đợi rất ngắn, sau đó kill những ai còn sống
                try:
                    gone, alive = psutil.wait_procs(procs, timeout=1.0)
                    for pr in alive:
                        try:
                            pr.kill()
                        except Exception:
                            pass
                except Exception:
                    pass

                # (E) đóng pipe để tránh treo .wait()
                try:
                    if p.stdout and not p.stdout.closed:
                        p.stdout.close()
                except Exception:
                    pass
                try:
                    if p.stderr and not p.stderr.closed:
                        p.stderr.close()
                except Exception:
                    pass
                try:
                    if p.stdin and not p.stdin.closed:
                        p.stdin.close()
                except Exception:
                    pass

                self._clear_process(p)

            except psutil.NoSuchProcess:
                self._clear_process(p)
            except Exception as e:
                self.log.emit(f"⚠️ Lỗi khi dừng process {getattr(p,'pid', '?')}: {e}")

        self.log.emit("🧹 Đã dừng và dọn tiến trình con.")

    def is_stopped(self) -> bool:
        return self._cancel.is_set()

    def run(self):
        ok = False
        try:
            ok = self.task_func(self)
        except Exception as e:
            self.log.emit(f"❌ Lỗi: {e}")
            ok = False
        self.finished.emit(bool(ok and not self._cancel.is_set()))
