from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QGroupBox, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import requests
from .workers import ScannerWorker
from .ui_effects import (ModernFrame, AnimatedButton, ModernLineEdit, ModernTextEdit,
                        ModernTable, ModernProgressBar, ModernSpinBox, ModernLabel, ResetButton)

class GitHubFetcher(QThread):
    content_fetched = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, field_type, url):
        super().__init__()
        self.field_type = field_type
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                content = response.text.strip()
                self.content_fetched.emit(self.field_type, content)
            else:
                self.error_occurred.emit(f"获取失败: HTTP {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"网络错误: {str(e)}")

class ScannerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner_worker = None
        self.progress_timer = QTimer(self)
        self.init_ui()
        self.setup_connections()
        self.set_controls_state(is_running=False)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        top_layout = QHBoxLayout()
        
        config_frame = ModernFrame()
        config_layout = QGridLayout(config_frame)
        config_layout.setContentsMargins(20, 20, 20, 20)
        config_layout.setSpacing(15)
        
        self.prefix_input = ModernLineEdit()
        self.prefix_input.setText("G")
        self.prefix_input.setPlaceholderText("前缀")

        self.start_suffix_input = ModernLineEdit()
        self.start_suffix_input.setText("KBEP6B")
        self.start_suffix_input.setPlaceholderText("起始后缀")

        self.end_suffix_input = ModernLineEdit()
        self.end_suffix_input.setText("ZZZZZZ")
        self.end_suffix_input.setPlaceholderText("结束后缀")

        self.prefix_reset_btn = ResetButton()
        self.start_suffix_reset_btn = ResetButton()
        
        self.threads_spinbox = ModernSpinBox()
        self.threads_spinbox.setRange(1, 1000)
        self.threads_spinbox.setValue(100)
        
        self.sleep_every_spinbox = ModernSpinBox()
        self.sleep_every_spinbox.setRange(0, 10000)
        self.sleep_every_spinbox.setValue(100)
        
        self.sleep_for_spinbox = ModernSpinBox()
        self.sleep_for_spinbox.setRange(0, 60)
        self.sleep_for_spinbox.setValue(2)
        
        config_layout.addWidget(ModernLabel("前缀:"), 0, 0)
        config_layout.addWidget(self.prefix_input, 0, 1)
        config_layout.addWidget(self.prefix_reset_btn, 0, 2)
        config_layout.addWidget(ModernLabel("起始后缀:"), 1, 0)
        config_layout.addWidget(self.start_suffix_input, 1, 1)
        config_layout.addWidget(self.start_suffix_reset_btn, 1, 2)
        config_layout.addWidget(ModernLabel("结束后缀:"), 2, 0)
        config_layout.addWidget(self.end_suffix_input, 2, 1)
        config_layout.addWidget(ModernLabel("线程数:"), 3, 0)
        config_layout.addWidget(self.threads_spinbox, 3, 1)
        config_layout.addWidget(ModernLabel("每N个请求暂停:"), 4, 0)
        config_layout.addWidget(self.sleep_every_spinbox, 4, 1)
        config_layout.addWidget(ModernLabel("暂停M秒:"), 5, 0)
        config_layout.addWidget(self.sleep_for_spinbox, 5, 1)
        
        control_frame = ModernFrame()
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(20, 20, 20, 20)
        control_layout.setSpacing(15)
        
        button_layout = QHBoxLayout()
        self.start_button = AnimatedButton("🚀 开始扫描")
        self.pause_button = AnimatedButton("⏸️ 暂停")
        self.stop_button = AnimatedButton("⏹️ 停止")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        
        self.progress_bar = ModernProgressBar()
        self.status_label = ModernLabel("状态: 空闲")
        
        control_layout.addLayout(button_layout)
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.status_label)
        
        top_layout.addWidget(config_frame, 1)
        top_layout.addWidget(control_frame, 1)
        
        results_frame = ModernFrame()
        results_layout = QHBoxLayout(results_frame)
        results_layout.setContentsMargins(20, 20, 20, 20)
        results_layout.setSpacing(20)
        
        vip_layout = QVBoxLayout()
        vip_header_layout = QHBoxLayout()
        vip_header_layout.addWidget(ModernLabel("🎯 VIP链接"))
        vip_header_layout.addStretch()
        self.copy_vip_btn = AnimatedButton("📋 复制")
        self.analyze_vip_btn = AnimatedButton("🔬 分析")
        vip_header_layout.addWidget(self.copy_vip_btn)
        vip_header_layout.addWidget(self.analyze_vip_btn)
        vip_layout.addLayout(vip_header_layout)
        self.vip_table = self.create_results_table(["VIP链接"])
        vip_layout.addWidget(self.vip_table)

        gift_layout = QVBoxLayout()
        gift_header_layout = QHBoxLayout()
        gift_header_layout.addWidget(ModernLabel("🎁 礼品链接"))
        gift_header_layout.addStretch()
        self.copy_gift_btn = AnimatedButton("📋 复制")
        self.analyze_gift_btn = AnimatedButton("🔬 分析")
        gift_header_layout.addWidget(self.copy_gift_btn)
        gift_header_layout.addWidget(self.analyze_gift_btn)
        gift_layout.addLayout(gift_header_layout)
        self.gift_table = self.create_results_table(["礼品链接"])
        gift_layout.addWidget(self.gift_table)

        audio_layout = QVBoxLayout()
        audio_header_layout = QHBoxLayout()
        audio_header_layout.addWidget(ModernLabel("🎵 音质链接"))
        audio_header_layout.addStretch()
        self.copy_audio_btn = AnimatedButton("📋 复制")
        self.analyze_audio_btn = AnimatedButton("🔬 分析")
        audio_header_layout.addWidget(self.copy_audio_btn)
        audio_header_layout.addWidget(self.analyze_audio_btn)
        audio_layout.addLayout(audio_header_layout)
        self.audio_table = self.create_results_table(["音质链接"])
        audio_layout.addWidget(self.audio_table)

        results_layout.addLayout(vip_layout, 1)
        results_layout.addLayout(gift_layout, 1)
        results_layout.addLayout(audio_layout, 1)
        
        log_frame = ModernFrame()
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(20, 20, 20, 20)
        log_layout.addWidget(ModernLabel("📋 日志输出"))
        
        self.log_output = ModernTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        log_layout.addWidget(self.log_output)
        
        main_layout.addLayout(top_layout)
        main_layout.addWidget(results_frame, 2)
        main_layout.addWidget(log_frame, 1)

    def create_results_table(self, headers):
        table = ModernTable()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        return table

    def setup_connections(self):
        self.start_button.clicked.connect(self.start_scan)
        self.stop_button.clicked.connect(self.stop_scan)
        self.pause_button.clicked.connect(self.toggle_pause_scan)
        self.progress_timer.timeout.connect(self.update_progress)

        self.copy_vip_btn.clicked.connect(lambda: self.copy_links('vip'))
        self.copy_gift_btn.clicked.connect(lambda: self.copy_links('gift'))
        self.copy_audio_btn.clicked.connect(lambda: self.copy_links('audio'))

        self.analyze_vip_btn.clicked.connect(lambda: self.send_to_analyzer('vip'))
        self.analyze_gift_btn.clicked.connect(lambda: self.send_to_analyzer('gift'))
        self.analyze_audio_btn.clicked.connect(lambda: self.send_to_analyzer('audio'))

        self.prefix_reset_btn.clicked.connect(self.reset_prefix)
        self.start_suffix_reset_btn.clicked.connect(self.reset_start_suffix)

    def start_scan(self):
        from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem

        prefix = self.prefix_input.text()
        start_suffix = self.start_suffix_input.text()
        end_suffix = self.end_suffix_input.text()
        max_workers = self.threads_spinbox.value()
        sleep_every = self.sleep_every_spinbox.value()
        sleep_for = self.sleep_for_spinbox.value()

        if not all([prefix, start_suffix, end_suffix]) or len(start_suffix) != 6 or len(end_suffix) != 6:
            QMessageBox.warning(self, "输入错误", "请确保前缀不为空，且起始/结束后缀均为6位字符。")
            return

        self.set_controls_state(is_running=True)
        self.log_output.clear()
        self.vip_table.setRowCount(0)
        self.gift_table.setRowCount(0)
        self.audio_table.setRowCount(0)

        self.scanner_worker = ScannerWorker(
            prefix, start_suffix, end_suffix, max_workers,
            sleep_every, sleep_for
        )

        self.scanner_worker.log_message.connect(self.log_output.append)
        self.scanner_worker.result_found.connect(self.add_result_to_table)
        self.scanner_worker.finished.connect(self.scan_finished)

        self.scanner_worker.start()
        self.progress_timer.start(1000)

    def stop_scan(self):
        if self.scanner_worker:
            self.scanner_worker.stop()
        self.progress_timer.stop()
        self.set_controls_state(is_running=False)
        self.status_label.setText("状态: 手动停止")

    def toggle_pause_scan(self):
        if not self.scanner_worker:
            return

        if self.pause_button.text() == "⏸️ 暂停":
            self.scanner_worker.pause()
            self.progress_timer.stop()
            self.pause_button.setText("▶️ 恢复")
            self.status_label.setText("状态: 已暂停")
        else:
            self.scanner_worker.resume()
            self.progress_timer.start(1000)
            self.pause_button.setText("⏸️ 暂停")
            self.status_label.setText("状态: 正在扫描...")

    def scan_finished(self):
        self.progress_timer.stop()
        self.update_progress()
        self.set_controls_state(is_running=False)
        self.status_label.setText("状态: 扫描完成")
        self.scanner_worker = None

    def add_result_to_table(self, link_type, url):
        from PyQt6.QtWidgets import QTableWidgetItem

        if link_type == 'vip':
            table = self.vip_table
        elif link_type == 'audio':
            table = self.audio_table
        else:
            table = self.gift_table

        row_position = table.rowCount()
        table.insertRow(row_position)
        table.setItem(row_position, 0, QTableWidgetItem(url))
        table.scrollToBottom()

    def update_progress(self):
        if not self.scanner_worker or not self.scanner_worker.isRunning():
            return

        checked = self.scanner_worker.checked_count
        found = self.scanner_worker.found_count
        speed = self.scanner_worker.get_speed()
        self.status_label.setText(f"状态: 已检查 {checked} / 已找到 {found} / 速度: {speed:.2f} 个/秒")

        total_range = self.scanner_worker.end_id - self.scanner_worker.start_id
        if total_range > 0:
            progress_value = int(((checked) / total_range) * 100)
            self.progress_bar.setValue(progress_value)

    def set_controls_state(self, is_running):
        self.start_button.setEnabled(not is_running)
        self.pause_button.setEnabled(is_running)
        self.stop_button.setEnabled(is_running)

        self.prefix_input.setDisabled(is_running)
        self.start_suffix_input.setDisabled(is_running)
        self.end_suffix_input.setDisabled(is_running)
        self.threads_spinbox.setDisabled(is_running)
        self.sleep_every_spinbox.setDisabled(is_running)
        self.sleep_for_spinbox.setDisabled(is_running)

        self.prefix_reset_btn.setDisabled(is_running)
        self.start_suffix_reset_btn.setDisabled(is_running)

        if not is_running:
            self.pause_button.setText("⏸️ 暂停")
            self.progress_bar.setValue(0)

    def copy_links(self, link_type):
        from PyQt6.QtWidgets import QApplication, QMessageBox

        if link_type == 'vip':
            table = self.vip_table
        elif link_type == 'audio':
            table = self.audio_table
        else:
            table = self.gift_table

        links = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                links.append(item.text())

        if links:
            clipboard_text = '\n'.join(links)
            QApplication.clipboard().setText(clipboard_text)
            type_names = {'vip': 'VIP', 'audio': '音质', 'gift': '礼品'}
            QMessageBox.information(self, "复制成功", f"已复制 {len(links)} 个{type_names[link_type]}链接到剪贴板")
        else:
            type_names = {'vip': 'VIP', 'audio': '音质', 'gift': '礼品'}
            QMessageBox.information(self, "提示", f"没有{type_names[link_type]}链接可复制")

    def send_to_analyzer(self, link_type):
        from PyQt6.QtWidgets import QMessageBox

        if link_type == 'vip':
            table = self.vip_table
        elif link_type == 'audio':
            table = self.audio_table
        else:
            table = self.gift_table

        links = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                links.append(item.text())

        if links:
            main_window = None
            widget = self
            while widget is not None:
                if hasattr(widget, 'tabs') and hasattr(widget, 'analyzer_tab'):
                    main_window = widget
                    break
                widget = widget.parent()

            if main_window:
                analyzer_tab = main_window.analyzer_tab
                current_text = analyzer_tab.links_text.toPlainText()
                if current_text:
                    new_text = current_text + '\n' + '\n'.join(links)
                else:
                    new_text = '\n'.join(links)
                analyzer_tab.links_text.setPlainText(new_text)
                analyzer_tab.update_links_count()
                main_window.tabs.setCurrentWidget(analyzer_tab)

                type_names = {'vip': 'VIP', 'audio': '音质', 'gift': '礼品'}
                QMessageBox.information(self, "转移成功", f"已将 {len(links)} 个{type_names[link_type]}链接发送到分析器")
            else:
                QMessageBox.warning(self, "错误", "无法找到分析器标签页")
        else:
            type_names = {'vip': 'VIP', 'audio': '音质', 'gift': '礼品'}
            QMessageBox.information(self, "提示", f"没有{type_names[link_type]}链接可发送")

    def reset_prefix(self):
        from PyQt6.QtWidgets import QMessageBox

        self.prefix_reset_btn.setEnabled(False)
        self.prefix_reset_btn.setText("⏳")

        self.github_fetcher = GitHubFetcher(
            'prefix',
            'https://raw.githubusercontent.com/Afly-dream/Free-wyy/main/checknewidforfree/newfirst'
        )
        self.github_fetcher.content_fetched.connect(self.on_content_fetched)
        self.github_fetcher.error_occurred.connect(self.on_fetch_error)
        self.github_fetcher.start()

    def reset_start_suffix(self):
        from PyQt6.QtWidgets import QMessageBox

        self.start_suffix_reset_btn.setEnabled(False)
        self.start_suffix_reset_btn.setText("⏳")

        self.github_fetcher = GitHubFetcher(
            'start_suffix',
            'https://raw.githubusercontent.com/Afly-dream/Free-wyy/main/checknewidforfree/newnext'
        )
        self.github_fetcher.content_fetched.connect(self.on_content_fetched)
        self.github_fetcher.error_occurred.connect(self.on_fetch_error)
        self.github_fetcher.start()

    def on_content_fetched(self, field_type, content):
        from PyQt6.QtWidgets import QMessageBox

        if field_type == 'prefix':
            self.prefix_input.setText(content)
            self.prefix_reset_btn.setEnabled(True)
            self.prefix_reset_btn.setText("🔄")
            QMessageBox.information(self, "成功", f"前缀已重置为: {content}")
        elif field_type == 'start_suffix':
            self.start_suffix_input.setText(content)
            self.start_suffix_reset_btn.setEnabled(True)
            self.start_suffix_reset_btn.setText("🔄")
            QMessageBox.information(self, "成功", f"起始后缀已重置为: {content}")

    def on_fetch_error(self, error_message):
        from PyQt6.QtWidgets import QMessageBox

        self.prefix_reset_btn.setEnabled(True)
        self.prefix_reset_btn.setText("🔄")
        self.start_suffix_reset_btn.setEnabled(True)
        self.start_suffix_reset_btn.setText("🔄")

        QMessageBox.warning(self, "错误", f"获取默认值失败: {error_message}")

    def closeEvent(self, event):
        self.progress_timer.stop()
        if self.scanner_worker and self.scanner_worker.isRunning():
            self.stop_scan()
            self.scanner_worker.wait()
        event.accept()
