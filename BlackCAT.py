import sys
from core import base
from PyQt5 import QtWidgets, QtCore, QtGui

if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	
	mw = base.main_window()
	mw.setWindowTitle('BlackCAT')
	mw.setWindowIcon(QtGui.QIcon('whitecat_256x256.png'))
	mw.show()
	
	sys.exit(app.exec_())