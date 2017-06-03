import sqlite3, os, polib
from PyQt5 import QtCore
from bs4 import BeautifulSoup

def create_project_db(self, project_file_path, source_language, target_language):
	project_db = sqlite3.connect(project_file_path)
	project_cursor = project_db.cursor()
	project_cursor.execute("""	CREATE TABLE source_files(
									name TEXT PRIMARY KEY,
									proc_algorithm TEXT NOT NULL,
									m_time INTEGER NOT NULL,
									encoding TEXT);""")
									
	project_cursor.execute("""	CREATE TABLE source_segments(
									segment_id INTEGER PRIMARY KEY,
									segment TEXT NOT NULL,
									language TEXT NOT NULL,
									source_file TEXT,
									source_file_index BIGINT,
									FOREIGN KEY(source_file) REFERENCES source_files(name),
									UNIQUE(segment, language, source_file) ON CONFLICT IGNORE);""")

	project_cursor.execute("""	CREATE TABLE variants(
									variant_id INTEGER PRIMARY KEY,
									segment TEXT NOT NULL,
									language TEXT NOT NULL,
									fuzzy INTEGER DEFAULT 0,
									creation_id TEXT,
									creation_date TEXT,
									modification_id TEXT,
									modification_date TEXT,
									source_segment INTEGER NOT NULL,
									source_file TEXT,
									external_source TEXT,
									FOREIGN KEY(source_segment) REFERENCES source_segments(segment_id),
									FOREIGN KEY(source_file) REFERENCES source_files(name),
									UNIQUE(language, source_segment, source_file) ON CONFLICT FAIL);""")
									
	project_cursor.execute("""	CREATE TABLE project_settings(
									setting_id INTEGER PRIMARY KEY,
									key TEXT UNIQUE NOT NULL,
									value TEXT);""")
									
	project_cursor.execute("	INSERT INTO project_settings(key, value) VALUES ('source_language', ?)", (source_language, ))
	
	project_cursor.execute("	INSERT INTO project_settings(key, value) VALUES ('target_language', ?)", (target_language, ))
	project_db.commit()
	project_db.close()

def save_variant(self, segment, language, source_segment, source_file):
	project_db = sqlite3.connect(self.project_path)
	project_cursor = project_db.cursor()
	project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment, source_file) VALUES(?, ?, ?, ?);", (segment, language, source_segment, source_file))
	project_db.commit()
	project_db.close()
	self.main_status_bar.showMessage("Segment #" + str(source_segment) + " saved.", 3000)
	
def get_segments_in_db(project_path, source_language, target_language, filename):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	segments_in_db = {}
	for row in project_cursor.execute("""	SELECT source_segments.segment, variants.segment, variants.fuzzy
											FROM source_segments
											LEFT OUTER JOIN variants ON (variants.source_segment = source_segments.segment_id AND variants.language = ? AND variants.source_file = ?)
											WHERE source_segments.language = ?
											AND source_segments.source_file = ?;""", (target_language, filename, source_language, filename)):
		segments_in_db[row[0]] = [row[1], row[2]]
	project_db.close()
	return segments_in_db
	
def get_encoding(self, project_path, filename):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	encoding = project_cursor.execute("SELECT encoding FROM source_files WHERE name = ?", (filename, )).fetchone()[0]
	project_db.close()
	return encoding

#Gets the list of the files at source_files that were already imported to the project
def get_imported_files(project_path):
	project_db = sqlite3.connect(project_path)
	project_cursor = project_db.cursor()
	files_already_imported = {}
	for row in project_cursor.execute("SELECT name, proc_algorithm FROM source_files;"):
		files_already_imported[row[0]] = row[1]
	project_db.close()
	return files_already_imported
	
class db_save_variant_thread(QtCore.QThread):
	finished = QtCore.pyqtSignal(object)
	
	def __init__(self, options, finished_callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.finished.connect(finished_callback)
		
	def run(self):
		project_db = sqlite3.connect(self.options['project_path'])
		project_cursor = project_db.cursor()
		project_cursor.execute("INSERT OR REPLACE INTO variants (segment, language, source_segment, source_file) VALUES(?, ?, ?, ?);", (self.options['segment'], self.options['target_language'], self.options['source_segment'], self.options['source_file']))
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
		for row in project_cursor.execute("""	SELECT source_segments.segment_id, source_segments.segment, variants.segment, variants.fuzzy
												FROM source_segments
												LEFT OUTER JOIN variants ON ((variants.source_segment = source_segments.segment_id) 
													AND (variants.language = ?))
												WHERE source_segments.source_file = ?
												AND source_segments.language = ?
												ORDER BY source_segments.source_file_index""", (self.options['target_language'], self.options['filename'], self.options['source_language'])):
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
									WHERE source_segments.source_file IN (SELECT source_files.name FROM source_files);""")
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
		project_db = sqlite3.connect(self.options['project_path'])
		project_cursor = project_db.cursor()
		project_cursor.execute("""	SELECT count(source_segments.segment_id)
									FROM source_segments
									JOIN variants ON variants.source_segment = source_segments.segment_id
									WHERE source_segments.source_file = ?;""", (self.options['filename'], ))
		file_transtaled_segments = project_cursor.fetchone()[0]
		project_cursor.execute("""	SELECT count(source_segments.segment_id)
									FROM source_segments
									WHERE source_segments.source_file = ?;""", (self.options['filename'], ))
		file_total_segments = project_cursor.fetchone()[0]
		project_db.close()
		
		if not self.aborted:
			self.finished.emit(file_transtaled_segments, file_total_segments)
			
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