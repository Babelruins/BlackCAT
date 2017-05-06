import nltk.data, sqlite3, os, chardet, pycountry
from PyQt5 import QtCore

def import_file(self, options):
	#First lets try to detect the encoding
	file = open(options['file_path'], 'rb')
	detected_encoding = chardet.detect(file.read())['encoding']
	file.close()

	filename = os.path.basename(options['file_path'])
	
	#Select appropriate tokenizer according to language
	punkt_languages = ['cs', 'da', 'nl', 'en', 'et', 'fi', 'fr', 'de', 'it', 'no', 'pl', 'pt', 'es', 'sv', 'tr']
	if options['source_language'] in punkt_languages:
		tokenizer = nltk.data.load('tokenizers/punkt/' + pycountry.languages.get(alpha_2=options['source_language']).name.lower() + '.pickle')
	elif options['source_language'] == 'el':
		tokenizer = nltk.data.load('tokenizers/punkt/greek.pickle')
	elif options['source_language'] == 'sl':
		tokenizer = nltk.data.load('tokenizers/punkt/slovene.pickle')
	elif options['source_language'] == 'ja':
		tokenizer = nltk.RegexpTokenizer(u'[^ 「」!?。．）]*[!?。]')
	else:
		tokenizer = nltk.LineTokenizer(blanklines='keep')
	
	file = open(options['file_path'], encoding=detected_encoding)
	text = file.read()
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
	sentences_in_file = tokenizer.tokenize(text)
	
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
	project_cursor.execute("INSERT OR REPLACE INTO source_files (name, proc_algorithm, m_time, encoding) VALUES(?, 'punkt', ?, ?);", (filename, options['m_time'], detected_encoding))
	
	#Insert the new sentences
	seen = set()
	for index, sentence in enumerate(sentences_in_file):
		if sentence not in seen:
			project_cursor.execute("INSERT INTO source_segments (segment, language, source_file) VALUES(?, ?, ?);", (sentence, options['source_language'], filename))
			project_cursor.execute("UPDATE source_segments SET source_file_index = ? WHERE segment = ? AND language = ? AND source_file = ?;", (index, sentence, options['source_language'], filename))
			seen.add(sentence)

	file.close()
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
			
		encoding = project_cursor.execute("SELECT encoding FROM source_files WHERE name = ?", (filename, )).fetchone()[0]

		#Select appropriate tokenizer according to language
		punkt_languages = ['cs', 'da', 'nl', 'en', 'et', 'fi', 'fr', 'de', 'it', 'no', 'pl', 'pt', 'es', 'sv', 'tr']
		if options['source_language'] in punkt_languages:
			tokenizer = nltk.data.load('tokenizers/punkt/' + pycountry.languages.get(alpha_2=options['source_language']).name.lower() + '.pickle')
		elif options['source_language'] == 'el':
			tokenizer = nltk.data.load('tokenizers/punkt/greek.pickle')
		elif options['source_language'] == 'sl':
			tokenizer = nltk.data.load('tokenizers/punkt/slovene.pickle')
		elif options['source_language'] == 'ja':
			tokenizer = nltk.RegexpTokenizer(u'[^ 「」!?。．）]*[!?。]')
		else:
			tokenizer = nltk.LineTokenizer(blanklines='keep')
		
		file = open(options['file_path'], encoding=encoding)
		text = file.read()
		translated_data = ''
		sentences = tokenizer.tokenize(text)
		positions = tokenizer.span_tokenize(text)
		last_sentence_ending_position = 0
		for sentence, position in zip(sentences, positions):
			translated_data = translated_data + text[last_sentence_ending_position:position[0]]
			#if not hasattr(sentences_in_db, 'sentence'):
			if sentences_in_db[sentence] is None:
				translated_data = translated_data + sentence
			else:
				translated_data = translated_data + sentences_in_db[sentence]
			last_sentence_ending_position = position[1]
		project_db.close()
		file.close()
		
		target_file = open(os.path.join(options['project_dir'], 'processed_files', filename), 'w', encoding='utf-8')
		target_file.write(translated_data)
		target_file.close()
		
		self.finished.emit()