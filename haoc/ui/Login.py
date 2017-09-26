from PySide2 import QtWidgets, QtUiTools, QtCore
from haoc import HaocEventFilter
from haoc import HaocUtils
from haoc import SCloudUtils
from haoc.ui.AssetManage import AssetMangeWidget


class LoginWidget(QtWidgets.QWidget):
	is_occupied = False

	def __init__(self, parent=None):
		QtWidgets.QWidget.__init__(self, parent)
		self.setWindowTitle("Login")
		loader = QtUiTools.QUiLoader()
		self.ui = loader.load(HaocUtils.get_root_path() + '/ui/Login.ui')
		self.access_key_lie = self.ui.findChild(QtWidgets.QLineEdit, "access_key_lie")
		self.secret_key_lie = self.ui.findChild(QtWidgets.QLineEdit, "secret_key_lie")
		self.login_btn = self.ui.findChild(QtWidgets.QPushButton, "accept_btn")
		self.link_lab = self.ui.findChild(QtWidgets.QLabel, "link")

		self.login_btn.clicked.connect(self.on_login)
		self.link_lab.linkActivated.connect(self.on_clicked_link)

		main_layout = QtWidgets.QVBoxLayout()
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.addWidget(self.ui)
		self.setLayout(main_layout)
		self.setGeometry(self.ui.geometry())
		self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

		HaocUtils.ObjectsHolder.add(self)
		LoginWidget.is_occupied = True

	@staticmethod
	def on_clicked_link(url):
		pass
		# QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

	def on_login(self):
		access_key = self.access_key_lie.text().strip()
		secret_key = self.secret_key_lie.text().strip()
		if access_key == '' or secret_key == '':
			HaocUtils.show_message_box(self, "Please complete the necessary information!")
			return
		login_data_state = SCloudUtils.login_cloud(access_key, secret_key)
		if login_data_state.state != SCloudUtils.ResultDataState.SUCCESS:
			if login_data_state.state == SCloudUtils.ResultDataState.ACCESS_KEY_ERROR:
				HaocUtils.show_message_box(self, "AccessKey is not exist!")
				return
			elif login_data_state.state == SCloudUtils.ResultDataState.SECRET_KEY_ERROR:
				HaocUtils.show_message_box(self, "SecretKey is incorrect")
				return
			elif login_data_state.state == SCloudUtils.ResultDataState.BAD_NETWORK:
				HaocUtils.show_message_box(self, "Bad Network or something wrong ,fix your network problem and try again!")
				return
			else:
				HaocUtils.show_message_box(self, "Unknown error!")
				return
		# Login success
		else:
			user_name = None
			data_state = SCloudUtils.get_user_name()
			if data_state.state != SCloudUtils.ResultDataState.SUCCESS:
				# If there is no name make one
				if data_state.state == SCloudUtils.ResultDataState.TARGET_NOT_FOUND:
					make_name_w = MakeNameWidget(self)
					# make_name_w.setParent(self, QtCore.Qt.Dialog)
					make_name_w.setWindowFlags(QtCore.Qt.Dialog)
					if make_name_w.exec_():
						user_name = make_name_w.get_name().strip()
					else:
						return
				else:
					HaocUtils.show_message_box(self, "Bad Network or something wrong ,fix your network problem and try again!")
			# Already has a name just get it
			else:
				user_name = data_state.data

			data = HaocUtils.Config(access_key, secret_key, user_name)
			data.save()

			asset_manage_widget = AssetMangeWidget(user_name)
			asset_manage_widget.setStyleSheet(self.styleSheet())
			asset_manage_widget.move(self.pos())
			asset_manage_widget.show()

			HaocEventFilter.HaocEventF.installHaocEventF()
			HaocUtils.is_login = True
			self.close()

	def closeEvent(self, event):
		HaocUtils.ObjectsHolder.remove(self)
		LoginWidget.is_occupied = False


class MakeNameWidget(QtWidgets.QDialog):
	def __init__(self, parent=None):
		QtWidgets.QDialog.__init__(self, parent)
		loader = QtUiTools.QUiLoader()
		self.ui = loader.load(HaocUtils.get_root_path() + '/ui/MakeName.ui')
		main_layout = QtWidgets.QVBoxLayout()
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.addWidget(self.ui)
		self.setLayout(main_layout)
		self.setGeometry(self.ui.geometry())
		self.setWindowModality(QtCore.Qt.ApplicationModal)
		self.move(self.cursor().pos() - QtCore.QPoint(self.size().width() / 2, self.size().height() / 2))
		self.setFixedSize(self.width(), self.height())

		self.name_lie = self.ui.findChild(QtWidgets.QLineEdit, "name_lie")
		self.accept_btn = self.ui.findChild(QtWidgets.QPushButton, "accept_btn")

		self.accept_btn.clicked.connect(self.on_accept)

		self.move(parent.mapToGlobal(QtCore.QPoint((parent.width()-self.width())/2, (parent.height()-self.height())/2)))

	def on_accept(self):
		name = self.name_lie.text().strip()
		if len(name) < 3:
			HaocUtils.show_message_box(self, "Name must at least have 3 letters!")
			return
		set_name_data_state = SCloudUtils.set_user_name(name)
		if set_name_data_state.state != SCloudUtils.ResultDataState.SUCCESS:
			HaocUtils.show_message_box(self, "Bad Network or something wrong ,fix your network problem and try again!")
		else:
			self.accept()

	def get_name(self):
		return self.name_lie.text().strip()
