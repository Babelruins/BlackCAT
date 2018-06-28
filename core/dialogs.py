from PyQt5 import QtWidgets, QtCore, QtGui
from core import db_op
import pycountry, os, datetime

class file_picker_dialog(QtWidgets.QDialog):
	def __init__(self, files_in_dir):
		super(file_picker_dialog, self).__init__()
		
		self.setWindowTitle("Pick a file for translation")
		self.setWindowFlags(QtCore.Qt.WindowTitleHint)
		self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint)
		self.setWindowIcon(QtGui.QIcon('whitecat_256x256.png'))
		
		layout = QtWidgets.QVBoxLayout(self)
		layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
		self.file_list = QtWidgets.QListWidget()
		
		for file in files_in_dir:
			self.file_list.addItem(QtWidgets.QListWidgetItem(file))
		accept_button = QtWidgets.QPushButton('Open', self)
		accept_button.clicked.connect(self.accept)
		
		layout.addWidget(self.file_list)
		layout.addWidget(accept_button)
		
		self.file_list.setCurrentRow(0)
		
	def closeEvent(self, event):
		self.accept()
		
class new_project_dialog(QtWidgets.QDialog):
	def __init__(self):
		super(new_project_dialog, self).__init__()
		
		language_dictionary = {}
		for language in pycountry.languages:
			if hasattr(language, 'alpha_2'):
				language_dictionary[language.alpha_2] = language.name
		
		self.setWindowTitle("New project")
		self.setWindowFlags(QtCore.Qt.WindowTitleHint)
		self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint)
		self.setWindowIcon(QtGui.QIcon('whitecat_256x256.png'))
		
		form_layout = QtWidgets.QFormLayout(self)
		form_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
		
		name_label = QtWidgets.QLabel("Name:")
		self.name_input = QtWidgets.QLineEdit()
		form_layout.addRow(name_label, self.name_input)
		
		location_label = QtWidgets.QLabel("Location:")
		self.location_input = QtWidgets.QLineEdit()
		location_button = QtWidgets.QPushButton("...")
		location_button.clicked.connect(self.show_directory_dialog)
		location_layout = QtWidgets.QHBoxLayout()
		location_layout.addWidget(self.location_input)
		location_layout.addWidget(location_button)
		form_layout.addRow(location_label, location_layout)
		
		source_label = QtWidgets.QLabel("Source language: ")
		self.source_input = QtWidgets.QComboBox()
		for lang_id, lang_name in language_dictionary.items():
			self.source_input.addItem(lang_name, lang_id)
		form_layout.addRow(source_label, self.source_input)
		
		target_label = QtWidgets.QLabel("Target language: ")
		self.target_input = QtWidgets.QComboBox()
		for lang_id, lang_name in language_dictionary.items():
			self.target_input.addItem(lang_name, lang_id)
		form_layout.addRow(target_label, self.target_input)
		
		accept_button = QtWidgets.QPushButton("Accept")
		cancel_button = QtWidgets.QPushButton("Cancel")
		accept_button.clicked.connect(self.create_project)
		cancel_button.clicked.connect(self.close)
		buttons_layout = QtWidgets.QHBoxLayout()
		buttons_layout.addWidget(accept_button)
		buttons_layout.addWidget(cancel_button)
		form_layout.addRow(buttons_layout)
	
	def show_directory_dialog(self):
		self.location_input.setText(os.path.abspath(QtWidgets.QFileDialog.getExistingDirectory(self, "Select location for project directory")))
	
	def create_project(self):
		try:
			project_name = self.name_input.text()
			project_path = os.path.join(self.location_input.text(), project_name)
			source_language = self.source_input.itemData(self.source_input.currentIndex())
			target_language = self.target_input.itemData(self.target_input.currentIndex())
			
			if not os.path.exists(project_path):
				os.makedirs(project_path)
				os.makedirs(os.path.join(project_path, "source_files"))
				os.makedirs(os.path.join(project_path, "processed_files"))
				
				db_op.create_project_db(self, os.path.join(project_path, project_name + ".blc"), source_language, target_language)
				
				info_message_box = QtWidgets.QMessageBox()
				info_message_box.setText("Project created successfully, please add files to the source_files directory and hit OK to open the project.")
				info_message_box.setIcon(QtWidgets.QMessageBox.Information)
				info_message_box.exec_()
				
				self.accept()
			else:
				error_message_box = QtWidgets.QMessageBox()
				error_message_box.setText("Error: directory '" + project_path + "' already exists.")
				error_message_box.setIcon(QtWidgets.QMessageBox.Warning)
				error_message_box.exec_()
		except Exception as e:
			error_message_box = QtWidgets.QMessageBox()
			error_message_box.setText("The following error ocurred while trying to create the project directory: " + str(e))
			error_message_box.setIcon(QtWidgets.QMessageBox.Warning)
			error_message_box.exec_()

class status_dialog(QtWidgets.QDialog):
	def __init__(self, title, message):
		super(status_dialog, self).__init__()
		
		self.setWindowTitle(title)
		self.setWindowFlags(QtCore.Qt.WindowTitleHint)
		self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint)
		self.setWindowIcon(QtGui.QIcon('whitecat_256x256.png'))
		
		layout = QtWidgets.QVBoxLayout(self)
		layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
		
		self.main_message = QtWidgets.QLabel(message)
		self.progress_bar = QtWidgets.QProgressBar()
		self.progress_bar.setRange(0,0)
		self.progress_bar.setMinimumWidth(350)
		self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
		self.textbox = QtWidgets.QTextEdit()
		self.textbox.setReadOnly(True)
		self.accept_button = QtWidgets.QPushButton("Close")
		self.accept_button.clicked.connect(self.close)
		self.accept_button.setEnabled(False)
		
		layout.addWidget(self.main_message)
		layout.addWidget(self.progress_bar)
		layout.addWidget(self.textbox)
		layout.addWidget(self.accept_button)
	
	def add_text(self, text):
		self.textbox.append(text)

	def tasks_completed(self):
		self.add_text("Done.")
		self.progress_bar.setRange(0,1)
		self.progress_bar.setValue(1)
		self.accept_button.setEnabled(True)

class import_files_dialog(QtWidgets.QDialog):

	def __init__(self, options, file_background_worker):
		super(import_files_dialog, self).__init__()
		
		self.options = options
		self.file_background_worker = file_background_worker
		
		self.setWindowTitle("Import files into project")
		self.setWindowFlags(QtCore.Qt.WindowTitleHint)
		self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint)
		self.setWindowIcon(QtGui.QIcon('whitecat_256x256.png'))
		self.setMinimumSize(800, 600)
		
		layout = QtWidgets.QGridLayout(self)
		layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
		
		self.file_list_table = QtWidgets.QTableWidget(self)
		self.file_list_table.setMinimumHeight(400)
		self.file_list_table.setMaximumHeight(400)
		self.file_list_table.setColumnCount(7)
		self.file_list_table.setHorizontalHeaderLabels(["Status", "File name", "Encoding", "Algorithm", "Previous modification", "Last modification", "mtime"])
		self.file_list_table.verticalHeader().hide()
		self.file_list_table.setAlternatingRowColors(True)
		self.file_list_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
		self.file_list_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.file_list_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		#self.file_list_table.cellClicked.connect(self.file_list_table_cellClicked)
		self.file_list_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.table_header = self.file_list_table.horizontalHeader()
		self.table_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		self.table_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
		self.table_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
		self.table_header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
		self.table_header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
		self.table_header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
		self.file_list_table.setColumnHidden(6, True)
		self.file_list_table.setEnabled(False)
		#self.file_list_table.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
		
		self.status_group = QtWidgets.QGroupBox("Status")
		self.status_group.setMaximumHeight(200)
		self.status_text = QtWidgets.QTextEdit()
		self.status_text.setReadOnly(True)
		#self.status_text.setMaximumHeight(100)
		self.progress_bar = QtWidgets.QProgressBar()
		self.progress_bar.setRange(0,0)
		self.progress_bar.setMinimumWidth(300)
		self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
		self.status_layout = QtWidgets.QVBoxLayout()
		self.status_layout.addWidget(self.status_text)
		self.status_layout.addWidget(self.progress_bar)
		self.status_group.setLayout(self.status_layout)
		
		self.actions_group = QtWidgets.QGroupBox("Actions")
		self.reimport_checked_button = QtWidgets.QPushButton("(Re-)import checked")
		self.reimport_checked_button.clicked.connect(self.reimport_checked)
		self.reimport_all_button = QtWidgets.QPushButton("(Re-)import everything")
		self.reimport_all_button.clicked.connect(self.reimport_everthing)
		self.close_button = QtWidgets.QPushButton("Close")
		self.close_button.clicked.connect(self.close)
		self.actions_layout = QtWidgets.QVBoxLayout()
		self.actions_layout.addWidget(self.reimport_checked_button)
		self.actions_layout.addWidget(self.reimport_all_button)
		self.actions_layout.addWidget(self.close_button)
		self.actions_group.setLayout(self.actions_layout)
		self.actions_group.setEnabled(False)
		
		layout.addWidget(self.file_list_table, 0, 0, 1, 2)
		layout.addWidget(self.status_group, 1, 0, 1, 1)
		layout.addWidget(self.actions_group, 1, 1, 1, 1)
		
	def update_status(self, text):
		self.status_text.append(text)
		
	def add_to_table(self, status, filename, details, m_time):
		row_position = self.file_list_table.rowCount()
		self.file_list_table.insertRow(row_position)
		checkbox = QtWidgets.QTableWidgetItem()
		status_text = "UNKNOWN"
		if status == 0:
			status_text = "OK"
			checkbox.setCheckState(QtCore.Qt.Unchecked)
		elif status == 1:
			status_text = "Changed"
			checkbox.setCheckState(QtCore.Qt.Checked)
		elif status == 2:
			status_text = "NEW"
			checkbox.setCheckState(QtCore.Qt.Checked)
		checkbox.setText(status_text)
		
		self.file_list_table.setItem(row_position, 0, checkbox)
		self.file_list_table.setItem(row_position, 1, QtWidgets.QTableWidgetItem(filename))
		self.file_list_table.setItem(row_position, 2, QtWidgets.QTableWidgetItem(details[2]))
		self.file_list_table.setItem(row_position, 3, QtWidgets.QTableWidgetItem(details[0]))
		old_mtime = datetime.datetime.fromtimestamp(details[1])
		old_mtime_widget = QtWidgets.QTableWidgetItem(old_mtime.strftime('%Y-%m-%d %H:%M:%S'))
		#old_mtime_widget.setTextAlignment(QtCore.Qt.AlignRight)
		self.file_list_table.setItem(row_position, 4, old_mtime_widget)
		new_mtime = datetime.datetime.fromtimestamp(m_time)
		new_mtime_widget = QtWidgets.QTableWidgetItem(new_mtime.strftime('%Y-%m-%d %H:%M:%S'))
		#new_mtime_widget.setTextAlignment(QtCore.Qt.AlignRight)
		self.file_list_table.setItem(row_position, 5, new_mtime_widget)
		self.file_list_table.setItem(row_position, 6, QtWidgets.QTableWidgetItem(str(m_time)))
	
	def reimport_checked(self):
		self.file_list_table.setEnabled(False)
		self.actions_group.setEnabled(False)
		self.progress_bar.setRange(0,0)
		file_list = {}
		for row in range(self.file_list_table.rowCount()):
			if self.file_list_table.item(row, 0).checkState() == QtCore.Qt.Checked:
				file_list[self.file_list_table.item(row, 1).text()] = self.file_list_table.item(row, 6).text()
		self.file_background_worker.process_file_list.emit(file_list, self.options)
	
	def reimport_everthing(self):
		self.file_list_table.setEnabled(False)
		self.actions_group.setEnabled(False)
		self.progress_bar.setRange(0,0)
		file_list = {}
		for row in range(self.file_list_table.rowCount()):
			file_list[self.file_list_table.item(row, 1).text()] = self.file_list_table.item(row, 6).text()
		self.file_background_worker.process_file_list.emit(file_list, self.options)
	
	#Not used
	def file_list_table_cellClicked(self, row, column):
		if self.file_list_table.item(row, 0).checkState() == QtCore.Qt.Checked:
			self.file_list_table.item(row, 0).setCheckState(QtCore.Qt.Unchecked)
		else:
			self.file_list_table.item(row, 0).setCheckState(QtCore.Qt.Checked)
			
	def update_table(self):
		self.file_list_table.setRowCount(0)
		self.file_background_worker.start.emit(self.options)
		
	def tasks_completed(self):
		self.progress_bar.setRange(0,1)
		self.progress_bar.setValue(1)
		self.file_list_table.setEnabled(True)
		self.actions_group.setEnabled(True)