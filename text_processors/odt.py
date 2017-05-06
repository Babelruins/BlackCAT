import sys, zipfile, sqlite3, os
from bs4 import BeautifulSoup
from PyQt5 import QtCore

def import_file(self, options):
	filename = os.path.basename(options['file_path'])
	odt_file = zipfile.ZipFile(options['file_path'])
	odt_xml = odt_file.open("content.xml")
	soup = BeautifulSoup(odt_xml.read(), "xml")

	project_db = sqlite3.connect(options['project_path'])
	project_cursor = project_db.cursor()
	
	#Lets see if the file already has imported segments
	imported_segments = {}
	for row in project_cursor.execute("""	SELECT source_segments.segment_id, source_segments.segment
												FROM source_segments
												WHERE source_segments.source_file = ?
												AND source_segments.language = ?""", (filename, options['source_language'])):
		imported_segments[row[1]] = row[0]
	
	#Get the sentences in file
	sentences_in_file = []
	for par in soup.find('text').find_all({'h': True, 'p' : True}):
		text = ''
		for element in par:
			text = text + str(element)
		if text:
			sentences_in_file.append(text)
			
	#If the segment exist in the db but not in the file...
	for row in imported_segments:
		if row not in sentences_in_file:
			#Delete the ones who don't have any translation
			project_cursor.execute("""	DELETE
										FROM source_segments
										WHERE segment_id IN (
											SELECT source_segments.segment_id
											FROM source_segments
											LEFT JOIN variants
											ON variants.source_segment = source_segments.segment_id
											WHERE variants.variant_id IS NULL
											AND source_segments.segment_id = ?)""", (imported_segments[row], ))

			#For the rest of the segments, keep them as translation memory
			project_cursor.execute("""	UPDATE source_segments
										SET source_file = 'tm:' || source_file
										WHERE segment_id = ?""", (imported_segments[row], ))
											
			project_cursor.execute("""	UPDATE variants
										SET source_file = 'tm:' || source_file
										WHERE source_segment = ?""", (imported_segments[row], ))
	
	#Add the file to the source_files table
	project_cursor.execute("INSERT OR REPLACE INTO source_files (name, proc_algorithm, m_time) VALUES(?, 'odt', ?);", (filename, options['m_time']))
	
	#Insert the new sentences
	seen = set()
	for index, sentence in enumerate(sentences_in_file):
		if sentence not in seen:
			project_cursor.execute("INSERT INTO source_segments (segment, language, source_file) VALUES(?, ?, ?);", (sentence, options['source_language'], filename))
			project_cursor.execute("UPDATE source_segments SET source_file_index = ? WHERE segment = ? AND language = ? AND source_file = ?;", (index, sentence, options['source_language'], filename))
			seen.add(sentence)

	odt_file.close()
	project_db.commit()
	project_db.close()
	
class file_generate_thread(QtCore.QThread):
	finished = QtCore.pyqtSignal()
	
	def __init__(self, options, callback, parent=None):
		QtCore.QThread.__init__(self, parent)
		
		self.options = options
		self.finished.connect(callback)
		
	def run(self):
		options = self.options
		filename = os.path.basename(options['file_path'])
		project_db = sqlite3.connect(options['project_path'])
		project_cursor = project_db.cursor()
		
		sentences_in_db = {}
		for row in project_cursor.execute("""	SELECT source_segments.segment, variants.segment
												FROM source_segments
												LEFT OUTER JOIN variants ON (variants.source_segment = source_segments.segment_id AND variants.language = ? AND variants.source_file = ?)
												WHERE source_segments.language = ?
												AND source_segments.source_file = ?;""", (options['target_language'], filename, options['source_language'], filename)):
			sentences_in_db[row[0]] = row[1]

		odt_file = zipfile.ZipFile(options['file_path'])
		odt_xml = odt_file.open("content.xml")
		soup = BeautifulSoup(odt_xml.read(), "xml")
		
		for par in soup.find('text').find_all({'h': True, 'p' : True}):
			text_in_par = ''
			for element in par:
				text_in_par = text_in_par + str(element)
			if text_in_par:
				if sentences_in_db[text_in_par] is not None:
					#par.string = sentences_in_db[text_in_par]
					par.string = ''
					sentence_soup = BeautifulSoup(sentences_in_db[text_in_par], 'lxml')
					for sentence_element in sentence_soup.p:
						par.append(sentence_element)
			
		project_db.close()
		
		target_file = zipfile.ZipFile(os.path.join(options['project_dir'], 'processed_files', filename), 'w')
		for file in odt_file.infolist():
			if file.filename != "content.xml":
				target_file.writestr(file, odt_file.read(file.filename))
		
		target_file.writestr("content.xml", soup.prettify())
		
		odt_file.close()
		target_file.close()
		
		self.finished.emit()