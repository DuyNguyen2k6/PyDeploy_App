import sys, os, subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QCheckBox, QLineEdit, QMessageBox, QListWidget,
    QSizePolicy, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class DropArea(QLabel):
    def __init__(self, parent=None):
        super().__init__("🗂️ Kéo thả file .py, .ico, .wav vào đây")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #888;
                border-radius: 14px;
                min-height: 70px;
                font-size: 18px;
                background: #f9f9f9;
                color: #666;
            }
            """)
        self.setAcceptDrops(True)
        self.parent = parent

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        files = [url.toLocalFile() for url in urls if url.isLocalFile()]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext == ".py":
                self.parent.py_path_edit.setText(file)
            elif ext == ".ico":
                self.parent.icon_path_edit.setText(file)
            elif ext == ".wav":
                if file not in self.parent.extra_files:
                    self.parent.extra_files.append(file)
                    self.parent.wav_files_list.addItem(file)
                    self.parent.wav_path_edit.setText(", ".join([os.path.basename(f) for f in self.parent.extra_files]))
            else:
                QMessageBox.warning(self, "Sai định dạng!", "Chỉ hỗ trợ .py, .ico, .wav")
        self.parent.update_command_preview()

class BuildThread(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, cmd, cwd):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd

    def run(self):
        try:
            process = subprocess.Popen(
                self.cmd,
                shell=True,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8"
            )
            while True:
                line = process.stdout.readline()
                if line:
                    self.log.emit(line.rstrip())
                if process.poll() is not None:
                    break
            # Read remaining output
            for line in process.stdout:
                self.log.emit(line.rstrip())
            if process.returncode == 0:
                self.finished.emit(True, "Đã đóng gói xong.")
            else:
                self.finished.emit(False, "Có lỗi khi đóng gói.")
        except Exception as e:
            self.finished.emit(False, str(e))

class ExeBuilder(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python → EXE Builder (Drag & Drop, Hiện log)")
        self.resize(730, 700)
        self.extra_files = []
        self.dist_folder = os.path.abspath("dist")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Ô kéo thả lớn
        self.drop_area = DropArea(self)
        layout.addWidget(self.drop_area)

        # Hàng 1: chọn file .py
        row_py = QHBoxLayout()
        self.py_path_edit = QLineEdit()
        self.py_path_edit.setPlaceholderText("Chọn file .py chính...")
        btn_py = QPushButton("Chọn file .py")
        btn_py.setMinimumWidth(140)
        btn_py.setMaximumWidth(140)
        row_py.addWidget(self.py_path_edit)
        row_py.addWidget(btn_py)
        layout.addLayout(row_py)

        # Hàng 2: chọn icon
        row_icon = QHBoxLayout()
        self.icon_path_edit = QLineEdit()
        self.icon_path_edit.setPlaceholderText("Chọn icon .ico (tùy chọn)...")
        btn_icon = QPushButton("Chọn icon")
        btn_icon.setMinimumWidth(140)
        btn_icon.setMaximumWidth(140)
        row_icon.addWidget(self.icon_path_edit)
        row_icon.addWidget(btn_icon)
        layout.addLayout(row_icon)

        # Hàng 3: thêm wav
        row_wav = QHBoxLayout()
        self.wav_path_edit = QLineEdit()
        self.wav_path_edit.setPlaceholderText("Thêm file WAV (có thể chọn nhiều lần)")
        btn_wav = QPushButton("Thêm file WAV")
        btn_wav.setMinimumWidth(140)
        btn_wav.setMaximumWidth(140)
        row_wav.addWidget(self.wav_path_edit)
        row_wav.addWidget(btn_wav)
        layout.addLayout(row_wav)

        # Nút kết nối
        btn_py.clicked.connect(self.select_py_file)
        btn_icon.clicked.connect(self.select_icon_file)
        btn_wav.clicked.connect(self.select_wav_files)

        # Danh sách file WAV đã chọn
        self.wav_files_list = QListWidget()
        self.wav_files_list.setMaximumHeight(60)
        layout.addWidget(self.wav_files_list)

        # --- Chọn thư mục lưu EXE ---
        row_dist = QHBoxLayout()
        self.dist_path_edit = QLineEdit(self.dist_folder)
        self.dist_path_edit.setPlaceholderText("Thư mục lưu file EXE (dist)")
        btn_dist = QPushButton("Chọn thư mục lưu")
        btn_open_dist = QPushButton("Mở thư mục EXE")
        btn_dist.setMinimumWidth(140)
        btn_open_dist.setMinimumWidth(140)
        row_dist.addWidget(self.dist_path_edit)
        row_dist.addWidget(btn_dist)
        row_dist.addWidget(btn_open_dist)
        layout.addLayout(row_dist)

        btn_dist.clicked.connect(self.select_dist_folder)
        btn_open_dist.clicked.connect(self.open_dist_folder)

        # Tuỳ chọn
        options_layout = QHBoxLayout()
        self.chk_onefile = QCheckBox("Đóng gói 1 file (--onefile)")
        self.chk_noconsole = QCheckBox("Ẩn console (--noconsole)")
        options_layout.addWidget(self.chk_onefile)
        options_layout.addWidget(self.chk_noconsole)
        layout.addLayout(options_layout)

        # Dòng lệnh tuỳ chỉnh
        self.command_preview = QLineEdit()
        self.command_preview.setReadOnly(False)
        layout.addWidget(QLabel("Lệnh sẽ chạy (bạn có thể sửa):"))
        layout.addWidget(self.command_preview)

        # Thanh tiến trình
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # 0 = chạy dạng "busy"
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Log build
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        layout.addWidget(QLabel("Log quá trình đóng gói:"))
        layout.addWidget(self.log_text)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Nút Build
        btn_build = QPushButton("Đóng gói")
        btn_build.clicked.connect(self.build_exe)
        layout.addWidget(btn_build)

        self.setLayout(layout)

        # Tự động cập nhật lệnh
        self.py_path_edit.textChanged.connect(self.update_command_preview)
        self.icon_path_edit.textChanged.connect(self.update_command_preview)
        self.dist_path_edit.textChanged.connect(self.update_command_preview)
        self.chk_onefile.stateChanged.connect(self.update_command_preview)
        self.chk_noconsole.stateChanged.connect(self.update_command_preview)

    def select_py_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Chọn file .py", "", "Python Files (*.py)")
        if file:
            self.py_path_edit.setText(file)
            self.update_command_preview()

    def select_icon_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Chọn icon", "", "Icon Files (*.ico)")
        if file:
            self.icon_path_edit.setText(file)
            self.update_command_preview()

    def select_wav_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn các file WAV", "", "WAV Files (*.wav)")
        for f in files:
            if f not in self.extra_files:
                self.extra_files.append(f)
                self.wav_files_list.addItem(f)
        self.wav_path_edit.setText(", ".join([os.path.basename(f) for f in self.extra_files]))
        self.update_command_preview()

    def select_dist_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu EXE")
        if folder:
            self.dist_path_edit.setText(folder)
            self.update_command_preview()

    def open_dist_folder(self):
        folder = self.dist_path_edit.text().strip()
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Lỗi", "Thư mục không tồn tại.")
            return
        os.startfile(folder)

    def update_command_preview(self):
        py = self.py_path_edit.text()
        ico = self.icon_path_edit.text()
        dist = self.dist_path_edit.text()
        options = []
        if self.chk_onefile.isChecked():
            options.append("--onefile")
        if self.chk_noconsole.isChecked():
            options.append("--noconsole")
        if ico:
            options.append(f"--icon=\"{ico}\"")
        if dist:
            options.append(f"--distpath \"{dist}\"")
        add_data = []
        for f in self.extra_files:
            add_data.append(f"--add-data \"{f};.\"")
        if py:
            cmd = f"pyinstaller {' '.join(options)} {' '.join(add_data)} \"{py}\""
            self.command_preview.setText(cmd)
        else:
            self.command_preview.setText("")

    def build_exe(self):
        py_file = self.py_path_edit.text()
        if not py_file or not os.path.exists(py_file):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file .py hợp lệ.")
            return
        cmd = self.command_preview.text()

        self.status_label.setText("Đang đóng gói...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.setEnabled(False)
        self.log_text.clear()

        self.thread = BuildThread(cmd, os.path.dirname(py_file))
        self.thread.log.connect(self.on_log)
        self.thread.finished.connect(self.on_build_finished)
        self.thread.start()

    def on_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def on_build_finished(self, success, msg):
        self.progress_bar.hide()
        self.setEnabled(True)
        if success:
            self.status_label.setText("Đã đóng gói xong.")
            self.log_text.append("\n=== Đã đóng gói xong ===")
            QMessageBox.information(self, "Hoàn tất", "Đã đóng gói xong.")
        else:
            self.status_label.setText("Lỗi đóng gói!")
            self.log_text.append("\n=== Lỗi đóng gói ===")
            QMessageBox.warning(self, "Lỗi", "Đóng gói thất bại.\nBạn xem log để biết chi tiết.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ExeBuilder()
    win.show()
    sys.exit(app.exec())
