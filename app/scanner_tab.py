# -*- coding: utf-8 -*-
"""
链接扫描器标签页的UI和逻辑
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QHeaderView, QProgressBar, QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer
from .workers import ScannerWorker

class ScannerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner_worker = None
        self.progress_timer = QTimer(self)
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        # --- 布局定义 ---
        main_layout = QVBoxLayout(self)
        top_splitter = QHBoxLayout()
        
        # --- 配置区域 ---
        config_group = QGroupBox("扫描配置")
        config_layout = QGridLayout()
        
        self.prefix_label = QLabel("前缀:")
        self.prefix_input = QLineEdit("G")
        self.start_suffix_label = QLabel("起始后缀:")
        self.start_suffix_input = QLineEdit("KBEP6B")
        self.end_suffix_label = QLabel("结束后缀:")
        self.end_suffix_input = QLineEdit("ZZZZZZ")
        self.threads_label = QLabel("线程数:")
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(1, 1000)
        self.threads_spinbox.setValue(100)

        self.sleep_every_label = QLabel("每 N 个请求暂停:")
        self.sleep_every_spinbox = QSpinBox()
        self.sleep_every_spinbox.setRange(0, 10000)
        self.sleep_every_spinbox.setValue(100) # 默认每100个请求

        self.sleep_for_label = QLabel("暂停 M 秒:")
        self.sleep_for_spinbox = QSpinBox()
        self.sleep_for_spinbox.setRange(0, 60)
        self.sleep_for_spinbox.setValue(2) # 默认暂停2秒

        config_layout.addWidget(self.prefix_label, 0, 0)
        config_layout.addWidget(self.prefix_input, 0, 1)
        config_layout.addWidget(self.start_suffix_label, 1, 0)
        config_layout.addWidget(self.start_suffix_input, 1, 1)
        config_layout.addWidget(self.end_suffix_label, 2, 0)
        config_layout.addWidget(self.end_suffix_input, 2, 1)
        config_layout.addWidget(self.threads_label, 3, 0)
        config_layout.addWidget(self.threads_spinbox, 3, 1)
        config_layout.addWidget(self.sleep_every_label, 4, 0)
        config_layout.addWidget(self.sleep_every_spinbox, 4, 1)
        config_layout.addWidget(self.sleep_for_label, 5, 0)
        config_layout.addWidget(self.sleep_for_spinbox, 5, 1)
        config_group.setLayout(config_layout)
        
        # --- 控制与状态区域 ---
        control_status_group = QGroupBox("控制与状态")
        control_status_layout = QVBoxLayout()

        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("开始扫描")
        self.pause_button = QPushButton("暂停")
        self.stop_button = QPushButton("停止")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        
        # 状态显示
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("状态: 空闲")
        
        control_status_layout.addLayout(button_layout)
        control_status_layout.addWidget(self.progress_bar)
        control_status_layout.addWidget(self.status_label)
        control_status_group.setLayout(control_status_layout)

        top_splitter.addWidget(config_group, 1)
        top_splitter.addWidget(control_status_group, 1)

        # --- 结果显示区域 ---
        results_group = QGroupBox("扫描结果")
        results_layout = QHBoxLayout()
        
        # VIP链接
        vip_layout = QVBoxLayout()
        self.vip_table = self.create_results_table(["VIP链接"])
        self.send_vip_button = QPushButton("发送选中VIP链接到分析器")
        vip_layout.addWidget(self.vip_table)
        vip_layout.addWidget(self.send_vip_button)

        # 礼品链接
        gift_layout = QVBoxLayout()
        self.gift_table = self.create_results_table(["礼品链接"])
        self.send_gift_button = QPushButton("发送选中礼品链接到分析器")
        gift_layout.addWidget(self.gift_table)
        gift_layout.addWidget(self.send_gift_button)
        
        results_layout.addLayout(vip_layout, 1)
        results_layout.addLayout(gift_layout, 1)
        results_group.setLayout(results_layout)

        # --- 日志输出区域 ---
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)

        main_layout.addLayout(top_splitter)
        main_layout.addWidget(results_group, 3)
        main_layout.addWidget(log_group, 1)

    def create_results_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        return table

    def setup_connections(self):
        self.start_button.clicked.connect(self.start_scan)
        self.stop_button.clicked.connect(self.stop_scan)
        self.pause_button.clicked.connect(self.toggle_pause_scan)
        self.progress_timer.timeout.connect(self.update_progress)

    def start_scan(self):
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

        self.scanner_worker = ScannerWorker(
            prefix, start_suffix, end_suffix, max_workers,
            sleep_every, sleep_for
        )
        
        self.scanner_worker.log_message.connect(self.log_output.append)
        self.scanner_worker.result_found.connect(self.add_result_to_table)
        self.scanner_worker.finished.connect(self.scan_finished)
        
        self.scanner_worker.start()
        self.progress_timer.start(1000) # 每秒更新一次进度

    def stop_scan(self):
        if self.scanner_worker:
            self.scanner_worker.stop()
        self.progress_timer.stop()
        self.set_controls_state(is_running=False)
        self.status_label.setText("状态: 手动停止")

    def toggle_pause_scan(self):
        if not self.scanner_worker:
            return
        
        if self.pause_button.text() == "暂停":
            self.scanner_worker.pause()
            self.progress_timer.stop()
            self.pause_button.setText("恢复")
            self.status_label.setText("状态: 已暂停")
        else:
            self.scanner_worker.resume()
            self.progress_timer.start(1000)
            self.pause_button.setText("暂停")
            self.status_label.setText("状态: 正在扫描...")

    def scan_finished(self):
        self.progress_timer.stop()
        self.update_progress() # 最后更新一次，确保数据准确
        self.set_controls_state(is_running=False)
        self.status_label.setText("状态: 扫描完成")
        self.scanner_worker = None

    def add_result_to_table(self, link_type, url):
        table = self.vip_table if link_type == 'vip' else self.gift_table
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
        
        if not is_running:
            self.pause_button.setText("暂停")
            self.progress_bar.setValue(0)
    
    def get_selected_links(self, link_type):
        table = self.vip_table if link_type == 'vip' else self.gift_table
        selected_items = table.selectedItems()
        # 由于我们是整行选择，每列都有一个item，需要去重
        return list(set(item.text() for item in selected_items))

    def closeEvent(self, event):
        self.progress_timer.stop()
        if self.scanner_worker and self.scanner_worker.isRunning():
            self.stop_scan()
            self.scanner_worker.wait() # 等待线程完全退出
        event.accept() 