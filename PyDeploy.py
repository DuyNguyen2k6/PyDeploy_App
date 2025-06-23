import sys
import os
import ast
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit,
    QCheckBox, QFileDialog, QHBoxLayout, QVBoxLayout, QMessageBox,
    QListWidget, QProgressBar, QDialog, QScrollArea, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon  # <--- import QIcon
from PyQt6.QtWidgets import QDialog

def get_imported_modules(pyfile):
    modules = set()
    try:
        with open(pyfile, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), pyfile)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    modules.add(n.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.add(node.module.split('.')[0])
    except Exception:
        pass
    return sorted(modules)

class BuildThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, cmd, cwd):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd

    def run(self):
        try:
            process = subprocess.Popen(
                self.cmd, shell=True, cwd=self.cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, encoding='utf-8'
            )
            for line in process.stdout:
                self.log_signal.emit(line.rstrip())
            process.wait()
            if process.returncode == 0:
                self.finished_signal.emit(True, "Build completed successfully.")
            else:
                self.finished_signal.emit(False, "Build error. Check logs for details.")
        except Exception as e:
            self.finished_signal.emit(False, f"Error: {e}")

class CollectModulesDialog(QDialog):
    def __init__(self, modules, selected_modules):
        super().__init__()
        self.setWindowTitle("Select modules for --collect-all")
        self.resize(350, 400)
        self.modules = modules
        self.selected_modules = set(selected_modules)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        vbox = QVBoxLayout()

        self.checkboxes = []
        for mod in self.modules:
            cb = QCheckBox(mod)
            if mod in self.selected_modules:
                cb.setChecked(True)
            vbox.addWidget(cb)
            self.checkboxes.append(cb)

        container.setLayout(vbox)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        self.setLayout(layout)

    def get_selected_modules(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

class DropArea(QLabel):
    def __init__(self, parent=None):
        super().__init__("🗂️ Drag and drop .py, .ico, and extra files here")
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
            if ext == '.py':
                self.parent.py_path_edit.setText(file)
            elif ext == '.ico':
                self.parent.icon_path_edit.setText(file)
                self.parent.setWindowIcon(QIcon(file))  # Cập nhật icon khi thả file .ico
            else:
                if file not in self.parent.extra_files:
                    self.parent.extra_files.append(file)
                    self.parent.extra_files_list.addItem(file)
                    self.parent.update_extra_files_entry()
        self.parent.update_command_preview()

class PyInstallerBuilder(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyInstaller Builder by Minh Duy")
        self.resize(750, 730)
        self.extra_files = []
        self.dist_folder = os.path.abspath("dist")
        self.selected_modules = []
        self.available_modules = []

        # Đặt icon mặc định lúc khởi động (nếu có file này)
        default_icon_path = "app_icon.ico"
        if os.path.isfile(default_icon_path):
            self.setWindowIcon(QIcon(default_icon_path))

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        self.drop_area = DropArea(self)
        layout.addWidget(self.drop_area)

        row_py = QHBoxLayout()
        self.py_path_edit = QLineEdit()
        self.py_path_edit.setPlaceholderText("Select main .py file...")
        btn_py = QPushButton("Select .py file")
        btn_py.setMinimumWidth(140)
        btn_py.setMaximumWidth(140)
        row_py.addWidget(self.py_path_edit)
        row_py.addWidget(btn_py)
        layout.addLayout(row_py)

        row_icon = QHBoxLayout()
        self.icon_path_edit = QLineEdit()
        self.icon_path_edit.setPlaceholderText("Select icon (.ico) (optional)...")
        btn_icon = QPushButton("Select icon")
        btn_icon.setMinimumWidth(140)
        btn_icon.setMaximumWidth(140)
        row_icon.addWidget(self.icon_path_edit)
        row_icon.addWidget(btn_icon)
        layout.addLayout(row_icon)

        row_extra = QHBoxLayout()
        self.extra_files_edit = QLineEdit()
        self.extra_files_edit.setPlaceholderText("Selected extra files")
        self.extra_files_edit.setReadOnly(True)
        btn_add_files = QPushButton("Add extra files")
        btn_add_files.setMinimumWidth(140)
        btn_add_files.setMaximumWidth(140)
        row_extra.addWidget(self.extra_files_edit)
        row_extra.addWidget(btn_add_files)
        layout.addLayout(row_extra)

        self.extra_files_list = QListWidget()
        self.extra_files_list.setMaximumHeight(80)
        layout.addWidget(self.extra_files_list)

        row_dist = QHBoxLayout()
        self.dist_path_edit = QLineEdit(self.dist_folder)
        self.dist_path_edit.setPlaceholderText("Folder to save EXE (dist)...")
        btn_dist = QPushButton("Select output folder")
        btn_open_dist = QPushButton("Open EXE folder")
        btn_dist.setMinimumWidth(140)
        btn_open_dist.setMinimumWidth(140)
        row_dist.addWidget(self.dist_path_edit)
        row_dist.addWidget(btn_dist)
        row_dist.addWidget(btn_open_dist)
        layout.addLayout(row_dist)

        options_layout = QHBoxLayout()
        self.chk_onefile = QCheckBox("One file bundle (--onefile)")
        self.chk_noconsole = QCheckBox("Hide console (--noconsole)")
        self.chk_collectall = QCheckBox("Collect module (--collect-all)")
        options_layout.addWidget(self.chk_onefile)
        options_layout.addWidget(self.chk_noconsole)
        options_layout.addWidget(self.chk_collectall)
        layout.addLayout(options_layout)

        layout.addWidget(QLabel("Command to run (editable):"))
        self.command_preview = QLineEdit()
        layout.addWidget(self.command_preview)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        layout.addWidget(QLabel("Build log:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        layout.addWidget(self.log_text)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.btn_build = QPushButton("Build")
        layout.addWidget(self.btn_build)

        self.setLayout(layout)

        # Connect events
        btn_py.clicked.connect(self.select_py_file)
        btn_icon.clicked.connect(self.select_icon_file)
        btn_add_files.clicked.connect(self.add_extra_files)
        btn_dist.clicked.connect(self.select_dist_folder)
        btn_open_dist.clicked.connect(self.open_dist_folder)

        self.chk_onefile.stateChanged.connect(self.update_command_preview)
        self.chk_noconsole.stateChanged.connect(self.update_command_preview)
        self.chk_collectall.stateChanged.connect(self.on_collectall_toggled)

        self.py_path_edit.textChanged.connect(self.update_command_preview)
        self.icon_path_edit.textChanged.connect(self.on_icon_path_changed)
        self.dist_path_edit.textChanged.connect(self.update_command_preview)
        self.btn_build.clicked.connect(self.build_exe)

    def select_py_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select .py file", "", "Python Files (*.py)")
        if file:
            self.py_path_edit.setText(file)

    def select_icon_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select icon (.ico)", "", "Icon Files (*.ico)")
        if file:
            self.icon_path_edit.setText(file)
            self.setWindowIcon(QIcon(file))  # Cập nhật icon cửa sổ ngay khi chọn file

    def on_icon_path_changed(self):
        icon_path = self.icon_path_edit.text()
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def add_extra_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select extra files")
        if files:
            for f in files:
                if f not in self.extra_files:
                    self.extra_files.append(f)
                    self.extra_files_list.addItem(f)
            self.update_extra_files_entry()

    def update_extra_files_entry(self):
        self.extra_files_edit.setText(", ".join(os.path.basename(f) for f in self.extra_files))
        self.update_command_preview()

    def select_dist_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select output folder for EXE")
        if folder:
            self.dist_path_edit.setText(folder)

    def open_dist_folder(self):
        folder = self.dist_path_edit.text()
        if os.path.isdir(folder):
            os.startfile(folder)
        else:
            QMessageBox.warning(self, "Error", "Folder does not exist.")

    def on_collectall_toggled(self, state):
        if self.chk_collectall.isChecked():
            pyfile = self.py_path_edit.text()
            if not os.path.isfile(pyfile):
                QMessageBox.warning(self, "Error", "Please select a valid .py file before selecting modules!")
                self.chk_collectall.setChecked(False)
                return
            self.available_modules = get_imported_modules(pyfile)
            dlg = CollectModulesDialog(self.available_modules, self.selected_modules)
            ret = dlg.exec()
            if ret == QDialog.DialogCode.Accepted:
                self.selected_modules = dlg.get_selected_modules()
            else:
                self.chk_collectall.setChecked(False)
                self.selected_modules = []
            self.update_command_preview()
        else:
            self.selected_modules = []
            self.update_command_preview()

    def update_command_preview(self):
        py = self.py_path_edit.text()
        ico = self.icon_path_edit.text()
        dist = self.dist_path_edit.text()
        options = []
        if self.chk_onefile.isChecked():
            options.append("--onefile")
        if self.chk_noconsole.isChecked():
            options.append("--noconsole")
        if self.chk_collectall.isChecked():
            for mod in self.selected_modules:
                options.append(f"--collect-all {mod}")
        if ico:
            options.append(f'--icon="{ico}"')
        if dist:
            options.append(f'--distpath "{dist}"')
        add_data = []
        for f in self.extra_files:
            add_data.append(f'--add-data "{f};."')
        cmd = ''
        if py:
            cmd = f'pyinstaller {" ".join(options)} {" ".join(add_data)} "{py}"'
        self.command_preview.setText(cmd)

    def build_exe(self):
        py_file = self.py_path_edit.text()
        if not py_file or not os.path.isfile(py_file):
            QMessageBox.warning(self, "Error", "Please select a valid .py file.")
            return
        cmd = self.command_preview.text()

        self.status_label.setText("Building...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.setEnabled(False)
        self.log_text.clear()

        self.thread = BuildThread(cmd, os.path.dirname(py_file))
        self.thread.log_signal.connect(self.append_log)
        self.thread.finished_signal.connect(self.on_build_finished)
        self.thread.start()

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def on_build_finished(self, success, msg):
        self.progress_bar.hide()
        self.setEnabled(True)
        if success:
            self.status_label.setText("Build completed.")
            self.log_text.append("\n=== Build completed ===")
            QMessageBox.information(self, "Notification", msg)
        else:
            self.status_label.setText("Build error!")
            self.log_text.append("\n=== Build error ===")
            QMessageBox.warning(self, "Error", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PyInstallerBuilder()
    window.show()
    sys.exit(app.exec())
