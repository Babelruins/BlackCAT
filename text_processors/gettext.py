import polib, sqlite3, os
from PyQt5 import QtCore

def import_file(self, options):
	po_file = polib.pofile(options['file_path'])
	filename = os.path.basename(options['file_path'])
	
	project_db = sqlite3.connect(options['project_path'])
	project_cursor = project_db.cursor()
	
	#Lets see if the file already has imported segments
	imported_segments = {}
	for row in project_cursor.execute("""	SELECT source_segments.segment_id, source_segments.segment
												FROM source_segments
												WHERE source_segments.source_file = ?
												AND source_segments.language = ?""", (filename, options['source_language'])):
		imported_segments[row[1]] = row[0]
	
	segments_in_file = []
	for entry in po_file:
		segments_in_file.append(entry.msgid)
		
	for row in imported_segments:
		if row not in segments_in_file:
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
	project_cursor.execute("INSERT OR REPLACE INTO source_files (name, proc_algorithm, m_time) VALUES(?, 'gettext', ?);", (filename, options['m_time']))
	
	for index, entry in enumerate(po_file):
		fuzzy = 0
		if 'fuzzy' in entry.flags:
			fuzzy = 1
		project_cursor.execute("INSERT INTO source_segments (segment, language, source_file) VALUES(?, ?, ?);", (entry.msgid, options['source_language'], filename))
		project_cursor.execute("UPDATE source_segments SET source_file_index = ? WHERE segment = ? AND language = ? AND source_file = ?;", (index, entry.msgid, options['source_language'], filename))
		if entry.msgstr != "":
			project_cursor.execute("INSERT OR IGNORE INTO variants (segment, language, fuzzy, source_segment, source_file) SELECT ?, ?, ?, source_segments.segment_id, ? FROM source_segments WHERE segment = ?;", (entry.msgstr, options['target_language'], fuzzy, filename, entry.msgid))
	
	project_db.commit()
	project_db.close()		