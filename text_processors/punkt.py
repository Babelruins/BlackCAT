import nltk.data, os, chardet, pycountry
from PyQt5 import QtCore
from core import db_op

def import_file(options):
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
	
	#Lets see if the file already has imported segments
	imported_segments = db_op.get_source_segments_in_db(options['project_path'], options['source_language'], filename)
	
	#Get the segments in file
	segments_in_file = tokenizer.tokenize(text)
	
	#If the segment exists in the db but not in the file...
	for row in imported_segments:
		if row not in segments_in_file:
			db_op.recycle_segment(options['project_path'], imported_segments[row])
	
	#Add the file to the source_files table
	db_op.import_source_file(options['project_path'], filename, 'punkt', options['m_time'], detected_encoding)
	
	#Insert the new segments
	seen = set()
	for index, segment in enumerate(segments_in_file):
		if segment not in seen:
			db_op.import_source_segment(options['project_path'], segment, options['source_language'], filename, index)
			seen.add(segment)

	file.close()
		
def generate_file(options):
	filename = os.path.basename(options['file_path'])
	
	#segments_in_db = db_op.get_segments_in_db(options['project_path'], options['source_language'], options['target_language'], filename)
		
	encoding = db_op.get_encoding(options['project_path'], filename)

	#Select appropriate tokenizer according to language
	punkt_languages = ['cs', 'da', 'nl', 'en', 'et', 'fi', 'fr', 'de', 'it', 'no', 'pl', 'pt', 'es', 'sv', 'tr']
	lang = pycountry.languages.get(alpha_2=options['source_language'])
	if options['source_language'] in punkt_languages:
		tokenizer = nltk.data.load('tokenizers/punkt/' + lang.name.lower() + '.pickle')
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
	segments = tokenizer.tokenize(text)
	positions = tokenizer.span_tokenize(text)
	last_segment_ending_position = 0

	for segment, position in zip(segments, positions):
		translated_data = translated_data + text[last_segment_ending_position:position[0]]
		#if segments_in_db[segment][0] is None:
		#	translated_data = translated_data + segment
		#else:
		#	translated_data = translated_data + segments_in_db[segment][0]
		
		translated_segment = db_op.get_translated_segment(options['project_path'], options['source_language'], options['target_language'], filename, segment)
		if translated_segment is None:
			translated_data = translated_data + segment
		else:
			translated_data = translated_data + translated_segment[1]
		
		last_segment_ending_position = position[1]
	file.close()
	
	target_file = open(os.path.join(options['project_dir'], 'processed_files', filename), 'w', encoding='utf-8')
	target_file.write(translated_data)
	target_file.close()