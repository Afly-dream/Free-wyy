from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QHeaderView, QAbstractItemView, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from .workers import AnalyzerWorker, FileOperationWorker
from .ui_effects import (ModernFrame, AnimatedButton, ModernTextEdit,
                        ModernTable, ModernProgressBar, ModernSpinBox, ModernLabel)

class AnalyzerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analyzer_worker = None
        self.file_worker = None
        self.current_results = []
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        toolbar_layout = QHBoxLayout()
        
        self.load_btn = AnimatedButton("📁 加载文件")
        self.analyze_btn = AnimatedButton("🚀 开始分析")
        self.pause_btn = AnimatedButton("⏸️ 暂停")
        self.stop_btn = AnimatedButton("⏹️ 停止")
        self.save_btn = AnimatedButton("💾 保存结果")
        self.clear_btn = AnimatedButton("🗑️ 清空")
        
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        self.thread_spinbox = ModernSpinBox()
        self.thread_spinbox.setRange(1, 20)
        self.thread_spinbox.setValue(5)
        
        toolbar_layout.addWidget(self.load_btn)
        toolbar_layout.addWidget(self.analyze_btn)
        toolbar_layout.addWidget(self.pause_btn)
        toolbar_layout.addWidget(self.stop_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(ModernLabel("线程数:"))
        toolbar_layout.addWidget(self.thread_spinbox)
        toolbar_layout.addWidget(self.save_btn)
        toolbar_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_frame = ModernFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)
        
        left_layout.addWidget(ModernLabel("📝 链接输入"))
        
        self.links_text = ModernTextEdit()
        self.links_text.setPlaceholderText("请输入链接，每行一个...")
        self.links_text.setMaximumHeight(200)
        left_layout.addWidget(self.links_text)
        
        self.links_count_label = ModernLabel("链接数量: 0")
        left_layout.addWidget(self.links_count_label)
        
        left_layout.addWidget(ModernLabel("📊 分析进度"))
        
        self.progress_bar = ModernProgressBar()
        self.progress_label = ModernLabel("就绪")
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.progress_label)
        
        left_layout.addWidget(ModernLabel("📈 统计信息"))
        
        self.stats_text = ModernTextEdit()
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setReadOnly(True)
        left_layout.addWidget(self.stats_text)
        
        splitter.addWidget(left_frame)
        
        right_frame = ModernFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)
        
        right_layout.addWidget(ModernLabel("🎁 分析结果"))
        
        filter_layout = QHBoxLayout()
        from PyQt6.QtWidgets import QCheckBox
        
        self.show_available_cb = QCheckBox("可领取")
        self.show_expired_cb = QCheckBox("已过期")
        self.show_claimed_cb = QCheckBox("已领取")
        self.show_error_cb = QCheckBox("错误")
        self.show_vip_valid_cb = QCheckBox("VIP有效")
        self.show_vip_expired_cb = QCheckBox("VIP过期")
        self.show_audio_valid_cb = QCheckBox("音质有效")
        self.show_audio_expired_cb = QCheckBox("音质过期")
        
        for cb in [self.show_available_cb, self.show_expired_cb, self.show_claimed_cb,
                   self.show_error_cb, self.show_vip_valid_cb, self.show_vip_expired_cb,
                   self.show_audio_valid_cb, self.show_audio_expired_cb]:
            cb.setChecked(True)
            cb.setStyleSheet("""
                QCheckBox {
                    color: #ffffff;
                    font-weight: bold;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid rgba(100, 120, 140, 180);
                    border-radius: 4px;
                    background: rgba(50, 60, 70, 200);
                }
                QCheckBox::indicator:checked {
                    background: rgba(0, 150, 255, 200);
                    border: 2px solid rgba(0, 150, 255, 255);
                }
            """)
        
        filter_layout.addWidget(ModernLabel("过滤:"))
        filter_layout.addWidget(self.show_available_cb)
        filter_layout.addWidget(self.show_expired_cb)
        filter_layout.addWidget(self.show_claimed_cb)
        filter_layout.addWidget(self.show_error_cb)
        filter_layout.addWidget(self.show_vip_valid_cb)
        filter_layout.addWidget(self.show_vip_expired_cb)
        filter_layout.addWidget(self.show_audio_valid_cb)
        filter_layout.addWidget(self.show_audio_expired_cb)
        filter_layout.addStretch()
        
        self.copy_results_btn = AnimatedButton("📋 复制结果")
        self.export_btn = AnimatedButton("📤 导出")
        filter_layout.addWidget(self.copy_results_btn)
        filter_layout.addWidget(self.export_btn)
        
        right_layout.addLayout(filter_layout)
        
        self.results_table = ModernTable()
        self.setup_results_table()
        right_layout.addWidget(self.results_table)
        
        splitter.addWidget(right_frame)
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)

    def setup_results_table(self):
        headers = ['状态', '链接', '类型', '发送者', '数量', '过期时间', '价值', '详情']
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSortingEnabled(True)

    def setup_connections(self):
        self.load_btn.clicked.connect(self.load_links_file)
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.pause_btn.clicked.connect(self.toggle_pause_analysis)
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.save_btn.clicked.connect(self.save_results)
        self.clear_btn.clicked.connect(self.clear_data)
        self.copy_results_btn.clicked.connect(self.copy_results)
        self.export_btn.clicked.connect(self.export_results)
        
        for cb in [self.show_available_cb, self.show_expired_cb, self.show_claimed_cb,
                   self.show_error_cb, self.show_vip_valid_cb, self.show_vip_expired_cb,
                   self.show_audio_valid_cb, self.show_audio_expired_cb]:
            cb.toggled.connect(self.update_table_filter)
        
        self.links_text.textChanged.connect(self.update_links_count)

    def update_links_count(self):
        text = self.links_text.toPlainText().strip()
        if text:
            links = [line.strip() for line in text.split('\n') if line.strip()]
            count = len(links)
        else:
            count = 0
        self.links_count_label.setText(f"链接数量: {count}")

    def load_links_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择链接文件", "", "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            if self.file_worker and self.file_worker.isRunning():
                QMessageBox.warning(self, "警告", "文件操作正在进行中...")
                return

            self.file_worker = FileOperationWorker('load', file_path)
            self.file_worker.operation_completed.connect(self.on_file_load_completed)
            self.file_worker.start()

    def on_file_load_completed(self, success, message, data):
        if success:
            self.links_text.setPlainText(data)
            self.update_links_count()
        else:
            QMessageBox.critical(self, "错误", message)

    def start_analysis(self):
        text = self.links_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要分析的链接！")
            return

        links = [line.strip() for line in text.split('\n') if line.strip()]
        if not links:
            QMessageBox.warning(self, "警告", "没有找到有效的链接！")
            return

        self.analyze_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

        self.current_results = []
        self.results_table.setRowCount(0)
        self.stats_text.clear()

        self.progress_bar.setMaximum(len(links))
        self.progress_bar.setValue(0)

        max_workers = self.thread_spinbox.value()
        self.analyzer_worker = AnalyzerWorker(links, max_workers)
        self.analyzer_worker.progress_updated.connect(self.update_progress)
        self.analyzer_worker.single_result_ready.connect(self.add_single_result)
        self.analyzer_worker.finished.connect(self.analysis_completed)
        self.analyzer_worker.start()

    def stop_analysis(self):
        if self.analyzer_worker and self.analyzer_worker.isRunning():
            self.analyzer_worker.stop()
            self.analyzer_worker.wait()

        self.analyze_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ 暂停")

    def toggle_pause_analysis(self):
        if not self.analyzer_worker or not self.analyzer_worker.isRunning():
            return

        if self.pause_btn.text() == "⏸️ 暂停":
            self.analyzer_worker.pause()
            self.pause_btn.setText("▶️ 继续")
        else:
            self.analyzer_worker.resume()
            self.pause_btn.setText("⏸️ 暂停")

    def update_progress(self, current, total, status):
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"进度: {current}/{total} - {status}")

    def add_single_result(self, result):
        from PyQt6.QtWidgets import QTableWidgetItem

        self.current_results.append(result)

        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        status = result.get('status_text', result.get('message', '未知'))
        link = result.get('short_url', '')
        gift_type = result.get('gift_type', '')
        sender = result.get('sender_name', result.get('sender', ''))
        count = result.get('gift_count', f"{result.get('available_count', 0)}/{result.get('total_count', 0)}")
        expire_date = result.get('expire_date', '')
        price = str(result.get('gift_price', 0))
        details = result.get('error_message', result.get('message', ''))

        items = [status, link, gift_type, sender, count, expire_date, price, details]
        for col, item in enumerate(items):
            self.results_table.setItem(row, col, QTableWidgetItem(str(item)))

        self.results_table.scrollToBottom()
        self.update_statistics()

    def analysis_completed(self):
        self.analyze_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("分析完成")

    def update_statistics(self):
        if not self.current_results:
            return

        total = len(self.current_results)
        available = len([r for r in self.current_results if r.get('gift_status') == 'available'])
        expired = len([r for r in self.current_results if r.get('gift_status') == 'expired'])
        claimed = len([r for r in self.current_results if r.get('gift_status') == 'claimed'])
        vip_valid = len([r for r in self.current_results if r.get('vip_status') == 'valid'])
        audio_valid = len([r for r in self.current_results if r.get('is_audio_link') and r.get('gift_status') == 'available'])
        audio_expired = len([r for r in self.current_results if r.get('is_audio_link') and r.get('gift_status') == 'expired'])
        errors = len([r for r in self.current_results if r.get('status') != 'success'])

        stats = f"""总数: {total}
可领取: {available}
已过期: {expired}
已领取: {claimed}
VIP有效: {vip_valid}
音质有效: {audio_valid}
音质过期: {audio_expired}
错误: {errors}"""

        self.stats_text.setPlainText(stats)

    def update_table_filter(self):
        pass

    def save_results(self):
        if not self.current_results:
            QMessageBox.information(self, "提示", "没有结果可保存")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "JSON文件 (*.json);;文本文件 (*.txt)"
        )

        if file_path:
            self.file_worker = FileOperationWorker('save', file_path, self.current_results)
            self.file_worker.operation_completed.connect(
                lambda s, m, d: QMessageBox.information(self, "成功" if s else "失败", m)
            )
            self.file_worker.start()

    def copy_results(self):
        from PyQt6.QtWidgets import QApplication, QMessageBox

        if not self.current_results:
            QMessageBox.information(self, "提示", "没有结果可复制")
            return

        links = [result.get('short_url', '') for result in self.current_results if result.get('short_url')]

        if links:
            clipboard_text = '\n'.join(links)
            QApplication.clipboard().setText(clipboard_text)
            QMessageBox.information(self, "复制成功", f"已复制 {len(links)} 个链接到剪贴板")
        else:
            QMessageBox.information(self, "提示", "没有有效链接可复制")

    def export_results(self):
        pass

    def clear_data(self):
        self.links_text.clear()
        self.results_table.setRowCount(0)
        self.stats_text.clear()
        self.current_results = []
        self.progress_bar.setValue(0)
        self.progress_label.setText("就绪")
