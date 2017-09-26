import sys
import math
from PySide2 import QtCore,QtGui,QtWidgets
from haoc import HaocUtils


class ProgressBar(QtWidgets.QWidget):
	def __init__(self, text=None, leader=None, is_up=False, parent=None):
		QtWidgets.QWidget.__init__(self, parent)
		self.is_up = is_up
		self.leader = leader
		self.dragPos = None
		self.desktop_rec = HaocUtils.desktop_rect
		self.setGeometry(0, 0, self.desktop_rec.height()*0.15, self.desktop_rec.height()*0.16)
		if leader is not None:
			self.follow_leader(leader.geometry())
		else:
			self.follow_leader(self.desktop_rec)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		# self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
		self.painter = QtGui.QPainter()

		self.bg_arc_pen = QtGui.QPen(QtGui.QColor(125, 125, 125, 180))
		self.bg_arc_pen.setWidth(6)

		self.fg_arc_pen = QtGui.QPen(QtGui.QColor(0, 183, 238, 200))
		self.fg_arc_pen.setWidth(6)

		self.arrow_brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
		self.arrow_brush.setColor(QtGui.QColor(0, 183, 238, 120))

		self.text_pen = QtGui.QPen(QtGui.QColor(0, 183, 238, 255))

		self.text = text

		self.progress = 0.0
		self.data_text = "0M/0M"

	def mouseMoveEvent(self, e):
		if e.buttons() & QtCore.Qt.LeftButton:
			self.move(e.globalPos() - self.dragPos)
			e.accept()

	def mousePressEvent(self, e):
		if e.button() == QtCore.Qt.LeftButton:
			self.dragPos = e.globalPos() - self.frameGeometry().topLeft()
			e.accept()

	def set_progress(self, current, total):
		if total != 0:
			self.progress = 1.0*current/total
		else:
			self.progress = 0

		if total < 1048576.0:
			self.data_text = "%dK/%dK" % (current/1024, total/1024)
		else:
			self.data_text = "%.1fM/%.1fM" % (current/1048576.0, total/1048576.0)

		orig_color = self.arrow_brush.color()
		orig_color.setAlpha((math.sin(current/51200.0)*0.5 + 0.5)*180 + 20)
		self.arrow_brush.setColor(orig_color)
		self.update()

	def set_text(self, text):
		self.text = text
		self.update()


	@staticmethod
	def create_poly(pos_x, pox_y, n, r, s):
		polygon = QtGui.QPolygonF()
		w = 360 / n
		for i in range(n):
			t = w * i + s
			x = r * math.cos(math.radians(t))
			y = r * math.sin(math.radians(t))
			polygon.append(QtCore.QPointF(pos_x + x, pox_y + y))

		return polygon

	def follow_leader(self, leader_rect):
		x = leader_rect.x() + leader_rect.width() - self.width()
		y = leader_rect.y() + leader_rect.height() - self.height()
		if x > self.desktop_rec.width() - self.width():
			x = self.desktop_rec.width() - self.width()
		if y > self.desktop_rec.height() - self.height():
			y = self.desktop_rec.height() - self.height()
		x -= 20
		y -= 20
		self.move(QtCore.QPoint(x, y))

	def paintEvent(self, e):
		self.painter.begin(self)
		self.painter.setRenderHint(QtGui.QPainter.Antialiasing)

		# pen = QtGui.QPen()
		# pen.setWidth(3)
		# self.painter.setPen(pen)
		# self.painter.drawRect(0, 0, self.width(), self.height())

		self.painter.setPen(self.bg_arc_pen)
		shorter = (self.width() if self.width() < self.height() else self.height())-20
		self.painter.translate(10, 10)

		circle_rect = QtCore.QRect(0, 0, shorter, shorter)
		self.painter.drawEllipse(circle_rect)
		self.painter.setPen(self.fg_arc_pen)
		self.painter.drawArc(circle_rect, 0, -5760 * self.progress)

		self.painter.setPen(self.text_pen)
		f = QtGui.QFont()
		f.setPointSize(shorter*0.1)
		self.painter.setFont(f)
		self.painter.drawText(circle_rect, QtCore.Qt.AlignCenter, self.data_text)
		if self.text is not None:
			r = circle_rect
			r.setHeight(circle_rect.height() + shorter*0.2)
			fm = self.painter.fontMetrics()
			str_elided_text = fm.elidedText(self.text, QtCore.Qt.ElideRight, shorter, QtCore.Qt.TextShowMnemonic)
			self.painter.drawText(circle_rect, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom, str_elided_text)

		self.painter.setPen(QtCore.Qt.NoPen)
		self.painter.setBrush(self.arrow_brush)
		if self.is_up:
			self.painter.drawPolygon(self.create_poly(shorter / 2, shorter * 0.25, 3, shorter * 0.15, -90))
		else:
			self.painter.drawPolygon(self.create_poly(shorter / 2, shorter * 0.75, 3, shorter * 0.15, 90))

		self.painter.end()

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	progress = ProgressBar("default box.nod")
	progress.show()
	progress.set_progress(120*1024, 1800*1024)
	sys.exit(app.exec_())
