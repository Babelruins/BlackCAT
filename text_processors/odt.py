import sys, zipfile, os
from bs4 import BeautifulSoup
from PyQt5 import QtCore
from core import db_op

def import_file(options):
	filename = os.path.basename(options['file_path'])
	odt_file = zipfile.ZipFile(options['file_path'])
	odt_xml = odt_file.open("content.xml")
	soup = BeautifulSoup(odt_xml.read(), "xml")
	
	#Lets see if the file already has imported segments
	imported_segments = db_op.get_source_segments_in_db(options['project_path'], options['source_language'], filename)
	
	#Get the sentences in file
	segments_in_file = []
	for par in soup.find('text').find_all({'h': True, 'p' : True}):
		#print(par.contents)
		text = ''
		for element in par.contents:
			text = text + str(element)
		if text:
			segments_in_file.append(text)
			
	#If the segment exists in the db but not in the file...
	for row in imported_segments:
		if row not in segments_in_file:
			db_op.recycle_segment(options['project_path'], imported_segments[row])
	
	#Add the file to the source_files table
	db_op.import_source_file(options['project_path'], filename, 'odt', options['m_time'])
	
	#Insert the new sentences
	seen = set()
	for index, segment in enumerate(segments_in_file):
		if segment not in seen:
			db_op.import_source_segment(options['project_path'], segment, options['source_language'], filename, index)
			seen.add(segment)

	odt_file.close()
	
def generate_file(options):
	filename = os.path.basename(options['file_path'])
	
	#segments_in_db = db_op.get_segments_in_db(options['project_path'], options['source_language'], options['target_language'], filename)

	odt_file = zipfile.ZipFile(options['file_path'])
	odt_xml = odt_file.open("content.xml")
	soup = BeautifulSoup(odt_xml.read(), "xml")
	
	for par in soup.find('text').find_all({'h': True, 'p' : True}):
		text_in_par = ''
		for element in par.contents:
			text_in_par = text_in_par + str(element)
		if text_in_par:
			translated_segment = db_op.get_translated_segment(options['project_path'], options['source_language'], options['target_language'], filename, text_in_par)
			if translated_segment is not None:
				par.clear()
				segment_soup = BeautifulSoup(translated_segment[1], 'html.parser')
				par.append(segment_soup)
	
	target_file = zipfile.ZipFile(os.path.join(options['project_dir'], 'processed_files', filename), 'w')
	for file in odt_file.infolist():
		if file.filename != "content.xml":
			target_file.writestr(file, odt_file.read(file.filename))
	
	target_file.writestr("content.xml", soup.prettify())
	
	odt_file.close()
	target_file.close()