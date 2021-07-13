import sqlite3, os, polib
from sqlite3.dbapi2 import OperationalError
from PyQt5 import QtCore
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

def create_project_db(tm_path):
	project_db = sqlite3.connect(tm_path)
	project_cursor = project_db.cursor()
	#project_cursor.execute("""	CREATE TABLE source_files(
	#								name TEXT PRIMARY KEY,
	#								proc_algorithm TEXT NOT NULL,
	#								m_time INTEGER NOT NULL,
	#								encoding TEXT);""")
									
	project_cursor.execute("""	CREATE TABLE source_segments(
									segment_id INTEGER PRIMARY KEY,
									segment TEXT NOT NULL,
									language TEXT NOT NULL,
									source_file TEXT,
									FOREIGN KEY(source_file) REFERENCES source_files(name),
									UNIQUE(segment, language, source_file) ON CONFLICT IGNORE);""")

	project_cursor.execute("""	CREATE TABLE variants(
									variant_id INTEGER PRIMARY KEY,
									segment TEXT NOT NULL,
									language TEXT NOT NULL,
									source_segment INTEGER NOT NULL,
									FOREIGN KEY(source_segment) REFERENCES source_segments(segment_id),
									UNIQUE(language, source_segment) ON CONFLICT FAIL);""")
	
	project_db.commit()
	project_db.close()

def verify_tm(tm_path):
	project_db = sqlite3.connect(tm_path)
	project_cursor = project_db.cursor()
	try:
		project_cursor.execute(""" SELECT variants.variant_id, variants.segment, variants.language, variants.source_segment,
									source_segments.segment_id, source_segments.segment, source_segments.language, source_segments.source_file
								FROM variants
								JOIN source_segments ON variants.source_segment = source_segments.segment_id
								LIMIT 1;""")
	except OperationalError:
		return False
	project_cursor.close()
	return True

#Obsolete
def save_variant(self, segment, language, source_segment, source_file):
	project_db = sqlite3.connect(self.project_path)
	project_cursor = project_db.cursor()
	project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment, source_file) VALUES(?, ?, ?, ?);", (segment, language, source_segment, source_file))
	project_db.commit()
	project_db.close()
	self.main_status_bar.showMessage("Segment #" + str(source_segment) + " saved.", 3000)

#Returns a dictionary where the key is a segment, and the value is a list containing the translation and the fuzzy flag
def get_segments_in_db(project_path, source_language, target_language, filename):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	segments_in_db = {}
	for row in project_cursor.execute("""	SELECT source_segments.segment, variants.segment, variants.fuzzy
											FROM source_segments
											LEFT OUTER JOIN variants ON (variants.source_segment = source_segments.segment_id AND variants.language = ? AND variants.source_file = ?)
											WHERE source_segments.language = ?
											AND source_segments.source_file = ?
											AND variants.plural_index = 0;""", (target_language, filename, source_language, filename)):
		segments_in_db[row[0]] = [row[1], row[2]]
	project_db.close()
	return segments_in_db
	
def get_translated_segment(project_path, source_language, target_language, filename, source_segment, plural_index=0):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	segments_in_db = {}
	row = project_cursor.execute("""	SELECT source_segments.segment, variants.segment, variants.fuzzy
											FROM source_segments
											LEFT OUTER JOIN variants ON (variants.source_segment = source_segments.segment_id AND variants.language = ? AND variants.source_file = ?)
											WHERE source_segments.language = ?
											AND source_segments.source_file = ?
											AND source_segments.segment = ?
											AND variants.plural_index = ?;""", (target_language, filename, source_language, filename, source_segment, plural_index)).fetchone()
	project_db.close()
	return row
	
#Returns a dictionary where the key is a segment and its translation's plural_index, and the value is a list containing the translation and the fuzzy flag
def get_segments_with_plurals_in_db(project_path, source_language, target_language, filename):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	segments_in_db = {}
	for row in project_cursor.execute("""	SELECT source_segments.segment, variants.plural_index, variants.segment, variants.fuzzy
											FROM source_segments
											LEFT OUTER JOIN variants ON (variants.source_segment = source_segments.segment_id AND variants.language = ? AND variants.source_file = ?)
											WHERE source_segments.language = ?
											AND source_segments.source_file = ?;""", (target_language, filename, source_language, filename)):
		segments_in_db[row[0], row[1]] = [row[2], row[3]]
	project_db.close()
	return segments_in_db
	
#Returns a dictionary of the source segments already imported in the db for 'filename'
def get_source_segments_in_db(project_path, source_language, filename):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	imported_segments = {}
	for row in project_cursor.execute("""	SELECT source_segments.segment_id, source_segments.segment
											FROM source_segments
											WHERE source_segments.source_file = ?
											AND source_segments.language = ?""", (filename, source_language)):
		imported_segments[row[1]] = row[0]
	project_db.close()
	return imported_segments
	
def recycle_segment(project_path, segment_id):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	#If it doesn't have any translation, delete it
	project_cursor.execute("""	DELETE
								FROM source_segments
								WHERE segment_id IN (
									SELECT source_segments.segment_id
									FROM source_segments
									LEFT JOIN variants
									ON variants.source_segment = source_segments.segment_id
									WHERE variants.variant_id IS NULL
									AND source_segments.segment_id = ?)""", (segment_id, ))

	#If it does have a translation, keep it as translation memory
	project_cursor.execute("""	UPDATE source_segments
								SET source_file = 'tm:' || source_file
								WHERE segment_id = ?""", (segment_id, ))
									
	project_cursor.execute("""	UPDATE variants
								SET source_file = 'tm:' || source_file
								WHERE source_segment = ?""", (segment_id, ))
	project_db.commit()
	project_db.close()
								
def import_source_file(project_path, filename, proc_algorithm, m_time, encoding=''):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	project_cursor.execute("INSERT OR REPLACE INTO source_files (name, proc_algorithm, m_time, encoding) VALUES(?, ?, ?, ?);", (filename, proc_algorithm, m_time, encoding))
	project_db.commit()
	project_db.close()

def get_encoding(project_path, filename):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	encoding = project_cursor.execute("SELECT encoding FROM source_files WHERE name = ?", (filename, )).fetchone()[0]
	project_db.close()
	return encoding
	
def get_setting(project_path, key):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	value = project_cursor.execute("SELECT value FROM project_settings WHERE key = ?", (key, )).fetchone()[0]
	project_db.close()
	return value

#Returns a dictionary of the files at source_files that were already imported to the project with their algorithm
def get_imported_files(project_path):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	files_already_imported = {}
	for row in project_cursor.execute("SELECT name, proc_algorithm FROM source_files;"):
		files_already_imported[row[0]] = row[1]
	project_db.close()
	return files_already_imported
	
#Returns a dictionary of the files at source_files that were already imported to the project with their details
def get_imported_files_details(project_path):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	files_already_imported = {}
	for row in project_cursor.execute("SELECT name, proc_algorithm, m_time, encoding FROM source_files ORDER BY name;"):
		files_already_imported[row[0]] = [row[1], row[2], row[3]]
	project_db.close()
	return files_already_imported
	
def import_source_segment(project_path, segment, source_language, filename, index, plural="", previous=""):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	project_cursor.execute("INSERT INTO source_segments (segment, language, plural, source_file) VALUES(?, ?, ?, ?);", (segment, source_language, plural, filename))
	project_cursor.execute("UPDATE source_segments SET source_file_index = ? WHERE segment = ? AND language = ? AND source_file = ?;", (index, segment, source_language, filename))
	if plural != "":
		project_cursor.execute("UPDATE source_segments SET plural = ? WHERE segment = ? AND language = ? AND source_file = ?;", (plural, segment, source_language, filename))
	if previous != "":
		project_cursor.execute("UPDATE source_segments SET previous = ? WHERE segment = ? AND language = ? AND source_file = ?;", (previous, segment, source_language, filename))
	project_db.commit()
	project_db.close()

def import_variant(project_path, variant, target_language, fuzzy, filename, segment, plural_index=0):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	#We need REPLACE for gettext where there could already be translated segements
	project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, fuzzy, source_segment, source_file, plural_index) SELECT ?, ?, ?, source_segments.segment_id, ?, ? FROM source_segments WHERE segment = ?;", (variant, target_language, fuzzy, filename, plural_index, segment))
	project_db.commit()
	project_db.close()

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

def get_source_segments_from_translation_memory(tm_path):
	project_db = sqlite3.connect(tm_path)
	project_cursor = project_db.cursor()
	try:
		project_cursor.execute("""	SELECT MIN(source_segments.segment_id), source_segments.segment
										FROM source_segments
										JOIN variants ON variants.source_segment = source_segments.segment_id
										GROUP BY source_segments.segment""")
	except OperationalError:
		return None
	result = dict(project_cursor.fetchall())
	project_db.close()
	return result

def get_translation_memory(tm_path, source_segments, target_language, source_text, ratio_limit):
	project_db = sqlite3.connect(tm_path)
	project_cursor = project_db.cursor()
	matching_segments = {}
	for segment in source_segments:
		ratio = fuzz.ratio(source_text, source_segments[segment])
		if ratio >= ratio_limit:
			matching_segments[segment] = ratio
	
	result = []
	for list_of_arguments in chunks(list(matching_segments.keys()), 800):
		placeholder = '?'
		placeholders = ', '.join(placeholder for x in list_of_arguments)
		query = """	SELECT source_segments.segment_id, source_segments.segment, MIN(variants.segment)
					FROM variants
					JOIN source_segments ON variants.source_segment = source_segments.segment_id
					WHERE source_segments.segment_id IN ({})
					AND variants.language = ?
					GROUP BY source_segments.segment_id, source_segments.segment;""".format(placeholders)
		list_of_arguments.append(target_language)
		
		for row in project_cursor.execute(query, list_of_arguments):
			result.append((matching_segments[row[0]], row[1], row[2]))
	
	result.sort(reverse=True)

	project_db.close()
	return result

def save_file_as_tm(project_path, filename):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	#Get rid of segments with no translation
	project_cursor.execute("""	DELETE
								FROM source_segments
								WHERE segment_id IN (
									SELECT source_segments.segment_id
									FROM source_segments
									LEFT JOIN variants
									ON variants.source_segment = source_segments.segment_id
									WHERE variants.variant_id IS NULL
									AND source_segments.source_file = ?)""", (filename, ))

	#For the rest of the segments, keep them as translation memory
	project_cursor.execute("""	UPDATE source_segments
								SET source_file = 'tm:' || source_file
								WHERE segment_id IN (
									SELECT source_segments.segment_id
									FROM source_segments
									LEFT JOIN variants
									ON variants.source_segment = source_segments.segment_id
									WHERE variants.variant_id IS NOT NULL
									AND source_segments.source_file = ?)""", (filename, ))
									
	project_cursor.execute("""	UPDATE variants
								SET source_file = 'tm:' || source_file
								WHERE source_segment IN (
									SELECT source_segments.segment_id
									FROM source_segments
									LEFT JOIN variants
									ON variants.source_segment = source_segments.segment_id
									WHERE variants.variant_id IS NOT NULL
									AND source_segments.source_file = ?)""", (filename, ))
	
	#Delete reference to the deleted file from the db
	project_cursor.execute("DELETE FROM source_files WHERE name = ?", (filename, ) )
	project_db.commit()
	project_db.close()
	
def import_tm(tm_path, files):
	project_db = sqlite3.connect(tm_path)
	project_cursor = project_db.cursor()
	imported_files = []
		
	for item in files:
		tm_file_name = os.path.abspath(item)
		file_extension = os.path.splitext(tm_file_name)[1]
		
		if file_extension == ".tmx":
			tm_file = open(tm_file_name, 'r', encoding='utf8')
			soup = BeautifulSoup(tm_file.read(), 'xml')
			for tu in soup.find_all('tu'):
				first_tuv = True
				for tuv in tu.find_all('tuv'):
					if tuv['xml:lang'] and tuv.seg.string is not None:
						lang = tuv['xml:lang']
						lang_code = (lang[:lang.index('-')] if '-' in lang else lang).lower()
						if first_tuv:
							project_cursor.execute("INSERT OR REPLACE INTO source_segments (segment, language, source_file) VALUES(?, ?, ?);", (tuv.seg.string, lang_code, "tm:" + tm_file_name))
							source_segment_id = project_cursor.lastrowid
						else:
							project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment, source_file) VALUES(?, ?, ?, ?);", (tuv.seg.string, lang_code, source_segment_id, "tm:" + tm_file_name))
						first_tuv = False
			imported_files.append(item)
			project_db.commit()
		elif file_extension == ".po":
			po = polib.pofile(tm_file_name)
			for entry in po.translated_entries():
				project_cursor.execute("INSERT OR REPLACE INTO source_segments (segment, language, source_file) VALUES(?, ?, ?);", (entry.msgid, 'en', os.path.basename(tm_file_name)))
				source_segment_id = project_cursor.lastrowid
				project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment) VALUES(?, ?, ?);", (entry.msgstr, po.metadata['Language'], source_segment_id))
			imported_files.append(item)
			project_db.commit()
	
	project_db.close()
	
	return imported_files

class db_save_variant_thread(QtCore.QThread):
	finished = QtCore.pyqtSignal(object)
	
	def __init__(self, options, finished_callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.finished.connect(finished_callback)
		#print("init -> ", self.options)
		
	def run(self):
		print("run -> ", self.options)
		project_db = sqlite3.connect(self.options['project_path'])
		project_cursor = project_db.cursor()
		project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment, source_file, fuzzy, plural_index) VALUES(?, ?, ?, ?, ?, ?);", (self.options['segment'], self.options['target_language'], self.options['source_segment'], self.options['source_file'], self.options['fuzzy'], self.options['plural_index']))
		project_db.commit()
		project_db.close()
		self.finished.emit(self.options['source_segment'])
	
class db_open_file_thread(QtCore.QThread):
	finished = QtCore.pyqtSignal(object, object)
	
	def __init__(self, options, finished_callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.finished.connect(finished_callback)
	
	def run(self):
		project_db = sqlite3.connect(self.options['project_path'])
		project_cursor = project_db.cursor()
		result = []
		for row in project_cursor.execute("""	SELECT source_segments.segment_id, source_segments.segment, variants.segment, variants.fuzzy, variants.plural_index, source_segments.plural, source_segments.previous
												FROM source_segments
												LEFT OUTER JOIN variants ON ((variants.source_segment = source_segments.segment_id) 
													AND (variants.language = ?) AND (variants.source_file = ?))
												WHERE source_segments.source_file = ?
												AND source_segments.language = ?
												ORDER BY source_segments.source_file_index""", (self.options['target_language'], self.options['filename'], self.options['filename'], self.options['source_language'])):
			result.append(row)
		project_db.close()
		self.finished.emit(self.options['filename'], result)
		
class db_get_project_statistics(QtCore.QThread):
	finished = QtCore.pyqtSignal(object, object)
	
	def __init__(self, options, finished_callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.finished.connect(finished_callback)
		self.aborted = False
	
	def run(self):
		project_db = sqlite3.connect(self.options['project_path'])
		project_cursor = project_db.cursor()
		project_cursor.execute("""	SELECT count(source_segments.segment_id)
									FROM source_segments
									JOIN variants ON variants.source_segment = source_segments.segment_id
									WHERE source_segments.source_file IN (SELECT source_files.name FROM source_files)
									AND variants.fuzzy = 0;""")
		project_transtaled_segments = project_cursor.fetchone()[0]
		project_cursor.execute("""	SELECT count(source_segments.segment_id)
									FROM source_segments
									WHERE source_segments.source_file IN (SELECT source_files.name FROM source_files);""")
		project_total_segments = project_cursor.fetchone()[0]
		project_db.close()
		
		if not self.aborted:
			self.finished.emit(project_transtaled_segments, project_total_segments)
			
class db_get_file_statistics(QtCore.QThread):
	finished = QtCore.pyqtSignal(object, object)
	
	def __init__(self, options, finished_callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.finished.connect(finished_callback)
		self.aborted = False
	
	def run(self):
		try:
			project_db = sqlite3.connect(self.options['project_path'])
			project_cursor = project_db.cursor()
			project_cursor.execute("""	SELECT count(DISTINCT source_segments.segment_id)
										FROM source_segments
										JOIN variants ON variants.source_segment = source_segments.segment_id
										WHERE source_segments.source_file = ?
										AND variants.plural_index = 0
										AND variants.fuzzy = 0;""", (self.options['filename'], ))
			file_transtaled_segments = project_cursor.fetchone()[0]
			project_cursor.execute("""	SELECT count(source_segments.segment_id)
										FROM source_segments
										WHERE source_segments.source_file = ?;""", (self.options['filename'], ))
			file_total_segments = project_cursor.fetchone()[0]
			project_db.close()
			if not self.aborted:
				self.finished.emit(file_transtaled_segments, file_total_segments)
		except sqlite3.OperationalError:
			self.finished.emit("-", "-")
		
class db_import_tm_thread(QtCore.QThread):
	finished = QtCore.pyqtSignal(object)
	
	def __init__(self, options, finished_callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.finished.connect(finished_callback)
		self.imported_files = []
	
	def run(self):
		project_db = sqlite3.connect(self.options['project_path'])
		project_cursor = project_db.cursor()
			
		for item in self.options['tm_file_name_list']:
			tm_file_name = os.path.abspath(item)
			file_extension = os.path.splitext(tm_file_name)[1]
			
			if file_extension == ".tmx":
				tm_file = open(tm_file_name, 'r', encoding='utf8')
				soup = BeautifulSoup(tm_file.read(), 'xml')
				for tu in soup.find_all('tu'):
					first_tuv = True
					for tuv in tu.find_all('tuv'):
						if tuv['xml:lang'] and tuv.seg.string is not None:
							lang = tuv['xml:lang']
							lang_code = (lang[:lang.index('-')] if '-' in lang else lang).lower()
							if first_tuv:
								project_cursor.execute("INSERT OR REPLACE INTO source_segments (segment, language, source_file) VALUES(?, ?, ?);", (tuv.seg.string, lang_code, "tm:" + tm_file_name))
								source_segment_id = project_cursor.lastrowid
							else:
								project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment, source_file) VALUES(?, ?, ?, ?);", (tuv.seg.string, lang_code, source_segment_id, "tm:" + tm_file_name))
							first_tuv = False
				self.imported_files.append(item)
				project_db.commit()
			elif file_extension == ".po":
				po = polib.pofile(tm_file_name)
				for entry in po.translated_entries():
					project_cursor.execute("INSERT OR REPLACE INTO source_segments (segment, language, source_file) VALUES(?, ?, ?);", (entry.msgid, self.options['source_language'], "tm:" + tm_file_name))
					source_segment_id = project_cursor.lastrowid
					project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment, source_file) VALUES(?, ?, ?, ?);", (entry.msgstr, self.options['target_language'], source_segment_id, "tm:" + tm_file_name))
				self.imported_files.append(item)
				project_db.commit()
		
		project_db.close()
		
		self.finished.emit(self.imported_files)
		
#Is this the right way to work with QThreads?
class db_worker(QtCore.QObject):
	start = QtCore.pyqtSignal(object)
	finished = QtCore.pyqtSignal(object)
	
	def __init__(self):
		super(db_worker, self).__init__()
		self.start.connect(self.run, QtCore.Qt.QueuedConnection)
		#self.start.connect(self.run)
		#self.start.connect(self.run, QtCore.Qt.BlockingQueuedConnection)
		self.mutex = QtCore.QMutex()
	
	@QtCore.pyqtSlot(object)
	def run(self, options):
		self.mutex.lock()
		#print("db_worker.run() -> ", options)
		if options['action'] == 'save_variant':
			project_db = sqlite3.connect(options['project_path'])
			project_cursor = project_db.cursor()
			project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment, source_file, fuzzy, plural_index) VALUES(?, ?, ?, ?, ?, ?);", (options['segment'], options['target_language'], options['source_segment_id'], options['source_file'], options['fuzzy'], options['plural_index']))
			project_db.commit()
			project_db.close()
			self.finished.emit(options)
		if options['action'] == 'save_po_entry':
			po_file = options['po_file']
			entry_to_save = po_file.find(options['source_text'])
			if entry_to_save.msgstr:
				entry_to_save.msgstr = options['target_text']
			if options['fuzzy_checked'] and ('fuzzy' not in entry_to_save.flags):
				entry_to_save.flags.append('fuzzy')
			elif not options['fuzzy_checked'] and ('fuzzy' in entry_to_save.flags):
				entry_to_save.flags.remove('fuzzy')
		self.mutex.unlock()