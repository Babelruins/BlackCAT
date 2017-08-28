from PyQt5 import QtWidgets, QtCore, QtGui
import configparser, nltk.data, os, functools, webbrowser, re, enchant
from core import dialogs, db_op
import text_processors, plugins
from bs4 import BeautifulSoup

class tags_highlighter(QtGui.QSyntaxHighlighter):
	def __init__(self, parent=None):
		super(tags_highlighter, self).__init__(parent)
		
		tag_format = QtGui.QTextCharFormat()
		tag_format.setForeground(QtCore.Qt.gray)
		tag_regex = QtCore.QRegExp("<[^\n]*>")
		tag_regex.setMinimal(True)
		self.highlightingRules = []
		self.highlightingRules.append((tag_regex, tag_format))
		
		self.dict = None
		self.spell_check_format = QtGui.QTextCharFormat()
		self.spell_check_format.setUnderlineColor(QtCore.Qt.red)
		self.spell_check_format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
		
	def set_dictionary(self, dict):
		self.dict = dict
		
	def highlightBlock(self, text):
		#Spell checking
		if self.dict is not None:
			for word in re.finditer('(?iu)[\w\']+', text):
				if not self.dict.check(word.group()):
					self.setFormat(word.start(), word.end() - word.start(), self.spell_check_format)
					
		#Tags
		for pattern, format in self.highlightingRules:
			expression = QtCore.QRegExp(pattern)
			index = expression.indexIn(text)
			
			while index >= 0:
				length = expression.matchedLength()
				self.setFormat(index, length, format)
				index = expression.indexIn(text, index + length)
				
class generate_translated_files_thread(QtCore.QThread):
	progress = QtCore.pyqtSignal(object)
	finished = QtCore.pyqtSignal()
	
	def __init__(self, options, on_progress, on_finish, parent=None):
		QtCore.QThread.__init__(self, parent)
		self.options = options
		self.progress.connect(on_progress)
		self.finished.connect(on_finish)

	def run(self):
		files_already_imported = db_op.get_imported_files(self.options['project_path'])
		for file in self.options['source_file_dir']:
			file_path = os.path.join(self.options['project_dir'], 'source_files', file)
			if (os.path.isfile(file_path)):
				if file in files_already_imported:
					self.options['file_path'] = file_path
					try:
						if files_already_imported[file] == "punkt":
							self.progress.emit("Processing file '" + file + "' with 'punkt' processor...")
							text_processors.punkt.generate_file(self.options)
							self.progress.emit('<font color="green">Success!</font>')
						elif files_already_imported[file] == "odt":
							self.progress.emit("Processing file '" + file + "' with 'odt' processor...")
							text_processors.odt.generate_file(self.options)
							self.progress.emit('<font color="green">Success!</font>')
						elif files_already_imported[file] == "sgml":
							self.progress.emit("Processing file '" + file + "' with 'sgml' processor...")
							text_processors.sgml.generate_file(self.options)
							self.progress.emit('<font color="green">Success!</font>')
						elif files_already_imported[file] == "gettext":
							self.progress.emit("Processing file '" + file + "' with 'gettext' processor...")
							text_processors.gettext.generate_file(self.options)
							self.progress.emit('<font color="green">Success!</font>')
						else:
							self.progress.emit("ERROR: Unsupported generate method '" + files_already_imported[file] + "'for file '" + file + "'.")
					except Exception as e:
						self.progress.emit('<font color="red">' + type(e).__name__ + ': ' + str(e) + '</font>')
				else:
					self.progress.emit("<font color=\"orange\">WARNING: File '" + file + "' has not been imported yet, it will not be processed.</font>")
		self.finished.emit()

class import_files_thread(QtCore.QThread):
	progress = QtCore.pyqtSignal(object)
	finished = QtCore.pyqtSignal(object)
	
	def __init__(self, options, on_progress, on_finish, parent=None):
		QtCore.QThread.__init__(self, parent)
		self.options = options
		self.progress.connect(on_progress)
		self.finished.connect(on_finish)
		
	def run(self):
		#If the item is a file and is not already imported, import it
		valid_files = []
		for file in self.options['source_file_dir']:
			self.progress.emit("Processing '" + file + "' ...")
			file_path = os.path.join(self.options['project_dir'], 'source_files', file)
			if (os.path.isfile(file_path)):
				valid_files.append(file)
				new_m_time = os.path.getmtime(file_path)
				if file not in self.options['files_already_imported']:
					self.progress.emit("'" + file + "' has not been imported yet, processing ...")
					self.import_file_into_project(file_path, new_m_time)
				else:
					#Do the same for the files that have changed
					if self.options['files_already_imported'][file] != new_m_time:
						self.progress.emit("'" + file + "' has changed, processing ...")
						self.import_file_into_project(file_path, new_m_time)
					else:
						self.progress.emit("'" + file + "' has not changed, skipping ...")
			else:
				self.progress.emit("'" + file + "' is not a file.")
		
		#If a file has been deleted from the source_file dir but still in the database:
		for file in self.options['files_already_imported']:
			if file not in valid_files:
				db_op.save_file_as_tm(self.options['project_path'], file)
				
		self.finished.emit(valid_files)
	
	def import_file_into_project(self, file_path, m_time):
		text_processor_options = {}
		text_processor_options['project_path'] = self.options['project_path']
		text_processor_options['file_path'] = file_path
		text_processor_options['source_language'] = self.options['source_language']
		text_processor_options['target_language'] = self.options['target_language']
		text_processor_options['m_time'] = m_time
	
		#first check file type
		file_extension = os.path.splitext(file_path)[1]
		try:
			if file_extension == ".txt":
				text_processors.punkt.import_file(text_processor_options)
				self.progress.emit('<font color="green">Success!</font>')
			elif file_extension == ".odt":
				text_processors.odt.import_file(text_processor_options)
				self.progress.emit('<font color="green">Success!</font>')
			elif file_extension == ".sgml":
				text_processors.sgml.import_file(text_processor_options)
				self.progress.emit('<font color="green">Success!</font>')
			elif file_extension == ".po":
				text_processors.gettext.import_file(text_processor_options)
				self.progress.emit('<font color="green">Success!</font>')
			else:
				self.progress.emit("<font color=\"orange\">WARNING: Unsupported file extension '" + file_extension + "'.</font>")
		except Exception as e:
			self.progress.emit('<font color="red">' + type(e).__name__ + ': ' + str(e) + '</font>')

class main_window(QtWidgets.QMainWindow):
	def __init__(self):
		super(main_window, self).__init__()
		
		self.reset_globals()
		self.status_msgbox = None
		
		self.main_widget = QtWidgets.QWidget(self)
		
		#Main layout
		self.main_widget.main_v_layout = QtWidgets.QVBoxLayout(self.main_widget)
		self.main_widget.main_h_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
		
		#Editor side
		self.main_widget.editor_v_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
		self.main_widget.main_editor_groupbox = QtWidgets.QGroupBox("[No file]")
		self.main_widget.main_editor_layout = QtWidgets.QVBoxLayout(self.main_widget.main_editor_groupbox)
		
		self.main_widget.main_editor = QtWidgets.QTableWidget(self)
		self.main_widget.main_editor.setColumnCount(3)
		self.main_widget.main_editor.setHorizontalHeaderLabels(["ID", "Source text", "Target text"])
		#self.main_widget.main_editor.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
		table_header = self.main_widget.main_editor.horizontalHeader()
		table_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		table_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
		table_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
		self.main_widget.main_editor.verticalHeader().hide()
		self.main_widget.main_editor.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.main_widget.main_editor.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.main_widget.main_editor.setFont(QtGui.QFont("Lucida Console"))
		self.main_widget.main_editor.setAlternatingRowColors(True)
		self.main_widget.main_editor.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.main_widget.main_editor.currentCellChanged.connect(self.main_editor_currentCellChanged)
		
		self.main_widget.source_text = QtWidgets.QTextEdit(self)
		self.main_widget.source_text.setFont(QtGui.QFont("Lucida Console"))
		self.main_widget.source_text.setReadOnly(True)
		self.main_widget.source_text.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.main_widget.source_text.customContextMenuRequested.connect(self.build_source_context_menu)
		source_text_highlighter = tags_highlighter(self.main_widget.source_text)
		
		self.main_widget.target_text = QtWidgets.QTextEdit(self)
		self.main_widget.target_text.setFont(QtGui.QFont("Lucida Console"))
		self.main_widget.target_text.setAcceptRichText(False)
		self.main_widget.target_text.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.main_widget.target_text.customContextMenuRequested.connect(self.build_target_context_menu)
		target_text_highlighter = tags_highlighter(self.main_widget.target_text)
		target_text_highlighter.set_dictionary(enchant.Dict())

		self.main_widget.current_segment_groupbox = QtWidgets.QGroupBox()
		self.main_widget.current_segment_layout = QtWidgets.QVBoxLayout(self.main_widget.current_segment_groupbox)
		self.main_widget.fuzzy_checkbox = QtWidgets.QCheckBox("Fuzzy translation.")
		self.main_widget.current_segment_layout.addWidget(self.main_widget.fuzzy_checkbox)
		
		self.main_widget.current_segment_source_tab_widget = QtWidgets.QTabWidget()
		self.main_widget.current_segment_layout.addWidget(self.main_widget.current_segment_source_tab_widget)
		self.main_widget.current_segment_source_tab_widget.addTab(self.main_widget.source_text, "Original text")
		
		self.main_widget.current_segment_target_tab_widget = QtWidgets.QTabWidget()
		self.main_widget.current_segment_layout.addWidget(self.main_widget.current_segment_target_tab_widget)
		self.main_widget.current_segment_target_tab_widget.addTab(self.main_widget.target_text, "Translated text")
		
		self.main_widget.main_editor_layout.addWidget(self.main_widget.main_editor)
		self.main_widget.editor_v_splitter.addWidget(self.main_widget.main_editor_groupbox)
		self.main_widget.editor_v_splitter.addWidget(self.main_widget.current_segment_groupbox)
		
		#Plugins side
		self.main_widget.plugins_v_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
		
		#Putting the main layout together
		self.main_widget.main_h_splitter.addWidget(self.main_widget.editor_v_splitter)
		self.main_widget.main_h_splitter.addWidget(self.main_widget.plugins_v_splitter)
		self.main_widget.main_v_layout.addWidget(self.main_widget.main_h_splitter)
		
		self.setCentralWidget(self.main_widget)
		
		#load the plugins
		self.list_of_loaded_plugin_widgets = []
		for plugin_widget in plugins.list_of_widgets:
			new_widget = plugin_widget()
			self.list_of_loaded_plugin_widgets.append(new_widget)
			self.main_widget.plugins_v_splitter.addWidget(new_widget)
		
		#Load the settings
		self.recent_files = []
		try:
			settings = QtCore.QSettings("Babelruins.org", "BlackCAT")
			self.recent_files = settings.value('recent_files', [])
			if self.recent_files is None:
				self.recent_files = []
			self.resize(settings.value('width', type=int), settings.value('height', type=int))
			self.move(settings.value('x_position', type=int), settings.value('y_position', type=int))
			if settings.value('maximized', type=bool):
				self.setWindowState(QtCore.Qt.WindowMaximized)
			self.main_widget.editor_v_splitter.restoreState(settings.value('editor_splitter_settings'))
			self.main_widget.main_h_splitter.restoreState(settings.value('main_splitter_settings'))
			if settings.value('number_of_loaded_plugins') == len(self.list_of_loaded_plugin_widgets):
				self.main_widget.plugins_v_splitter.restoreState(settings.value('plugins_splitter_settings'))
		except Exception as e:
			#Load the defaults
			self.resize(800,600)
			self.main_widget.editor_v_splitter.setSizes([400, 200])
			print(e)
		
		self.menu_bar = self.menuBar()
		self.build_menu(self.recent_files, False)
		
		#Status bar
		self.main_status_bar = QtWidgets.QStatusBar()
		self.setStatusBar(self.main_status_bar)
		self.status_label = QtWidgets.QLabel("Ready.")
		self.main_status_bar.addWidget(self.status_label, 1)
		
		self.file_statistics_label = QtWidgets.QLabel("File segments: -/-")
		self.main_status_bar.addPermanentWidget(self.file_statistics_label)
		
		self.project_statistics_label = QtWidgets.QLabel("Project segments: -/-")
		self.main_status_bar.addPermanentWidget(self.project_statistics_label)
		
		#Shortcuts
		next_segment_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+U"), self)
		next_segment_shortcut.activated.connect(self.go_to_next_segment)
		insert_tag_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+T"), self)
		insert_tag_shortcut.activated.connect(self.insert_next_tag)
		
		#Threads
		self.db_thread = QtCore.QThread(self)
		self.db_thread.start()
		self.db_background_worker = db_op.db_worker()
		self.db_background_worker.finished.connect(self.db_thread_on_finish)
		self.db_background_worker.moveToThread(self.db_thread)
	
	def reset_globals(self):
		self.filename = ''
		self.project_path = ''
		self.project_dir = ''
		self.valid_files = ''
		self.source_language = ''
		self.target_language = ''
		self.previous_translated_text = ''
		self.previous_plurals = {}
		self.project_total_segments = 0
		self.project_transtaled_segments = 0
		self.working_with_plurals = False
		self.plurals = {}
		self.max_plurals_in_file = 0
	
	def show_plural_controls(self, n):
		plurals = []
		plural_text_highlighters = []
		for i in range(n):
			plurals.append(QtWidgets.QTextEdit(self))
			
		for plural in plurals:
			plural.setFont(QtGui.QFont("Lucida Console"))
			plural.setAcceptRichText(False)
			plural.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
			plural.customContextMenuRequested.connect(self.build_target_context_menu)
			plural_text_highlighters.append(tags_highlighter(plural.document()))
		
		for i in range(n):
			self.main_widget.current_segment_target_tab_widget.addTab(plurals[i], "Plural [" + str(i+1) + "]")
	
	def hide_plural_controls(self):
		for i in range(self.main_widget.current_segment_target_tab_widget.count() - 1):
			self.main_widget.current_segment_target_tab_widget.removeTab(1)

	def build_source_context_menu(self, pos):
		self.main_widget.source_text.context_menu = self.main_widget.source_text.createStandardContextMenu()
		self.main_widget.source_text.context_menu.addSeparator()
		self.main_widget.source_text.context_menu.addAction("Google Search in Browser", lambda: webbrowser.open_new_tab('https://www.google.com/search?q=' + self.main_widget.source_text.textCursor().selectedText()))
		#for plugin in self.list_of_loaded_plugin_widgets:
		#		if hasattr(plugin, 'secondary_action'):
		#		self.main_widget.source_text.context_menu.addAction(plugin.name, lambda name=plugin.name:self.secondary_action_trigger(name, self.main_widget.source_text.textCursor().selectedText()))
		self.main_widget.source_text.context_menu.exec_(self.main_widget.source_text.viewport().mapToGlobal(pos))
		
	def build_target_context_menu(self, pos):
		self.main_widget.target_text.context_menu = self.main_widget.target_text.createStandardContextMenu()
		self.main_widget.target_text.context_menu.addSeparator()
		self.main_widget.target_text.context_menu.addAction("Google Search in Browser", lambda: webbrowser.open_new_tab('https://www.google.com/search?q=' + self.main_widget.target_text.textCursor().selectedText()))
		#for plugin in self.list_of_loaded_plugin_widgets:
		#	if hasattr(plugin, 'secondary_action'):
		#		self.main_widget.target_text.context_menu.addAction(plugin.name, lambda name=plugin.name:self.secondary_action_trigger(name, self.main_widget.target_text.textCursor().selectedText()))
		self.main_widget.target_text.context_menu.exec_(self.main_widget.target_text.viewport().mapToGlobal(pos))
	
	def secondary_action_trigger(self, name, text):
		for plugin in self.list_of_loaded_plugin_widgets:
			if (plugin.name == name) and hasattr(plugin, 'secondary_action'):
				plugin.secondary_action(text)
	
	def build_menu(self, recent_files, is_project_open):
		self.menu_bar.clear()
		self.menu_file_new = QtWidgets.QAction(QtGui.QIcon('new.png'), '&New Project Directory', self)
		self.menu_file_new.setShortcut('Ctrl+N')
		self.menu_file_new.setStatusTip('Create a new project directory')
		self.menu_file_new.triggered.connect(self.new_project)
		
		self.menu_file_open = QtWidgets.QAction(QtGui.QIcon('open.png'), '&Open Project', self)
		self.menu_file_open.setShortcut('Ctrl+O')
		self.menu_file_open.setStatusTip('Open a project file')
		self.menu_file_open.triggered.connect(lambda: self.open_project(False))
		
		self.menu_file_save = QtWidgets.QAction('&Save Project', self)
		self.menu_file_save.setShortcut('Ctrl+S')
		self.menu_file_save.setStatusTip('Save current project')
		self.menu_file_save.triggered.connect(self.save_current_file)
		
		self.menu_file_close = QtWidgets.QAction('Close Project', self)
		self.menu_file_close.setShortcut('Ctrl+W')
		self.menu_file_close.setStatusTip('Close current project')
		self.menu_file_close.triggered.connect(self.close_current_project)
		
		self.menu_project_project_files = QtWidgets.QAction('Project Files &List', self)
		self.menu_project_project_files.setShortcut('Ctrl+L')
		self.menu_project_project_files.setStatusTip('Show a list of the files in the current project')
		self.menu_project_project_files.triggered.connect(self.call_file_picker)
		
		self.menu_project_import_tm = QtWidgets.QAction('Import translation memory files', self)
		self.menu_project_import_tm.setShortcut('Ctrl+I')
		self.menu_project_import_tm.setStatusTip('Import files into the project translation memory')
		self.menu_project_import_tm.triggered.connect(self.import_tm)
			
		self.menu_project_generate_translated_files = QtWidgets.QAction('&Generate translated files', self)
		self.menu_project_generate_translated_files.setShortcut('Ctrl+G')
		self.menu_project_generate_translated_files.setStatusTip('Generates translated files from the ones imported into the project')
		self.menu_project_generate_translated_files.triggered.connect(self.generate_translated_files)
		
		self.menu_file_exit = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
		self.menu_file_exit.setShortcut('Ctrl+Q')
		self.menu_file_exit.setStatusTip('Exit application')
		self.menu_file_exit.triggered.connect(QtWidgets.qApp.quit)
		
		self.menu_help_about = QtWidgets.QAction('&About', self)
		self.menu_help_about.setShortcut('Ctrl+A')
		self.menu_help_about.setStatusTip('Shows the about dialog.')
		self.menu_help_about.triggered.connect(self.show_about_dialog)
		
		#File menu
		self.menu_file = self.menu_bar.addMenu('&File')
		self.menu_file.addAction(self.menu_file_new)
		self.menu_file.addAction(self.menu_file_open)
		self.menu_file.addAction(self.menu_file_save)
		self.menu_file.addAction(self.menu_file_close)
		self.menu_file.addSeparator()
		if recent_files is not None:
			for path in recent_files:
				menu_recent_file = QtWidgets.QAction(path, self)
				menu_recent_file.triggered.connect(functools.partial(self.open_project, path))
				self.menu_file.addAction(menu_recent_file)
		self.menu_file.addSeparator()
		self.menu_file.addAction(self.menu_file_exit)
		
		#Project menu
		self.menu_project = self.menu_bar.addMenu('&Project')
		self.menu_project.addAction(self.menu_project_project_files)
		self.menu_project.addAction(self.menu_project_import_tm)
		self.menu_project.addAction(self.menu_project_generate_translated_files)
		
		#Help menu
		self.menu_help = self.menu_bar.addMenu('&Help')
		self.menu_help.addAction(self.menu_help_about)
			
		if is_project_open:
			self.menu_file_save.setEnabled(True)
			self.menu_file_close.setEnabled(True)
			self.menu_project.setEnabled(True)
		else:
			self.menu_file_save.setEnabled(False)
			self.menu_file_close.setEnabled(False)
			self.menu_project.setEnabled(False)
	
	def go_to_next_segment(self):
		max_row = self.main_widget.main_editor.rowCount() - 1
		if max_row >= 0:
			current_row = self.main_widget.main_editor.currentRow()
			if current_row >= 0 and current_row < max_row:
				self.main_widget.main_editor.setCurrentCell(current_row + 1, 0)
			else:
				self.main_widget.main_editor.setCurrentCell(0, 0)
				
	def insert_next_tag(self):
		source_text = self.main_widget.source_text.toPlainText()
		target_text = self.main_widget.target_text.toPlainText()
		text = target_text
		for match in re.findall('<[^\n]*?>', source_text):
			parts = text.split(match, 1)
			if (len(parts) == 1) and (source_text.count(match) > self.main_widget.target_text.toPlainText().count(match)):
				self.main_widget.target_text.insertPlainText(match)
				break
			elif len(parts) == 2:
				text = parts[1]
	
	def main_editor_currentCellChanged(self, current_row, current_column, previous_row, previous_column):
		#Check if we need to save the previous variant
		save_variant = False
		if previous_row >= 0:
			if self.main_widget.target_text.toPlainText() != self.previous_translated_text:
				save_variant = True

			for i in range(self.main_widget.current_segment_target_tab_widget.count()):
				if i > 0:
					if self.previous_plurals[i] != self.main_widget.current_segment_target_tab_widget.widget(i).toPlainText():
						save_variant = True
			
			if(self.main_widget.fuzzy_checkbox.isChecked()):
				previous_segment_new_fuzzy_status = True
			else:
				previous_segment_new_fuzzy_status = False
				
			if(self.previous_fuzzy_status != previous_segment_new_fuzzy_status):
				save_variant = True
					
		if save_variant:
			self.main_widget.main_editor.item(previous_row, 2).setText(self.main_widget.target_text.toPlainText())
			if self.main_widget.fuzzy_checkbox.isChecked():
				self.main_widget.main_editor.item(previous_row, 0).setBackground(QtGui.QColor(255, 255, 0))
			else:
				self.main_widget.main_editor.item(previous_row, 0).setBackground(QtGui.QColor(0, 255, 0))
				
			options = {}
			options['project_path'] = self.project_path
			options['segment'] = self.main_widget.target_text.toPlainText()
			options['target_language'] = self.target_language
			options['source_segment_id'] = self.main_widget.main_editor.item(previous_row, 0).text()
			options['source_file'] = self.filename
			options['fuzzy'] = self.main_widget.fuzzy_checkbox.isChecked()
			options['plural_index'] = 0
			options['action'] = 'save_variant'
			
			self.db_background_worker.start.emit(options)
			
			if self.working_with_plurals:
				plural_options = {}
				for i in range(self.main_widget.current_segment_target_tab_widget.count()):
					if i > 0:
						plural_options[i] = dict(options)
						plural_options[i]['segment'] = self.main_widget.current_segment_target_tab_widget.widget(i).toPlainText()
						plural_options[i]['plural_index'] = i
						
						self.db_background_worker.start.emit(plural_options[i])
						
						self.plurals[self.main_widget.main_editor.item(previous_row, 1).text(),i][0] = plural_options[i]['segment']
						
		#Check if the row we moved to is valid
		if current_row >= 0:
			#Check if we're gonna work with plurals
			current_source_text = self.main_widget.main_editor.item(current_row, 1).text()
			if (current_source_text,1) in self.plurals:
				self.working_with_plurals = True
				plurals_count = 0
				for sentence, plural_index in self.plurals.keys():
					if sentence == current_source_text:
						plurals_count += 1
				self.show_plural_controls(plurals_count)
			else:
				self.working_with_plurals = False
				self.hide_plural_controls()
			
			#Let's work on the current string
			if current_row != previous_row:
				if not self.working_with_plurals:
					self.main_widget.source_text.setText(current_source_text)
					self.main_widget.target_text.setText(self.main_widget.main_editor.item(current_row, 2).text())
				else:
					self.main_widget.source_text.setHtml('<font color="gray">Singular:</font><br>' + current_source_text + '<br><br><font color="gray">Plural:</font><br>' + self.plurals[current_source_text,1][2])
					self.main_widget.target_text.setText(self.main_widget.main_editor.item(current_row, 2).text())
					for i in range(plurals_count):
						self.main_widget.current_segment_target_tab_widget.widget(i+1).setText(self.plurals[current_source_text,i+1][0])
						self.previous_plurals = {}
						self.previous_plurals[i+1] = self.main_widget.current_segment_target_tab_widget.widget(i+1).toPlainText()
				
				self.previous_translated_text = self.main_widget.main_editor.item(current_row, 2).text()

				current_segment_color = self.main_widget.main_editor.item(current_row, 0).background().color()
				if(current_segment_color == QtGui.QColor(255, 255, 0)):
					self.main_widget.fuzzy_checkbox.setChecked(True)
					self.previous_fuzzy_status = True
				else:
					self.main_widget.fuzzy_checkbox.setChecked(False)
					self.previous_fuzzy_status = False
				
				#Get the plugins to work
				plugin_options = {}
				plugin_options['project_file_path'] = self.project_path
				plugin_options['filename'] = self.filename
				plugin_options['segment_id'] = self.main_widget.main_editor.item(current_row, 0).text()
				plugin_options['source_text'] = current_source_text
				plugin_options['target_text'] = self.main_widget.target_text.toPlainText()
				plugin_options['source_language'] = self.source_language
				plugin_options['target_language'] = self.target_language
				for plugin_widget in self.list_of_loaded_plugin_widgets:
					plugin_widget.main_action(plugin_options)
	
	def db_thread_on_finish(self, options):
		if options['action'] == 'save_variant':
			self.main_status_bar.showMessage("Segment #" + str(options['source_segment_id']) + " saved.", 3000)
			self.update_status_bar_file()
			self.update_status_bar_project()
	
	def save_variant_onFinish(self, source_segment_id):
		self.main_status_bar.showMessage("Segment #" + str(source_segment_id) + " saved.", 3000)
		self.update_status_bar_file()
		self.update_status_bar_project()
	
	def new_project(self):
		new_project_dialog = dialogs.new_project_dialog()
		if new_project_dialog.exec_():
			creation_path = new_project_dialog.location_input.text()
			project_name = new_project_dialog.name_input.text()
			
			self.open_project(os.path.join(creation_path, project_name, project_name + ".blc"))
	
	def open_project(self, project_file_path):
		if not project_file_path:
			project_path = QtWidgets.QFileDialog.getOpenFileName(self, 'Open project', '', 'BlackCAT files (*.blc)')[0]
			if not project_path:
				return
		else:
			if os.path.isfile(project_file_path):
				project_path = project_file_path
			else:
				error_message_box = QtWidgets.QMessageBox()
				error_message_box.setText("File " + str(project_file_path) + " not found")
				error_message_box.setIcon(QtWidgets.QMessageBox.Critical)
				error_message_box.exec_()
				return
		
		self.close_current_project()
		
		self.project_path = os.path.abspath(project_path)
		self.project_dir = os.path.dirname(self.project_path)
		
		#Get the settings
		self.source_language = db_op.get_setting(self.project_path, 'source_language')
		self.target_language = db_op.get_setting(self.project_path, 'target_language')
		
		#Get the list of the files at source_files that were already imported to the project
		files_already_imported = db_op.get_imported_files_mtime(self.project_path)
			
		#Save in recent files
		self.recent_files.append(self.project_path)
		self.build_menu(list(dict.fromkeys(self.recent_files[::-1]))[:10], True)
		self.setWindowTitle('BlackCAT - ' + str(self.project_path))
		
		#Check the items in source_file dir
		source_file_dir = os.listdir(os.path.join(self.project_dir, 'source_files'))
		
		options = {}
		options['project_dir'] = self.project_dir
		options['source_file_dir'] = source_file_dir
		options['files_already_imported'] = files_already_imported
		options['project_path'] = self.project_path
		options['source_language'] = self.source_language
		options['target_language'] = self.target_language
		
		if source_file_dir:
			import_thread = import_files_thread(options, self.open_project_on_progress, self.open_project_on_finish, self)
			self.status_msgbox = dialogs.status_dialog("Scan source files directory", "Processing files...")
			#self.status_msgbox.show()
			import_thread.start()
			self.status_msgbox.exec_()
			self.call_file_picker()
			
		else:
			error_message_box = QtWidgets.QMessageBox()
			error_message_box.setText("No valid source files were found. Please copy some supported files in the source_files directory of the project and try opening it again.")
			error_message_box.setIcon(QtWidgets.QMessageBox.Critical)
			error_message_box.exec_()

	def open_project_on_progress(self, message):
		self.status_msgbox.add_text(message)
	
	def open_project_on_finish(self, valid_files):
		self.valid_files = valid_files
		self.status_label.setText("Ready.")
		self.update_status_bar_project()
		self.status_msgbox.tasks_completed()
		#self.call_file_picker()
	
	def update_status_bar_project(self):
		options = {}
		options['project_path'] = self.project_path
		if hasattr(self, 'update_status_bar_project_thread'):
			self.update_status_bar_project_thread.aborted = True
			self.update_status_bar_project_thread.quit()
		self.update_status_bar_project_thread = db_op.db_get_project_statistics(options, self.update_status_bar_project_onFinish, self)
		self.update_status_bar_project_thread.start()
		
	def update_status_bar_project_onFinish(self, project_translated_segments, project_total_segments):
		self.project_statistics_label.setText("Project segments: " + str(project_translated_segments) + "/" + str(project_total_segments))
		
	def update_status_bar_file(self):
		options = {}
		options['project_path'] = self.project_path
		options['filename'] = self.filename
		if hasattr(self, 'update_status_bar_file_thread'):
			self.update_status_bar_file_thread.aborted = True
			self.update_status_bar_file_thread.quit()
		self.update_status_bar_file_thread = db_op.db_get_file_statistics(options, self.update_status_bar_file_onFinish, self)
		self.update_status_bar_file_thread.start()
		
	def update_status_bar_file_onFinish(self, file_translated_segments, file_total_segments):
		self.file_statistics_label.setText("File segments: " + str(file_translated_segments) + "/" + str(file_total_segments))
	
	def save_current_file(self):
		#current_row = self.main_widget.main_editor.currentRow()
		#if current_row >= 0 and self.main_widget.target_text.toPlainText() != '':
		#	db_op.save_variant(self, self.main_widget.target_text.toPlainText(), self.target_language, self.main_widget.main_editor.item(current_row, 0).text(), self.filename)
		#	self.main_widget.main_editor.item(current_row, 2).setText(self.main_widget.target_text.toPlainText())
		self.main_editor_currentCellChanged(self.main_widget.main_editor.currentRow(), 1,self.main_widget.main_editor.currentRow(), 1 )
			
	def close_current_project(self):
		#Save current file
		if self.filename:
			self.save_current_file()
	
		#Clear the controls
		self.main_widget.main_editor.setRowCount(0)
		self.main_widget.source_text.setText('')
		self.main_widget.target_text.setText('')
		#self.main_widget.main_h_splitter.setEnabled(False)
		if self.recent_files is not None:
			self.build_menu(list(dict.fromkeys(self.recent_files))[:10], False)
		else:
			self.build_menu(None, False)
		
		self.reset_globals()
		
		self.main_widget.main_editor_groupbox.setTitle("[No file]")
		self.setWindowTitle('BlackCAT')
	
	def call_file_picker(self):
		if self.valid_files:
			dialog = dialogs.file_picker_dialog(self.valid_files)
		
			#Open the chosen file for edition
			if dialog.exec_():
				self.open_file_for_translation(dialog.file_list.currentItem().text())
		else:
			error_message_box = QtWidgets.QMessageBox()
			error_message_box.setText("No valid source files were found. Please copy some supported files in the source_files directory of the project and try opening it again.")
			error_message_box.setIcon(QtWidgets.QMessageBox.Critical)
			error_message_box.exec_()
	
	def import_file_into_project(self, file_path, m_time):
		text_processor_options = {}
		text_processor_options['project_path'] = self.project_path
		text_processor_options['file_path'] = file_path
		text_processor_options['source_language'] = self.source_language
		text_processor_options['target_language'] = self.target_language
		text_processor_options['m_time'] = m_time
	
		#first check file type
		file_extension = os.path.splitext(file_path)[1]
		
		if file_extension == ".txt":
			text_processors.punkt.import_file(text_processor_options)
		elif file_extension == ".odt":
			text_processors.odt.import_file(text_processor_options)
		elif file_extension == ".sgml":
			text_processors.sgml.import_file(text_processor_options)
		elif file_extension == ".po":
			text_processors.gettext.import_file(text_processor_options)
		else:
			print("Unsupported file with extension " + file_extension)
		
	def open_file_for_translation(self, filename):
		self.main_widget.main_h_splitter.setEnabled(False)
		if filename != self.filename:
			self.status_label.setText("Openning file: " + filename)
			
			#Clear the controls
			self.main_widget.main_editor.setRowCount(0)
			self.main_widget.source_text.setText('')
			self.main_widget.target_text.setText('')
			
			options = {}
			options['filename'] = filename
			options['project_path'] = self.project_path
			options['source_language'] = self.source_language
			options['target_language'] = self.target_language
			self.open_file_thread = db_op.db_open_file_thread(options, self.open_file_onFinish, self)
			self.open_file_thread.start()	
		
	def open_file_onFinish(self, filename, result):
		self.main_widget.main_editor.setRowCount(len(result))
		self.max_plurals_in_file = 0
		plurals_offset = 0
		# row [0]=id, [1]=source text, [2]=target text, [3]=fuzzy flag, [4]=plural index, [5]=plural form
		for index, row in enumerate(result):
			if row[4]==0 or row[4] is None:
				row_id = QtWidgets.QTableWidgetItem(str(row[0]))
				row_source = QtWidgets.QTableWidgetItem(row[1])
				row_target = QtWidgets.QTableWidgetItem(row[2])
				if(row[2]=="" or row[2] is None):
					row_id.setBackground(QtGui.QColor(255, 0, 0))
				else:
					if(row[3]==1):
						row_id.setBackground(QtGui.QColor(255, 255, 0))
					else:
						row_id.setBackground(QtGui.QColor(0, 255, 0))
				row_source.setTextAlignment(QtCore.Qt.AlignTop)
				row_target.setTextAlignment(QtCore.Qt.AlignTop)
				self.main_widget.main_editor.setItem(index - plurals_offset, 0, row_id)
				self.main_widget.main_editor.setItem(index - plurals_offset, 1, row_source)
				self.main_widget.main_editor.setItem(index - plurals_offset, 2, row_target)
				self.status_label.setText("Openning file: " + filename + " (loading segment " + str(index + 1) + " of " + str(len(result)) + ")" )
				QtWidgets.QApplication.processEvents()
			else:
				if row[4] > self.max_plurals_in_file:
					self.max_plurals_in_file = row[4]
				self.plurals[row[1], row[4]] = [row[2], row[3], row[5]]
				plurals_offset = plurals_offset + 1
		
		self.main_widget.main_editor.setRowCount(len(result) - plurals_offset)
	
		self.filename = filename
		self.previous_translated_text = ''
		self.main_widget.main_editor_groupbox.setTitle(filename)
		
		self.main_widget.main_h_splitter.setEnabled(True)
		self.status_label.setText("Ready.")
		self.main_widget.target_text.setFocus()
		
		self.update_status_bar_file()
		
	def generate_translated_files(self):
		#Check the items in source_file dir
		source_file_dir = os.listdir(os.path.join(self.project_dir, 'source_files'))
		options = {}
		options['project_dir'] = self.project_dir
		options['project_path'] = self.project_path
		options['source_language'] = self.source_language
		options['target_language'] = self.target_language
		options['source_file_dir'] = source_file_dir
		if source_file_dir:
			generate_thread = generate_translated_files_thread(options, self.generate_translated_file_on_progress, self.generate_translated_files_on_finish, self)
			self.status_msgbox = dialogs.status_dialog("Generate translated files", "Generating files...")
			generate_thread.start()
			self.status_msgbox.exec_()
			
		else:
			error_message_box = QtWidgets.QMessageBox()
			error_message_box.setText("No valid source files were found. Please copy some supported files in the source_files directory of the project and try opening it again.")
			error_message_box.setIcon(QtWidgets.QMessageBox.Critical)
			error_message_box.exec_()

	def generate_translated_file_on_progress(self, message):
		self.status_msgbox.add_text(message)
	
	def generate_translated_files_on_finish(self):
		self.status_msgbox.tasks_completed()
		
	def import_tm(self):
		tm_file_name_list = QtWidgets.QFileDialog.getOpenFileNames(self, 'Import translation memory files', '', 'Any Supported File (*.tmx, *.po);;Translation Memory eXchange (*.tmx);;PO files (*.po)')[0]
		import_options = {}
		import_options['tm_file_name_list'] = tm_file_name_list
		import_options['project_path'] = self.project_path
		import_options['source_language'] = self.source_language
		import_options['target_language'] = self.target_language
		
		import_tm_thread = db_op.db_import_tm_thread(import_options, self.import_tm_onFinish, self)
		import_tm_thread.start()
			
	def import_tm_onFinish(self, imported_files):
		message = "Imported files: " + str(len(imported_files))
		for file in imported_files:
			message = message + "\n- " + file
		info_box = QtWidgets.QMessageBox()
		info_box.setText(message)
		info_box.setIcon(QtWidgets.QMessageBox.Information)
		info_box.exec_()
		
	def show_about_dialog(self):
		about_text = "BlackCAT 1.0 (beta)\n\n"
		about_text = about_text + "This is a work in progress.\n"
		about_text = about_text + "That includes this about dialog.\n\n"
		about_text = about_text + 'contact: carloswaldo@babelruins.org'
		QtWidgets.QMessageBox.about(self, "About BlackCAT 1.0 (beta)", about_text)
		
	def closeEvent(self, event):
		#Let's save the current dimensions before closing
		settings = QtCore.QSettings("Babelruins.org", "BlackCAT")
		settings.setValue('maximized', self.isMaximized())
		settings.setValue('width', self.width())
		settings.setValue('height', self.height())
		settings.setValue('x_position', self.x())
		settings.setValue('y_position', self.y())
		settings.setValue('editor_splitter_settings', self.main_widget.editor_v_splitter.saveState())
		settings.setValue('main_splitter_settings', self.main_widget.main_h_splitter.saveState())
		settings.setValue('plugins_splitter_settings', self.main_widget.plugins_v_splitter.saveState())
		settings.setValue('number_of_loaded_plugins', len(self.list_of_loaded_plugin_widgets))
		if self.recent_files is not None:
			settings.setValue('recent_files', list(dict.fromkeys(self.recent_files[::-1]))[:10])
		del settings
		
		#Save current file
		if self.filename:
			self.save_current_file()