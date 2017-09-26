from PySide2 import QtWidgets, QtUiTools, QtCore
import codecs
import os
from haoc import HaocUtils, SCloudUtils, HaocEventFilter, HaocObjects, DBUtils


class AssetMangeWidget(QtWidgets.QWidget):
	is_occupied = False

	def __init__(self, user_name='', parent=None):
		QtWidgets.QWidget.__init__(self, parent)
		self.setWindowTitle("Assets Manager")
		self.__old_name_for_rename = None
		self.__downloading_item = None
		loader = QtUiTools.QUiLoader()
		loader.registerCustomWidget(HaocObjects.HaocTreeView)
		self.ui = loader.load(HaocUtils.get_root_path() + '/ui/AssetMange.ui')

		self.tree_view = self.ui.findChild(HaocObjects.HaocTreeView, "tree_view")
		self.search_bar = self.ui.findChild(QtWidgets.QLineEdit, "search_bar")
		self.user_name = self.ui.findChild(QtWidgets.QLabel, "user_name")
		self.logout = self.ui.findChild(QtWidgets.QPushButton, "logout")
		self.sync = self.ui.findChild(QtWidgets.QPushButton, "sync")
		self.help_tee = self.ui.findChild(QtWidgets.QTextEdit, "help")
		self.apply_help_change = self.ui.findChild(QtWidgets.QPushButton, "apply_help_change")
		self.sync_while_launch = self.ui.findChild(QtWidgets.QCheckBox, "sync_while_launch")

		self.help_tee.setDisabled(True)
		self.sync_while_launch.setChecked(DBUtils.is_launch_with_sync())
		self.sync_while_launch.stateChanged.connect(self.on_swl_changed)

		self.logout.clicked.connect(self.on_logout)
		self.sync.clicked.connect(self.on_sync)
		self.apply_help_change.clicked.connect(self.on_apply_help_change)
		self.user_name.setText(user_name)
		self.tree_view.doubleClicked.connect(self.on_tree_dou_clicked)
		self.tree_view.source_model.itemChanged.connect(self.on_tree_item_changed)
		self.tree_view.selectionModel()
		self.selection_model = self.tree_view.selectionModel()
		self.selection_model.selectionChanged.connect(self.on_sel_changed)

		self.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.tree_view.customContextMenuRequested.connect(self.open_menu)

		self.search_bar.textChanged.connect(self.on_search_changed)

		main_layout = QtWidgets.QVBoxLayout()
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.addWidget(self.ui)
		self.setLayout(main_layout)
		self.setGeometry(self.ui.geometry())
		self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

		HaocUtils.ObjectsHolder.add(self)
		AssetMangeWidget.is_occupied = True
		SCloudUtils.Trumpet.singleton.sync_done.connect(self.on_done)

		self.refresh_tree()

	def refresh_tree(self):
		self.tree_view.source_model.clear()
		HaocUtils.setup_tree_model(self.tree_view.source_model, "%s/data/%s/nodes/" % (HaocUtils.get_root_path(), HaocUtils.Config.get_ak()))
		self.tree_view.source_model.setHorizontalHeaderLabels([""])

	@staticmethod
	def on_swl_changed(state):
		if state == QtCore.Qt.Checked:
			DBUtils.set_launch_with_sync(True)
		elif state == QtCore.Qt.Unchecked:
			DBUtils.set_launch_with_sync(False)

	def on_sel_changed(self, selected, deselected):
		indexes = selected.indexes()
		if len(indexes) < 1:
			return

		index = self.tree_view.sort_filter.mapToSource(indexes[0])
		selected_item = self.tree_view.source_model.itemFromIndex(index)
		selected_path = HaocObjects.get_selected_path(selected_item)
		self.tree_view.source_model.setHorizontalHeaderLabels([selected_path if selected_path[-1] == '/' else selected_path + '.nod'])

		# Show help stuff
		if selected_path[-1] != '/':
			text = ''
			file_path = '%s/data/%s/nodes/%s.hlp' % (HaocUtils.get_root_path(), HaocUtils.Config.get_ak(), selected_path)
			if os.path.exists(file_path):
				if os.path.getsize(file_path) == 0:
					self.help_tee.setDisabled(True)
				else:
					self.help_tee.setDisabled(False)
					with open(file_path, 'r') as comments_file:
						text = comments_file.read()
			else:
				self.help_tee.setDisabled(False)
			self.help_tee.setText(text)
		else:
			self.help_tee.setDisabled(True)
			self.help_tee.setText('')

	def on_tree_dou_clicked(self, index):
		if SCloudUtils.is_any_cloud_operation_running():
			print "Please wait for current cloud operation finish"
			return
		index = self.tree_view.sort_filter.mapToSource(index)
		item = self.tree_view.sort_filter.sourceModel().itemFromIndex(index)
		common_path = HaocObjects.get_selected_path(item)
		if common_path[-1] == '/':
			return
		else:
			common_path = "%s.nod" % common_path

		local_path = "%s/%s" % (HaocUtils.get_local_nodes_path(), common_path)
		if os.path.getsize(local_path) == 0:
			d = SCloudUtils.TDownloadNode(common_path)
			d.download_finished.connect(self.on_download_finished)
			d.start()
			self.__downloading_item = item

	def on_download_finished(self, res):
		if res.state != SCloudUtils.ResultDataState.SUCCESS:
			print "Download failed"
		else:
			self.__downloading_item.set_downloaded(True)
			self.selection_model.clearSelection()
		self.__downloading_item = None

	def on_search_changed(self, text):
		if text == '':
			self.tree_view.collapseAll()
		else:
			self.tree_view.expandAll()
		self.tree_view.sort_filter.setFilterFixedString(text)

	def on_apply_help_change(self):
		txt = self.help_tee.toPlainText().strip()
		if txt == '':
			return
		sel_item = self.get_current_item()
		if sel_item is None:
			return
		sel_path = HaocObjects.get_selected_path(sel_item)
		if sel_path[-1] == '/':
			return
		if SCloudUtils.is_any_cloud_operation_running():
			print "Please wait for current cloud operation finish"
			return
		local_path = "%s/%s.hlp" % (HaocUtils.get_local_nodes_path(), sel_path)

		with codecs.open(local_path, 'w', 'utf-8') as f:
			f.write(txt)
		upload_hlp_t = SCloudUtils.TUploadHlp(sel_path)
		upload_hlp_t.start()

	def on_logout(self):
		data = HaocUtils.Config()
		data.save()
		HaocEventFilter.HaocEventF.uninstallHaocEventF()
		HaocUtils.is_login = False
		self.close()

	def open_menu(self, position):
		idx = self.tree_view.indexAt(QtCore.QPoint(position.x(), position.y()))
		if idx.row() == -1:
			return

		idx = self.tree_view.sort_filter.mapToSource(idx)
		selected_item = self.tree_view.sort_filter.sourceModel().itemFromIndex(idx)
		if not selected_item:
			return
		if not selected_item.hasChildren():
			menu = QtWidgets.QMenu()
			menu.setStyleSheet(self.styleSheet())
			rename_action = QtWidgets.QAction('Rename', self)
			rename_action.triggered.connect(self.on_rename_menu)
			menu.addAction(rename_action)
			delete_action = QtWidgets.QAction('Delete', self)
			delete_action.triggered.connect(self.on_delete_menu)
			menu.addAction(delete_action)
			menu.exec_(self.tree_view.viewport().mapToGlobal(position))

	def on_delete_menu(self):
		if SCloudUtils.is_any_cloud_operation_running():
			print "Please wait for current cloud operation finish"
			return
		selected_path = HaocObjects.get_selected_path(self.get_current_item())
		local_path = "%s/%s" % (HaocUtils.get_local_nodes_path(), selected_path)
		if selected_path[-1] == '/':
			os.rmdir(local_path)
		else:
			os.remove("%s.nod" % local_path)
			if os.path.exists("%s.hlp" % local_path):
				os.remove("%s.hlp" % local_path)
		com = HaocObjects.CommandItem(2, path=selected_path)
		t_delete = SCloudUtils.TDoCommands([com])
		t_delete.start()
		index = self.tree_view.currentIndex()
		self.tree_view.sort_filter.removeRow(index.row(), index.parent())

	def get_current_item(self):
		index = self.tree_view.currentIndex()
		index = self.tree_view.sort_filter.mapToSource(index)
		return self.tree_view.sort_filter.sourceModel().itemFromIndex(index)

	def on_rename_menu(self):
		if SCloudUtils.is_any_cloud_operation_running():
			print "Please wait for current cloud operation finish"
			return
		index = self.tree_view.currentIndex()
		source_index = self.tree_view.sort_filter.mapToSource(index)
		selected_item = self.tree_view.sort_filter.sourceModel().itemFromIndex(source_index)
		self.__old_name_for_rename = selected_item.text()
		self.tree_view.edit(index)

	def on_tree_item_changed(self, item):
		new_name = item.text()

		if self.__old_name_for_rename is None or self.__old_name_for_rename == new_name:
			return
		if len(new_name) < 3:
			item.setText(self.__old_name_for_rename)
			return
		res = HaocUtils.check_name_ok(new_name)

		if res != '':
			item.setText(self.__old_name_for_rename)
			return

		if self.__old_name_for_rename[-1] == '/':
			if new_name.count('/') > 1:
				item.setText(self.__old_name_for_rename)
				return
			if new_name[-1] != '/':
				new_name = "%s/" % new_name
				item.setText(new_name)
				return
		else:
			if new_name.find('/') != -1:
				item.setText(self.__old_name_for_rename)
				return

		new_local_name = "%s/%s" % (HaocUtils.get_local_nodes_path(), HaocObjects.get_selected_path(item))
		old_local_name = new_local_name[:-len(item.text())] + self.__old_name_for_rename
		new_cloud_name = HaocObjects.get_selected_path(item)
		old_cloud_name = new_cloud_name[:-len(item.text())] + self.__old_name_for_rename
		if new_local_name[-1] == "/":
			if os.path.exists(new_local_name):
				item.setText(self.__old_name_for_rename)
				return
			else:
				os.rename(old_local_name, new_local_name)
		else:
			if os.path.exists("%s.nod" % new_local_name):
				item.setText(self.__old_name_for_rename)
				return
			else:
				os.rename("%s.nod" % old_local_name, "%s.nod" % new_local_name)
				if os.path.exists("%s.hlp" % old_local_name):
					os.rename("%s.hlp" % old_local_name, "%s.hlp" % new_local_name)
		com = HaocObjects.CommandItem(3, old_name=old_cloud_name, new_name=new_cloud_name)
		rename_t = SCloudUtils.TDoCommands([com])
		rename_t.start()

	@staticmethod
	def on_sync():
		if SCloudUtils.is_any_cloud_operation_running():
			print "Please wait for current cloud operation finish"
			return
		SCloudUtils.sync_data()

	def on_done(self):
		self.refresh_tree()

	def closeEvent(self, event):
		HaocUtils.ObjectsHolder.remove(self)
		AssetMangeWidget.is_occupied = False

