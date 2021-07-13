from PyQt5 import QtWidgets, QtCore, QtGui
from fuzzywuzzy import fuzz
from core import db_op
from os import path
from mstranslator import Translator
import html

class main_worker(QtCore.QObject):
	start = QtCore.pyqtSignal(object)
	interrupt = QtCore.pyqtSignal()
	refresh = QtCore.pyqtSignal()
	import_tm = QtCore.pyqtSignal(object)
	import_tm_finish = QtCore.pyqtSignal(object)
	finished = QtCore.pyqtSignal(object)

	def __init__(self):
		super(main_worker, self).__init__()

		self.tm_source_segments_cache = None
		self.start.connect(self.run, QtCore.Qt.QueuedConnection)
		self.interrupt.connect(self.stop)
		self.refresh.connect(self.refresh_tm)
		self.import_tm.connect(self.import_tm_files)
		
		#self.mutex = QtCore.QMutex()
		self.limit = 15
		self.running = False
		self.tm_path = 'global_tm.blc'
		self.verify_tm()

	@QtCore.pyqtSlot(object)
	def run(self, options):
		#self.mutex.lock()
		
		self.running = True

		suggestions_html = '<table border="0.5" cellspacing="0" cellpadding="2" width="100%" style="border-color:gray;">'

		if self.tm_source_segments_cache is None:
			self.refresh_tm()

		if not self.running:
			return

		if self.tm_source_segments_cache:
			matching_segments = db_op.get_translation_memory(self.tm_path, self.tm_source_segments_cache, options['target_language'], options['source_text'], 60)
		else:
			matching_segments = []

		if not self.running:
			return
		
		if options['context']:
			suggestions_html += '<tr>'
			suggestions_html += '<td valign="middle"><img src="images/code_white_24dp.svg"></td>'
			suggestions_html += '<td><font color="gray">Occurrences (first 4):</font>'
			for index, occurrence in enumerate(options['context']):
				if index > 3:
					break
				suggestions_html += '<br>' + occurrence[0] + ':' + occurrence[1]
			suggestions_html += '</td></tr>'

		if options['previous_text']:
			if options['previous_text'] != '':
					suggestions_html += '<tr>'
					suggestions_html += '<td valign="middle"><img src="images/undo_white_24dp.svg"></td>'
					suggestions_html += '<td><font color="gray">Previous text:</font><br>'
					suggestions_html += html.escape(options['previous_text'])
					suggestions_html += '</td></tr>'

		for index, row in enumerate(matching_segments):
			suggestions_html += '<tr>'
			suggestions_html += '<td valign="middle"><img src="images/storage_white_24dp.svg"></td>'
			suggestions_html += '<td><font color="gray">TM match (' + str(row[0]) + '%):</font><br>'
			suggestions_html += html.escape(row[1])
			suggestions_html += '<br><font color="gray">Translated text:</font><br>'
			suggestions_html += html.escape(row[2])
			suggestions_html += '</td></tr>'
			if index + 1 >= self.limit:
				break
			if not self.running:
				return
		suggestions_html += '</table>'
		self.finished.emit(suggestions_html)

		#Machine translation
		settings = QtCore.QSettings("Babelruins.org", "BlackCAT")
		translator = Translator(settings.value('plugins_mstranslate_api_key', ""))
		try:
			mst_response = translator.translate(options['source_text'], options['source_language'], options['target_language'])
			if mst_response:
				#suggestions_html += '<table border="0.5" cellspacing="0" cellpadding="2" width="100%" style="border-color:gray;">'
				suggestions_html = suggestions_html[:-8]
				suggestions_html += '<tr>'
				suggestions_html += '<td valign="middle"><img src="images/computer_white_24dp.svg"></td>'
				suggestions_html += '<td><font color="gray">Microsoft Translate:</font><br>'
				suggestions_html += html.escape(mst_response)
				suggestions_html += '</td></tr>'
				suggestions_html += '</table>'
				#suggestions_html.replace('</table>', mt_html)
				if not self.running:
					return
				self.finished.emit(suggestions_html)
		except Exception as e:
			print(str(e))

		#self.mutex.unlock()
	
	def stop(self):
		self.running = False

	def refresh_tm(self):
		self.tm_source_segments_cache = db_op.get_source_segments_from_translation_memory(self.tm_path)

	def verify_tm(self):
		#Check if file exists:
		if not path.exists(self.tm_path):
			db_op.create_project_db(self.tm_path)
		else:
			if not db_op.verify_tm(self.tm_path):
				print("File " + self.tm_path + " is not a valid translation memory file.")

	def import_tm_files(self, files):
		imported_files = db_op.import_tm(self.tm_path, files)
		self.import_tm_finish.emit(imported_files)

class main_widget(QtWidgets.QWidget):
	def __init__(self):
		super(main_widget, self).__init__()

		self.name = "Translation Memory"
		self.running = False
		self.abort = False
		
		main_layout = QtWidgets.QGridLayout(self)

		self.suggestions = QtWidgets.QTextEdit(self)
		self.suggestions.setFont(QtGui.QFont("Lucida Console"))
		self.suggestions.setReadOnly(True)
		self.suggestions.setStyleSheet("QTextEdit { padding:0; }")
		
		status_layout = QtWidgets.QHBoxLayout()
		self.status_label = QtWidgets.QLabel("Ready.")
		status_layout.addWidget(self.status_label)

		main_layout.addWidget(self.suggestions, 0, 0)
		main_layout.addLayout(status_layout, 1, 0)
		
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

	def import_tm_onFinish(self, imported_files):
		message = "Imported files: " + str(len(imported_files))
		for file in imported_files:
			message = message + "\n- " + file
		info_box = QtWidgets.QMessageBox()
		info_box.setWindowTitle('BlackCAT')
		info_box.setText(message)
		info_box.setIcon(QtWidgets.QMessageBox.Information)
		info_box.exec_()