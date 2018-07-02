import polib, os
from PyQt5 import QtCore
from core import db_op
from time import localtime, strftime

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
		#Check if it has plurals
		if entry.msgid_plural != '':
			db_op.import_source_segment(options['project_path'], entry.msgid, options['source_language'], filename, index, plural=entry.msgid_plural)
			for index, plural in entry.msgstr_plural.items():
				db_op.import_variant(options['project_path'], plural, options['target_language'], fuzzy, filename, entry.msgid, plural_index=index)
		else:
			db_op.import_source_segment(options['project_path'], entry.msgid, options['source_language'], filename, index)
			if entry.msgstr != "":
				db_op.import_variant(options['project_path'], entry.msgstr, options['target_language'], fuzzy, filename, entry.msgid)
	
def generate_file(options):
	filename = os.path.basename(options['file_path'])
	#segments_in_db = db_op.get_segments_with_plurals_in_db(options['project_path'], options['source_language'], options['target_language'], filename)
	po_file = polib.pofile(options['file_path'], wrapwidth = 0)
	for entry in po_file:
		if entry.msgid_plural != '':
			is_fuzzy = False
			for index, plural in entry.msgstr_plural.items():
				translated_segment = db_op.get_translated_segment(options['project_path'], options['source_language'], options['target_language'], filename, entry.msgid, index)
				entry.msgstr_plural[index] = translated_segment[1]
				if translated_segment[2] == 1:
					is_fuzzy = True
			if is_fuzzy and ('fuzzy' not in entry.flags):
				entry.flags.append('fuzzy')
			elif not is_fuzzy and ('fuzzy' in entry.flags):
				entry.flags.remove('fuzzy')
		else:
			translated_segment = db_op.get_translated_segment(options['project_path'], options['source_language'], options['target_language'], filename, entry.msgid, 0)
			if translated_segment is not None:
				entry.msgstr = translated_segment[1]
				if (translated_segment[2] == 0) and ('fuzzy' in entry.flags):
					entry.flags.remove('fuzzy')
				elif (translated_segment[2] == 1) and ('fuzzy' not in entry.flags):
					entry.flags.append('fuzzy')
	
	po_file.metadata['X-Generator'] = 'BlackCAT 1.0'
	po_file.metadata['PO-Revision-Date'] = strftime("%Y-%m-%d %H:%M%z", localtime())
	po_file.save(os.path.join(options['project_dir'], 'processed_files', filename))