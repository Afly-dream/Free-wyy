# -*- coding: utf-8 -*-
"""
链接分析器标签页的UI和逻辑, 整合了礼品卡和VIP链接分析
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QGroupBox, QSpinBox, QCheckBox, QSplitter,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from .workers import AnalyzerWorker, VipCheckWorker, FileOperationThread, to_beijing_time

class AnalyzerTab(QWidget):
    request_send_links_to_analyzer = pyqtSignal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.analyzer_worker = None
        self.vip_checker_worker = None
        self.file_worker = None
        
        self.gift_results_data = []
        self.vip_results_data = []

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 输入区域 ---
        input_group = QGroupBox("链接输入")
        input_layout = QHBoxLayout()
        self.links_input = QTextEdit()
        self.links_input.setPlaceholderText("在此处粘贴链接，每行一个...")
        
        input_controls_layout = QVBoxLayout()
        self.load_links_button = QPushButton("从文件加载")
        self.clear_links_button = QPushButton("清空输入")
        self.links_count_label = QLabel("链接数量: 0")
        input_controls_layout.addWidget(self.load_links_button)
        input_controls_layout.addWidget(self.clear_links_button)
        input_controls_layout.addWidget(self.links_count_label)
        input_controls_layout.addStretch()

        input_layout.addWidget(self.links_input, 4)
        input_layout.addLayout(input_controls_layout, 1)
        input_group.setLayout(input_layout)

        # --- 控制区域 ---
        control_group = QGroupBox("分析控制")
        control_layout = QHBoxLayout()
        self.threads_label = QLabel("分析线程数:")
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(1, 100)
        self.threads_spinbox.setValue(10)
        self.start_analysis_button = QPushButton("开始分析")
        self.stop_analysis_button = QPushButton("停止分析")
        self.stop_analysis_button.setEnabled(False)
        
        control_layout.addWidget(self.threads_label)
        control_layout.addWidget(self.threads_spinbox)
        control_layout.addStretch()
        control_layout.addWidget(self.start_analysis_button)
        control_layout.addWidget(self.stop_analysis_button)
        control_group.setLayout(control_layout)

        # --- 筛选与导出 ---
        filter_group = QGroupBox("筛选与导出")
        filter_layout = QHBoxLayout()
        self.filter_available_check = QCheckBox("可用")
        self.filter_available_check.setChecked(True)
        self.filter_claimed_check = QCheckBox("已领完")
        self.filter_claimed_check.setChecked(True)
        self.filter_expired_check = QCheckBox("已过期")
        self.filter_expired_check.setChecked(True)
        self.filter_invalid_check = QCheckBox("无效/错误")
        self.filter_invalid_check.setChecked(True)
        
        self.export_selected_button = QPushButton("导出选中")
        self.export_all_button = QPushButton("导出全部(可见)")

        filter_layout.addWidget(QLabel("筛选:"))
        filter_layout.addWidget(self.filter_available_check)
        filter_layout.addWidget(self.filter_claimed_check)
        filter_layout.addWidget(self.filter_expired_check)
        filter_layout.addWidget(self.filter_invalid_check)
        filter_layout.addStretch()
        filter_layout.addWidget(self.export_selected_button)
        filter_layout.addWidget(self.export_all_button)
        filter_group.setLayout(filter_layout)

        # --- 结果显示区域 (使用QSplitter) ---
        results_splitter = QSplitter(Qt.Orientation.Vertical)

        # 礼品卡分析结果
        gift_group = QGroupBox("礼品卡分析结果")
        gift_layout = QVBoxLayout()
        self.gift_progress = QProgressBar()
        self.gift_status = QLabel("状态: 空闲")
        self.gift_table = self.create_gift_table()
        gift_layout.addWidget(self.gift_progress)
        gift_layout.addWidget(self.gift_status)
        gift_layout.addWidget(self.gift_table)
        gift_group.setLayout(gift_layout)
        
        # VIP链接分析结果
        vip_group = QGroupBox("VIP链接分析结果")
        vip_layout = QVBoxLayout()
        self.vip_progress = QProgressBar()
        self.vip_status = QLabel("状态: 空闲")
        self.vip_table = self.create_vip_table()
        vip_layout.addWidget(self.vip_progress)
        vip_layout.addWidget(self.vip_status)
        vip_layout.addWidget(self.vip_table)
        vip_group.setLayout(vip_layout)

        results_splitter.addWidget(gift_group)
        results_splitter.addWidget(vip_group)
        results_splitter.setSizes([200, 200])

        main_layout.addWidget(input_group)
        main_layout.addWidget(control_group)
        main_layout.addWidget(filter_group)
        main_layout.addWidget(results_splitter, 1)

    def create_gift_table(self):
        headers = ["短链接", "状态", "类型", "价值", "总数/已领", "赠送者", "过期时间"]
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        return table

    def create_vip_table(self):
        headers = ["短链接", "状态", "是否有效", "过期时间"]
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        return table

    def setup_connections(self):
        self.load_links_button.clicked.connect(self.load_links_from_file)
        self.clear_links_button.clicked.connect(self.links_input.clear)
        self.links_input.textChanged.connect(self.update_links_count)
        self.start_analysis_button.clicked.connect(self.start_analysis)
        self.stop_analysis_button.clicked.connect(self.stop_analysis)
        
        # 筛选功能连接
        self.filter_available_check.stateChanged.connect(self.apply_gift_table_filter)
        self.filter_claimed_check.stateChanged.connect(self.apply_gift_table_filter)
        self.filter_expired_check.stateChanged.connect(self.apply_gift_table_filter)
        self.filter_invalid_check.stateChanged.connect(self.apply_gift_table_filter)
        
        # 导出功能连接
        self.export_selected_button.clicked.connect(lambda: self.export_links(selected_only=True))
        self.export_all_button.clicked.connect(lambda: self.export_links(selected_only=False))
        
    def add_links_to_input(self, link_type, links):
        """供外部调用的槽，用于接收来自扫描器的链接"""
        if not links:
            return
        
        current_text = self.links_input.toPlainText()
        new_text = '\n'.join(links)
        
        if current_text:
            self.links_input.setPlainText(current_text + '\n' + new_text)
        else:
            self.links_input.setPlainText(new_text)
            
        QMessageBox.information(self, "链接已添加", f"{len(links)}个{link_type}链接已添加到输入框。")
    
    def update_links_count(self):
        links = self.get_links_from_input()
        self.links_count_label.setText(f"链接数量: {len(links)}")

    def get_links_from_input(self):
        return [line.strip() for line in self.links_input.toPlainText().split('\n') if line.strip()]

    def load_links_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "加载链接文件", "", "文本文件 (*.txt);;所有文件 (*.*)")
        if file_path:
            self.file_worker = FileOperationThread('load_text', file_path)
            self.file_worker.operation_completed.connect(self.on_file_load_completed)
            self.file_worker.start()

    def on_file_load_completed(self, success, message, data):
        if success:
            self.links_input.setPlainText(data)
            self.update_links_count()
        else:
            QMessageBox.critical(self, "错误", message)

    def start_analysis(self):
        links = self.get_links_from_input()
        if not links:
            QMessageBox.warning(self, "没有链接", "请输入或加载需要分析的链接。")
            return

        self.set_controls_state(is_running=True)
        self.gift_table.setRowCount(0)
        self.vip_table.setRowCount(0)
        self.gift_results_data.clear()
        self.vip_results_data.clear()

        gift_links = [link for link in links if 'gift' in link or '163cn.tv' in link] # 宽泛匹配
        vip_links = [link for link in links if 'vip-invite-cashier' in link]

        if gift_links:
            self.analyzer_worker = AnalyzerWorker(gift_links, self.threads_spinbox.value())
            self.analyzer_worker.progress_updated.connect(lambda cur, tot: self.update_progress('gift', cur, tot))
            self.analyzer_worker.single_result_ready.connect(self.add_gift_result)
            self.analyzer_worker.finished.connect(lambda: self.on_task_finished('gift'))
            self.analyzer_worker.start()
        
        if vip_links:
            self.vip_checker_worker = VipCheckWorker(vip_links, self.threads_spinbox.value())
            self.vip_checker_worker.progress_updated.connect(lambda cur, tot: self.update_progress('vip', cur, tot))
            self.vip_checker_worker.single_result_ready.connect(self.add_vip_result)
            self.vip_checker_worker.finished.connect(lambda: self.on_task_finished('vip'))
            self.vip_checker_worker.start()

    def stop_analysis(self):
        if self.analyzer_worker:
            self.analyzer_worker.stop()
        if self.vip_checker_worker:
            self.vip_checker_worker.stop()
        self.set_controls_state(is_running=False)

    def on_task_finished(self, task_type):
        if task_type == 'gift':
            self.gift_status.setText("状态: 礼品卡分析完成")
            self.analyzer_worker = None
        elif task_type == 'vip':
            self.vip_status.setText("状态: VIP链接检查完成")
            self.vip_checker_worker = None
            
        if not self.analyzer_worker and not self.vip_checker_worker:
            self.set_controls_state(is_running=False)

    def update_progress(self, task_type, current, total):
        if task_type == 'gift':
            self.gift_progress.setValue(int((current / total) * 100))
            self.gift_status.setText(f"状态: 正在分析礼品卡... ({current}/{total})")
        elif task_type == 'vip':
            self.vip_progress.setValue(int((current / total) * 100))
            self.vip_status.setText(f"状态: 正在检查VIP链接... ({current}/{total})")

    def add_gift_result(self, result):
        if result.get("status") == "not_gift":
            if "vip-invite-cashier" in result.get("redirect_url", ""):
                vip_placeholder_result = {
                    'status': 'not_checked', 
                    'short_url': result['short_url'], 
                    'status_text': '待检查 (来自礼品卡分析)', 
                    'is_valid': False, 
                    'expire_date': 'N/A'
                }
                self.add_vip_result(vip_placeholder_result)
            return

        row = self.gift_table.rowCount()
        self.gift_results_data.append(result)
        self.gift_table.insertRow(row)
        
        self.populate_gift_table_row(row, result)
        self.apply_gift_table_filter()
        self.gift_table.scrollToBottom()

    def populate_gift_table_row(self, row, result):
        self.gift_table.setItem(row, 0, QTableWidgetItem(result.get('short_url', '')))
        self.gift_table.setItem(row, 1, QTableWidgetItem(result.get('status_text', result.get('message', ''))))
        self.gift_table.setItem(row, 2, QTableWidgetItem(result.get('gift_type', 'N/A')))
        self.gift_table.setItem(row, 3, QTableWidgetItem(str(result.get('gift_price', 0))))
        self.gift_table.setItem(row, 4, QTableWidgetItem(f"{result.get('available_count', 'N/A')} / {result.get('total_count', 'N/A')}"))
        self.gift_table.setItem(row, 5, QTableWidgetItem(result.get('sender_name', 'N/A')))
        self.gift_table.setItem(row, 6, QTableWidgetItem(result.get('expire_date', 'N/A')))
        self.gift_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, len(self.gift_results_data) - 1)

    def add_vip_result(self, result):
        self.vip_results_data.append(result)
        row = self.vip_table.rowCount()
        self.vip_table.insertRow(row)
        self.vip_table.setItem(row, 0, QTableWidgetItem(result.get('short_url', '')))
        self.vip_table.setItem(row, 1, QTableWidgetItem(result.get('status_text', result.get('message', ''))))
        self.vip_table.setItem(row, 2, QTableWidgetItem("是" if result.get('is_valid') else "否"))
        self.vip_table.setItem(row, 3, QTableWidgetItem(result.get('expire_date', 'N/A')))
        self.vip_table.scrollToBottom()

    def apply_gift_table_filter(self):
        """根据复选框状态显示/隐藏礼品卡表的行"""
        filters = {
            'available': self.filter_available_check.isChecked(),
            'claimed': self.filter_claimed_check.isChecked(),
            'expired': self.filter_expired_check.isChecked(),
            'invalid': self.filter_invalid_check.isChecked()
        }

        for row in range(self.gift_table.rowCount()):
            item = self.gift_table.item(row, 0)
            if not item: continue
            
            data_index = item.data(Qt.ItemDataRole.UserRole)
            result_data = self.gift_results_data[data_index]
            
            status = result_data.get('gift_status') # available, claimed, expired
            if result_data.get('status') != 'success':
                status = 'invalid' # Group all other statuses as invalid

            if filters.get(status, False):
                self.gift_table.setRowHidden(row, False)
            else:
                self.gift_table.setRowHidden(row, True)

    def export_links(self, selected_only=False):
        """导出链接到文件"""
        links_to_export = []
        if selected_only:
            # 导出 gift table 选中的
            selected_gift_rows = {index.row() for index in self.gift_table.selectedIndexes()}
            for row in selected_gift_rows:
                item = self.gift_table.item(row, 0)
                if item and not self.gift_table.isRowHidden(row):
                    links_to_export.append(item.text())
            # 导出 vip table 选中的
            selected_vip_rows = {index.row() for index in self.vip_table.selectedIndexes()}
            for row in selected_vip_rows:
                item = self.vip_table.item(row, 0)
                if item and not self.vip_table.isRowHidden(row):
                    links_to_export.append(item.text())
        else: # 导出所有可见的
            for row in range(self.gift_table.rowCount()):
                if not self.gift_table.isRowHidden(row):
                    links_to_export.append(self.gift_table.item(row, 0).text())
            for row in range(self.vip_table.rowCount()):
                if not self.vip_table.isRowHidden(row):
                    links_to_export.append(self.vip_table.item(row, 0).text())

        if not links_to_export:
            QMessageBox.information(self, "无内容", "没有可导出的链接。")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "保存链接到文件", "", "文本文件 (*.txt)")
        if file_path:
            self.file_worker = FileOperationThread('save_text', file_path, data='\n'.join(links_to_export))
            self.file_worker.operation_completed.connect(lambda s, m, d: QMessageBox.information(self, "成功" if s else "失败", m))
            self.file_worker.start()

    def set_controls_state(self, is_running):
        self.start_analysis_button.setEnabled(not is_running)
        self.stop_analysis_button.setEnabled(is_running)
        self.load_links_button.setEnabled(not is_running)
        self.links_input.setDisabled(is_running)
        
        if not is_running:
            self.gift_progress.setValue(0)
            self.vip_progress.setValue(0) 