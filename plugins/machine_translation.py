from PyQt5 import QtWidgets, QtCore, QtGui
from yandex_translate import YandexTranslate
from mstranslator import Translator
from bs4 import BeautifulSoup
import requests

class plugin_thread(QtCore.QThread):
	finished = QtCore.pyqtSignal(object, object)
	
	def __init__(self, options, source, callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.source = source
		
		#Insert your api keys here
		self.mstranslate_key = ''
		self.yandex_key = ''
		
		self.options = options
		self.finished.connect(callback)
		self.aborted = False
	
	def run(self):
		response = ''
		try:
			if self.source == "gtranslateweb":
				user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
				host = 'https://translate.google.com/m'
				headers = {'User-Agent':user_agent,}
			
				params = {'sl': self.options['source_language'], 'tl': self.options['target_language'], 'q': self.options['source_text']}
				html = requests.get(host, params=params, headers=headers)
				soup = BeautifulSoup(html.text, "lxml")
				for div in soup.find_all('div'):
					if div.has_attr('class'):
						if div['class'][0] == 't0':
							response = div.string
			elif self.source == "mstranslator":
				self.translator = Translator(self.mstranslate_key )
				response = self.translator.translate(self.options['source_text'], lang_from=self.options['source_language'], lang_to=self.options['target_language'])
			elif self.source == "yandex":
				self.translator = YandexTranslate(self.yandex_key)
				response = self.translator.translate(self.options['source_text'], self.options['source_language'] + "-" + self.options['target_language'])['text'][0]
		except Exception as e:
			response = '[Error] ' + str(e)
		if not self.aborted:
			self.finished.emit(self.source, response)

class main_widget(QtWidgets.QWidget):
	def __init__(self):
		super(main_widget, self).__init__()
		
		self.name = "Machine Translation"
		
		self.plugin_threads = {}
		
		main_layout = QtWidgets.QGridLayout(self)
		self.mt_table = QtWidgets.QTableWidget()
		self.mt_table.setColumnCount(2)
		self.mt_table.setRowCount(3)
		self.mt_table.setHorizontalHeaderLabels(["Source", "Translation"])
		self.table_header = self.mt_table.horizontalHeader()
		self.table_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
		self.table_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
		self.mt_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
		self.mt_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.mt_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.mt_table.setFont(QtGui.QFont("Lucida Console"))
		self.mt_table.setAlternatingRowColors(True)
		self.mt_table.verticalHeader().hide()
		self.mt_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.mt_table.setItem(0 , 0, QtWidgets.QTableWidgetItem("Google Translate Web"))
		self.mt_table.setItem(1 , 0, QtWidgets.QTableWidgetItem("Microsoft Translator"))
		self.mt_table.setItem(2 , 0, QtWidgets.QTableWidgetItem("Yandex Translate"))
		
		self.mt_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.mt_table.customContextMenuRequested.connect(self.contextMenuEvent)
		
		main_layout.addWidget(self.mt_table, 0, 0)
		
	def contextMenuEvent(self, pos):
		self.target_text = self.parent().parent().main_widget.target_text
	
		self.context_menu = QtWidgets.QMenu()
		insert_translation_action = QtWidgets.QAction("Insert machine translation")
		insert_translation_action.triggered.connect(self.insert_translation)
		replace_translation_action = QtWidgets.QAction("Replace with machine translation")
		replace_translation_action.triggered.connect(self.replace_translation)
		self.context_menu.addAction(insert_translation_action)
		self.context_menu.addAction(replace_translation_action)
		action = self.context_menu.exec_(self.mt_table.viewport().mapToGlobal(pos))
		
	def insert_translation(self):
		self.target_text.setText(self.target_text.toPlainText() + self.mt_table.item(self.mt_table.currentRow(), 1).text())
		
	def replace_translation(self):
		self.target_text.setText(self.mt_table.item(self.mt_table.currentRow(), 1).text())
	
	def main_action(self, options):
		available_sources = ["gtranslateweb", "mstranslator", "yandex"]
		
		for index, source in enumerate(available_sources):
			self.mt_table.setItem(index , 1, QtWidgets.QTableWidgetItem("(Loading...)"))
			if source in self.plugin_threads:
				self.plugin_threads[source].aborted = True
				self.plugin_threads[source].quit()
			self.plugin_threads[source] = plugin_thread(options, source, self.onFinish, self)
			self.plugin_threads[source].start()
	
	def onFinish(self, provider, response):
		if provider == "gtranslateweb":
			self.mt_table.setItem(0 , 1, QtWidgets.QTableWidgetItem(response))
		elif provider == "mstranslator":
			self.mt_table.setItem(1 , 1, QtWidgets.QTableWidgetItem(response))
		elif provider == "yandex":
			self.mt_table.setItem(2 , 1, QtWidgets.QTableWidgetItem(response))