from PyQt5 import QtWidgets, QtCore, QtGui
from fuzzywuzzy import fuzz
from core import db_op
import html

class main_worker(QtCore.QObject):
	start = QtCore.pyqtSignal(object)
	interrupt = QtCore.pyqtSignal()
	finished = QtCore.pyqtSignal(object)

	def __init__(self):
		super(main_worker, self).__init__()

		self.tm_source_segments_cache = None
		self.start.connect(self.run, QtCore.Qt.QueuedConnection)
		self.interrupt.connect(self.stop)
		
		#self.mutex = QtCore.QMutex()
		self.limit = 15
		self.running = False

	@QtCore.pyqtSlot(object)
	def run(self, options):
		#self.mutex.lock()
		
		self.running = True

		suggestions_html = '<table border="0.5" cellspacing="0" cellpadding="2" width="100%" style="border-color:gray;">'

		if self.tm_source_segments_cache is None:
			self.tm_source_segments_cache = db_op.get_source_segments_from_translation_memory(options['project_file_path'])

		if not self.running:
			return

		matching_segments = db_op.get_translation_memory(options['project_file_path'], self.tm_source_segments_cache, options['target_language'], options['source_text'], 50)

		if not self.running:
			return
		
		if options['previous_text']:
			if options['previous_text'] != '':
					suggestions_html += '<tr>'
					suggestions_html += '<td valign="middle"><img src="images/undo_white_24dp.svg"></td>'
					suggestions_html += '<td><font color="gray">Previous text:</font><br>'
					suggestions_html += html.escape(options['previous_text'])
					suggestions_html += '</tr></td>'

		if len(matching_segments) >= self.limit:
			total = self.limit
		else:
			total = len(matching_segments)

		for index, row in enumerate(matching_segments):
			suggestions_html += '<tr>'
			suggestions_html += '<td valign="middle"><img src="images/storage_white_24dp.svg"></td>'
			suggestions_html += '<td><font color="gray">TM match (' + str(row[0]) + '%):</font><br>'
			suggestions_html += html.escape(row[1])
			suggestions_html += '<br><font color="gray">Translated text:</font><br>'
			suggestions_html += html.escape(row[2])
			suggestions_html += '</tr></td>'
			if index + 1 >= self.limit:
				break
			if not self.running:
				return
		suggestions_html += '</table>'
		self.finished.emit(suggestions_html)

		#self.mutex.unlock()
	
	def stop(self):
		self.running = False

class main_widget(QtWidgets.QWidget):
	def __init__(self):
		super(main_widget, self).__init__()

		self.name = "Translation Memory"
		self.running = False
		self.abort = False
		
		main_layout = QtWidgets.QGridLayout(self)

		#New test
		self.suggestions = QtWidgets.QTextEdit(self)
		self.suggestions.setFont(QtGui.QFont("Lucida Console"))
		self.suggestions.setReadOnly(True)
		self.suggestions.setStyleSheet("QTextEdit { padding:0; }")
		#self.suggestions.document().setDefaultStyleSheet('table { border-style: solid; border-color:red;}')
		
		#self.candidates_box = QtWidgets.QTableWidget(self)
		#self.candidates_box.setColumnCount(1)
		#self.candidates_box.setHorizontalHeaderLabels(["Suggestions"])
		#self.table_header = self.candidates_box.horizontalHeader()
		#self.table_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
		#self.table_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
		#self.table_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
		#self.table_header.setSectionResizeMode(3, QtWidgets.QHeaderView.Interactive)
		#self.candidates_box.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
		#self.candidates_box.verticalHeader().hide()
		#self.candidates_box.sortItems(0, QtCore.Qt.DescendingOrder)
		
		#self.candidates_box.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		#self.candidates_box.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		#self.candidates_box.setFont(QtGui.QFont("Lucida Console"))
		#self.candidates_box.setAlternatingRowColors(True)
		
		#self.candidates_box.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		#self.candidates_box.customContextMenuRequested.connect(self.contextMenuEvent)
		
		status_layout = QtWidgets.QHBoxLayout()
		self.status_label = QtWidgets.QLabel("Ready.")
		status_layout.addWidget(self.status_label)
		
		#main_layout.addWidget(self.candidates_box, 0, 0)
		main_layout.addWidget(self.suggestions, 0, 0)
		main_layout.addLayout(status_layout, 1, 0)
		
		#self.limit = 15
	
	def contextMenuEvent(self, pos):
		self.target_text = self.parent().parent().main_widget_target_text
	
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
	
	def onFinish(self, html):
		self.suggestions.setHtml(html)

	def old3_onFinish(self, index, html):
		if index == 0:
			self.candidates_box.setRowCount(0)
		self.candidates_box.insertRow(index)
		#item = QtWidgets.QTextEdit()
		#item.setHtml(html)
		#item.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		item = QtWidgets.QLabel(html)
		item.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
		item.setFont(QtGui.QFont("Lucida Console"))
		item.setWordWrap(True)
		self.candidates_box.verticalHeader().setSectionResizeMode(index, QtWidgets.QHeaderView.ResizeToContents)
		self.candidates_box.setCellWidget(index, 0, item)

	def old_onFinish(self, result):
		#self.running = True
		#self.candidates_box.setSortingEnabled(False)
		if (result is None):
			return
		if len(result) >= self.limit:
			total = self.limit
		else:
			total = len(result)
		#total_str = str(total)
		self.candidates_box.setRowCount(total)
		for index, row in enumerate(result):
			if self.abort:
				print('canceling tm')
				break
			#print(self.plugin_thread.aborted)
			percent_widget = QtWidgets.QTableWidgetItem()
			percent_widget.setData(QtCore.Qt.EditRole, QtCore.QVariant(row[0]))
			if row[0] == 100:
				percent_widget.setBackground(QtGui.QColor(0, 255, 0))
			else:
				percent_widget.setBackground(QtGui.QColor(255, 255, 0))
			self.candidates_box.setItem(index, 0, percent_widget)
			
			source_widget = QtWidgets.QTableWidgetItem(row[1])
			#source_widget.setData(QtCore.Qt.EditRole, QtCore.QVariant(row[1]))
			self.candidates_box.setItem(index, 1, source_widget)
			
			target_widget = QtWidgets.QTableWidgetItem(row[2])
			#target_widget.setData(QtCore.Qt.EditRole, QtCore.QVariant(row[2]))
			self.candidates_box.setItem(index, 2, target_widget)
			
			#file_widget = QtWidgets.QTableWidgetItem()
			#file_widget.setData(QtCore.Qt.EditRole, QtCore.QVariant(row[3]))
			#self.candidates_box.setItem(index, 3, file_widget)
			
			#self.status_label.setText('Loading match ' + str(index + 1) + ' of ' + total_str + '.')
			#QtWidgets.QApplication.processEvents()
			
			if index + 1 >= self.limit:
				break
		#self.candidates_box.setSortingEnabled(True)
		self.status_label.setText('Ready.')
		#self.abort = False
		#self.running = False
