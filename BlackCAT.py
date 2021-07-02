import sys
import qdarkstyle
from core import base
from PyQt5 import QtWidgets, QtCore, QtGui

if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	app.setStyleSheet(qdarkstyle.load_stylesheet())
	
	mw = base.main_window()
	mw.setWindowTitle('BlackCAT')
	mw.setWindowIcon(QtGui.QIcon('images/blackcat.png'))
	mw.show()
	
	sys.exit(app.exec_())