from PyQt5 import QtWidgets, QtCore
from core import db_op
import pycountry, os

class file_picker_dialog(QtWidgets.QDialog):
	def __init__(self, files_in_dir):
		super(file_picker_dialog, self).__init__()
		
		self.setWindowTitle("Pick a file for translation")
		self.setWindowFlags(QtCore.Qt.WindowTitleHint)
		self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint)
		
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