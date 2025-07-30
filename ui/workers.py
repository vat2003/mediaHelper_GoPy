from PyQt6.QtCore import QThread, pyqtSignal


class BaseWorker(QThread):
    progress = pyqtSignal(int)      # Gửi % tiến độ
    log = pyqtSignal(str)           # Gửi log chi tiết
    finished = pyqtSignal(bool)     # Gửi trạng thái hoàn tất

    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func  # Hàm xử lý chính
        self.args = args
        self.kwargs = kwargs
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def is_stopped(self):
        return self._is_stopped

    def run(self):
        try:
            result = self.task_func(self)  # self chính là worker, truyền vào hàm
            self.finished.emit(result)
        except Exception as e:
            self.log.emit(f"❌ Lỗi: {str(e)}")
            self.finished.emit(False)
