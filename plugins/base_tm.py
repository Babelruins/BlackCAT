from PyQt5 import QtWidgets, QtCore, QtGui
from fuzzywuzzy import fuzz
from core import db_op

class plugin_thread(QtCore.QThread):
	finished = QtCore.pyqtSignal(object)
	
	def __init__(self, options, finished_callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.finished.connect(finished_callback)
		
		self.aborted = False
	
	def run(self):
		matching_segments = db_op.get_translation_memory(self.options['project_file_path'], self.options['segment_id'], self.options['source_language'], self.options['target_language'], self.options['source_text'], self.options['filename'], 50)
		
		if not self.aborted:
			self.finished.emit(matching_segments)

class main_widget(QtWidgets.QWidget):
	def __init__(self):
		super(main_widget, self).__init__()

		self.name = "Translation Memory"
		
		main_layout = QtWidgets.QGridLayout(self)
		
		self.candidates_box = QtWidgets.QTableWidget(self)
		self.candidates_box.setColumnCount(4)
		self.candidates_box.setHorizontalHeaderLabels(["%", "Source text", "Target text", "File"])
		self.table_header = self.candidates_box.horizontalHeader()
		self.table_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		self.table_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
		self.table_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
		self.table_header.setSectionResizeMode(3, QtWidgets.QHeaderView.Interactive)
		self.candidates_box.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
		self.candidates_box.verticalHeader().hide()
		self.candidates_box.sortItems(0, QtCore.Qt.DescendingOrder)
		
		self.candidates_box.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.candidates_box.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.candidates_box.setFont(QtGui.QFont("Lucida Console"))
		self.candidates_box.setAlternatingRowColors(True)
		
		self.candidates_box.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.candidates_box.customContextMenuRequested.connect(self.contextMenuEvent)
		
		status_layout = QtWidgets.QHBoxLayout()
		self.status_label = QtWidgets.QLabel("Ready.")
		status_layout.addWidget(self.status_label)
		
		main_layout.addWidget(self.candidates_box, 0, 0)
		main_layout.addLayout(status_layout, 1, 0)
		
		self.limit = 50
	
	def contextMenuEvent(self, pos):
		self.target_text = self.parent().parent().main_widget.target_text
	
		if self.candidates_box.currentRow() >= 0:
			self.context_menu = QtWidgets.QMenu()
			insert_target_action = QtWidgets.QAction("Insert coincidence target text")
			insert_target_action.triggered.connect(self.insert_target)
			insert_source_action = QtWidgets.QAction("Insert coincidence source text")
			insert_source_action.triggered.connect(self.insert_source)
			replace_target_action = QtWidgets.QAction("Replace with coincidence target text")
			replace_target_action.triggered.connect(self.replace_target)
			replace_source_action = QtWidgets.QAction("Replace with coincidence source text")
			replace_source_action.triggered.connect(self.replace_source)
			self.context_menu.addAction(insert_target_action)
			self.context_menu.addAction(insert_source_action)
			self.context_menu.addAction(replace_target_action)
			self.context_menu.addAction(replace_source_action)
			action = self.context_menu.exec_(self.candidates_box.viewport().mapToGlobal(pos))
		
	def insert_target(self):
		self.target_text.setText(self.target_text.toPlainText() + self.candidates_box.item(self.candidates_box.currentRow(), 2).text())
		
	def insert_source(self):
		self.target_text.setText(self.target_text.toPlainText() + self.candidates_box.item(self.candidates_box.currentRow(), 1).text())
		
	def replace_target(self):
		self.target_text.setText(self.candidates_box.item(self.candidates_box.currentRow(), 2).text())
		
	def replace_source(self):
		self.target_text.setText(self.candidates_box.item(self.candidates_box.currentRow(), 1).text())
		
	def main_action(self, options):
		if hasattr(self, 'plugin_thread'):
			self.plugin_thread.aborted = True
			self.plugin_thread.quit()
		self.plugin_thread = plugin_thread(options, self.onFinish, self)
		self.status_label.setText("Searching for fuzzy matches...")
		self.plugin_thread.start()
	
	def onFinish(self, result):
		self.candidates_box.setSortingEnabled(False)
		if len(result) >= self.limit:
			total = self.limit
		else:
			total = len(result)
		total_str = str(total)
		self.candidates_box.setRowCount(total)
		for index, row in enumerate(result):
			percent_widget = QtWidgets.QTableWidgetItem()
			percent_widget.setData(QtCore.Qt.EditRole, QtCore.QVariant(row[4]))
			if row[4] == 100:
				percent_widget.setBackground(QtGui.QColor(0, 255, 0))
			else:
				percent_widget.setBackground(QtGui.QColor(255, 255, 0))
			self.candidates_box.setItem(index, 0, percent_widget)
			
			source_widget = QtWidgets.QTableWidgetItem()
			source_widget.setData(QtCore.Qt.EditRole, QtCore.QVariant(row[1]))
			self.candidates_box.setItem(index, 1, source_widget)
			
			target_widget = QtWidgets.QTableWidgetItem()
			target_widget.setData(QtCore.Qt.EditRole, QtCore.QVariant(row[2]))
			self.candidates_box.setItem(index, 2, target_widget)
			
			file_widget = QtWidgets.QTableWidgetItem()
			file_widget.setData(QtCore.Qt.EditRole, QtCore.QVariant(row[3]))
			self.candidates_box.setItem(index, 3, file_widget)
			
			self.status_label.setText('Loading match ' + str(index + 1) + ' of ' + total_str + '.')
			QtWidgets.QApplication.processEvents()
			
			if index + 1 >= self.limit:
				break
		self.candidates_box.setSortingEnabled(True)
		self.status_label.setText('Ready.')