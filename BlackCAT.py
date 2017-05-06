import sys
from core import base
from PyQt5 import QtWidgets, QtCore

if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	
	mw = base.main_window()
	mw.setWindowTitle('BlackCAT')
	mw.show()
	
	sys.exit(app.exec_())