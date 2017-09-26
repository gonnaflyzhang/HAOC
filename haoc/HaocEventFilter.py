import hou
from PySide2 import QtCore, QtGui
from haoc.ui import Popup


class HaocEventF(QtCore.QObject):
	singleton = None
	pop = None
	is_control_hold = False
	is_shift_hold = False

	def __init__(self, parent=None):
		QtCore.QObject.__init__(self, parent)

	def eventFilter(self, obj, event):
		if event.type() == QtCore.QEvent.MouseButtonPress:
			if event.button() != QtCore.Qt.MouseButton.MidButton:
				return False
			if HaocEventF.pop is not None:
				if HaocEventF.pop.isVisible():
					return False
			if HaocEventF.is_control_hold and HaocEventF.is_shift_hold:
				pane_tab = hou.ui.curDesktop().paneTabUnderCursor()
				if pane_tab is not None:
					if pane_tab.type() == hou.paneTabType.NetworkEditor:
						if HaocEventF.pop is None:
							HaocEventF.pop = Popup.PopWidget()
							HaocEventF.pop.setStyleSheet(hou.qt.styleSheet())

						main_window_rec = hou.ui.mainQtWindow().geometry()
						des_pos = QtCore.QPoint()
						delta_x = main_window_rec.width() - event.pos().x()
						delta_y = main_window_rec.height() - event.pos().y()
						if delta_x < HaocEventF.pop.size().width():
							des_pos.setX(event.pos().x() - HaocEventF.pop.size().width())
						else:
							des_pos.setX(event.pos().x())
						if delta_y < HaocEventF.pop.size().height():
							des_pos.setY(main_window_rec.height() - HaocEventF.pop.size().height())
						else:
							des_pos.setY(event.pos().y())

						HaocEventF.pop.move(hou.ui.mainQtWindow().mapToGlobal(des_pos))
						HaocEventF.pop.show_pop(pane_tab, len(hou.selectedItems()) > 0)
		if event.type() == QtCore.QEvent.KeyPress:
			if event.key() == QtCore.Qt.Key_Control:
				HaocEventF.is_control_hold = True
			if event.key() == QtCore.Qt.Key_Shift:
				HaocEventF.is_shift_hold = True
		if event.type() == QtCore.QEvent.KeyRelease:
			if event.key() == QtCore.Qt.Key_Control:
				HaocEventF.is_control_hold = False
			if event.key() == QtCore.Qt.Key_Shift:
				HaocEventF.is_shift_hold = False
		return QtCore.QObject.eventFilter(self, obj, event)

	@classmethod
	def installHaocEventF(cls):
		if cls.singleton is None:
			cls.singleton = HaocEventF()
			app = QtGui.QGuiApplication.instance()
			app.installEventFilter(cls.singleton)

	@classmethod
	def uninstallHaocEventF(cls):
		if cls.singleton is not None:
			app = QtGui.QGuiApplication.instance()
			app.removeEventFilter(cls.singleton)
			cls.singleton = None
