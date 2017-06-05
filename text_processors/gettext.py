import polib, os
from PyQt5 import QtCore
from core import db_op

def import_file(options):
	po_file = polib.pofile(options['file_path'])
	filename = os.path.basename(options['file_path'])
	
	#Lets see if the file already has imported segments
	imported_segments = db_op.get_source_segments_in_db(options['project_path'], options['source_language'], filename)
	
	segments_in_file = []
	for entry in po_file:
		segments_in_file.append(entry.msgid)
		
	for row in imported_segments:
		if row not in segments_in_file:
			db_op.recycle_segment(options['project_path'], imported_segments[row])
										
	#Add the file to the source_files table
	db_op.import_source_file(options['project_path'], filename, 'gettext', options['m_time'])
	
	for index, entry in enumerate(po_file):
		fuzzy = 0
		if 'fuzzy' in entry.flags:
			fuzzy = 1
		db_op.import_source_segment(options['project_path'], entry.msgid, options['source_language'], filename, index)
		if entry.msgstr != "":
			db_op.import_variant(options['project_path'], entry.msgstr, options['target_language'], fuzzy, filename, entry.msgid)
	
def generate_file(options):
	filename = os.path.basename(options['file_path'])
	segments_in_db = db_op.get_segments_in_db(options['project_path'], options['source_language'], options['target_language'], filename)
	po_file = polib.pofile(options['file_path'])
	for entry in po_file:
		if segments_in_db[entry.msgid][0] is not None:
			entry.msgstr = segments_in_db[entry.msgid][0]
			if segments_in_db[entry.msgid][1] == 0:
				if 'fuzzy' in entry.flags:
					entry.flags.remove('fuzzy')
			elif segments_in_db[entry.msgid][1] == 1:
				if 'fuzzy' not in entry.flags:
					entry.flags.append('fuzzy')
	po_file.save(os.path.join(options['project_dir'], 'processed_files', filename))