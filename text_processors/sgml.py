import sys, zipfile, os
from bs4 import BeautifulSoup
from PyQt5 import QtCore
from core import db_op

def import_file(options):
	filename = os.path.basename(options['file_path'])
	sgml_file = open(options['file_path'])
	soup = BeautifulSoup(sgml_file.read(), "html.parser")
	sgml_file.close()

	imported_segments = db_op.get_source_segments_in_db(options['project_path'], options['source_language'], filename)
	
	#Get the segments in file
	segments_in_file = []
	search_tags = {'title':True, 'para':True, 'programlisting':True}
	for seg in soup.find_all(search_tags):
		parents = seg.find_parents(search_tags)
		#Only get non-nested tags
		if len(parents) == 0:
			text = ''
			for element in seg:
				text = text + str(element)
			if text:
				segments_in_file.append(text)
			
	#If the segment exists in the db but not in the file...
	for row in imported_segments:
		if row not in segments_in_file:
			db_op.recycle_segment(options['project_path'], imported_segments[row])
	
	#Add the file to the source_files table
	db_op.import_source_file(options['project_path'], filename, 'sgml', options['m_time'])
	
	#Insert the new sentences
	seen = set()
	for index, segment in enumerate(segments_in_file):
		if segment not in seen:
			db_op.import_source_segment(options['project_path'], segment, options['source_language'], filename, index)
			seen.add(segment)
	
def generate_file(options):
	filename = os.path.basename(options['file_path'])
	
	#segments_in_db = db_op.get_segments_in_db(options['project_path'], options['source_language'], options['target_language'], filename)

	sgml_file = open(options['file_path'])
	soup = BeautifulSoup(sgml_file.read(), "html.parser")
	sgml_file.close()
	
	search_tags = {'title':True, 'para':True, 'programlisting':True}
	for seg in soup.find_all(search_tags):
		parents = seg.find_parents(search_tags)
		#Only get non-nested tags
		if len(parents) == 0:
			text_in_par = ''
			for element in seg:
				text_in_par = text_in_par + str(element)
			if text_in_par:
				translated_segment = db_op.get_translated_segment(options['project_path'], options['source_language'], options['target_language'], filename, text_in_par)
				#if segments_in_db[text_in_par][0] is not None:
				if translated_segment is not None:
					seg.string = ''
					sentence_soup = BeautifulSoup(translated_segment[1], 'lxml')
					for sentence_element in sentence_soup.p:
						seg.append(sentence_element)
	
	target_file = open(os.path.join(options['project_dir'], 'processed_files', filename), 'w')
	target_file.write(soup.prettify())
	target_file.close()