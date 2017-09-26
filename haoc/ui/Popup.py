from PySide2 import QtWidgets, QtCore, QtUiTools, QtGui
import hou
import os
from haoc import HaocUtils
from haoc import SCloudUtils, HaocObjects
import codecs


class HelpWidget(QtWidgets.QFrame):
	def __init__(self, text, leader):
		QtWidgets.QFrame.__init__(self)
		self.leader = leader
		self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
		self.setMaximumWidth(180)
		self.setMinimumWidth(120)
		self.label = QtWidgets.QTextBrowser(self)
		main_layout = QtWidgets.QVBoxLayout()
		main_layout.addWidget(self.label)
		main_layout.setContentsMargins(0, 0, 0, 0)
		self.label.setText(text)
		self.setLayout(main_layout)
		self.label.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.label.setStyleSheet("border-style:outset; border-width:1px;  border-radius: 4px; ")

	def showEvent(self, e):
		PopWidget.help_follow_parent(self, self.leader)
		height =  self.label.document().size().height()
		if height > self.leader.height():
			height = self.leader.height()
		self.resize(self.width(),height)

class PopWidget(QtWidgets.QWidget):
	def __init__(self, parent=None):
		QtWidgets.QWidget.__init__(self, parent)
		self.is_shift_hold = False
		self.help_widget = None
		self.network_editor = None
		self.mouse_Press_pos = QtCore.QPoint()
		self.can_move = False
		self.accepted_index = None
		self.pwd_for_load_nodes = None
		self.pos_for_load_nodes = None
		self.__old_name_for_rename = None
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.NoDropShadowWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

		loader = QtUiTools.QUiLoader()
		self.ui = loader.load(HaocUtils.get_root_path() + '/ui/Popup.ui')

		self.title = self.ui.findChild(QtWidgets.QLabel, "title")
		self.upload_widgets = self.ui.findChild(QtWidgets.QWidget, "upload_widgets")
		self.comments = self.ui.findChild(QtWidgets.QTextEdit, "comments")
		self.splitter = self.ui.findChild(QtWidgets.QSplitter, "splitter")
		self.upload_btn = self.ui.findChild(QtWidgets.QPushButton, "upload")
		self.search_bar = self.ui.findChild(QtWidgets.QLineEdit, "search_bar")
		self.asset_name = self.ui.findChild(QtWidgets.QLineEdit, "asset_name")
		self.tree_view = self.ui.findChild(QtWidgets.QTreeView, "tree_view")
		self.hda_fall_backs = self.ui.findChild(QtWidgets.QCheckBox, "hda_fall_backs")

		self.splitter.setSizes([0])
		self.upload_btn.clicked.connect(self.on_upload)
		self.search_bar.textChanged.connect(self.on_search_changed)

		self.tree_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.tree_view.doubleClicked.connect(self.on_tree_dou_clicked)
		self.tree_view.collapsed.connect(self.on_resize_column)
		self.tree_view.expanded.connect(self.on_resize_column)
		self.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.tree_view.customContextMenuRequested.connect(self.open_menu)

		self.model = QtGui.QStandardItemModel()
		self.model.itemChanged.connect(self.on_tree_item_changed)
		self.sort_filter = HaocObjects.TreeViewSortFilterProxyModel()
		self.sort_filter.setSourceModel(self.model)
		self.tree_view.setModel(self.sort_filter)
		self.selection_model = self.tree_view.selectionModel()
		self.selection_model.selectionChanged.connect(self.on_sel_changed)

		main_layout = QtWidgets.QVBoxLayout()
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.addWidget(self.ui)
		self.setLayout(main_layout)
		self.setGeometry(self.ui.geometry())

	def show_pop(self, net_editor, is_upload):
		self.upload_widgets.setVisible(is_upload)
		self.comments.setText('')
		self.comments.setVisible(is_upload)
		self.network_editor = net_editor
		self.refresh_tree()
		self.splitter.setSizes([0])
		if self.help_widget is not None:
			self.help_widget.close()
		if is_upload:
			self.asset_name.setFocus()
		else:
			self.search_bar.setFocus()
		self.show()

	def open_menu(self, position):
		index = self.tree_view.currentIndex()
		index = self.sort_filter.mapToSource(index)
		selected_item = self.sort_filter.sourceModel().itemFromIndex(index)
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
		selected_path = self.get_selected_path(self.get_current_item())
		cat_name = self.get_context_name()
		local_path = "%s/%s/%s" % (HaocUtils.get_local_nodes_path(), cat_name, selected_path)
		if selected_path[-1] == '/':
			os.rmdir(local_path)
		else:
			os.remove("%s.nod" % local_path)
			if os.path.exists("%s.hlp" % local_path):
				os.remove("%s.hlp" % local_path)
		com = HaocObjects.CommandItem(2, path="%s/%s" % (cat_name, selected_path))
		t_delete = SCloudUtils.TDoCommands([com])
		t_delete.start()

		index = self.tree_view.currentIndex()
		self.sort_filter.removeRow(index.row(), index.parent())

	def get_current_item(self):
		index = self.tree_view.currentIndex()
		index = self.sort_filter.mapToSource(index)
		return self.sort_filter.sourceModel().itemFromIndex(index)

	def on_rename_menu(self):
		if SCloudUtils.is_any_cloud_operation_running():
			print "Please wait for current cloud operation finish"
			return
		index = self.tree_view.currentIndex()
		source_index = self.sort_filter.mapToSource(index)
		selected_item = self.sort_filter.sourceModel().itemFromIndex(source_index)
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

		if self.__old_name_for_rename != item.text():
			new_local_name = "%s/%s/%s" % (HaocUtils.get_local_nodes_path(), self.get_context_name(), self.get_selected_path(item))
			old_local_name = new_local_name[:-len(item.text())] + self.__old_name_for_rename
			new_cloud_name = "%s/%s" % (self.get_context_name(), self.get_selected_path(item))
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
			t_rename = SCloudUtils.TDoCommands([com])
			t_rename.start()

	def on_search_changed(self, text):
		if text == '':
			self.tree_view.collapseAll()
		else:
			self.tree_view.expandAll()

		self.sort_filter.setFilterFixedString(text)

	def on_resize_column(self):
		self.tree_view.resizeColumnToContents(0)

	def on_sel_changed(self, selected, deselected):
		indexes = selected.indexes()
		if len(indexes) < 1:
			return
		index = self.sort_filter.mapToSource(indexes[0])
		selected_item = self.sort_filter.sourceModel().itemFromIndex(index)
		selected_path = PopWidget.get_selected_path(selected_item)
		self.model.setHorizontalHeaderLabels(["%s/%s" % (self.get_context_name(), selected_path if selected_path[-1] == '/' else selected_path + '.nod')])

		# Show help stuff
		text = ''
		if selected_path[-1] != '/':
			file_path = '%s/data/%s/nodes/%s/%s.hlp' % (HaocUtils.get_root_path(), HaocUtils.Config.get_ak(), self.get_context_name(), selected_path)
			if os.path.exists(file_path):
				with open(file_path, 'r') as comments_file:
					text = comments_file.read()
		if text != '':
			self.help_widget = HelpWidget(text, self)
			self.help_widget.setStyleSheet(self.styleSheet())
			self.help_widget.show()

		elif self.help_widget is not None and self.help_widget.isVisible():
			self.help_widget.close()

	def on_tree_dou_clicked(self, index):
		self.accepted_index = index
		self.pwd_for_load_nodes = self.network_editor.pwd()
		self.pos_for_load_nodes = self.network_editor.cursorPosition()
		self.load_nodes()

	def on_upload(self):
		self.save_nodes()
		self.close()

	def save_nodes(self):
		input_name = self.asset_name.text().strip()
		if len(input_name) < 3:
			QtWidgets.QMessageBox.warning(hou.qt.mainWindow(), "Input Error", "The number of letters of Asset name must at least have 3")
			return
		input_error = HaocUtils.check_name_ok(input_name)
		if input_error != '':
			QtWidgets.QMessageBox.warning(hou.qt.mainWindow(), "Input Error", "File name is not up to standard,please remove the stuff below from your input:\n%s" % input_error)
			return

		selected_path = ""
		index = self.tree_view.currentIndex()
		index = self.sort_filter.mapToSource(index)
		selected_item = self.sort_filter.sourceModel().itemFromIndex(index)
		if selected_item:
			selected_path = PopWidget.get_selected_folder(selected_item)
		asset_upload_path = selected_path + input_name
		parent = hou.selectedItems()[0].parent()
		cat_name = parent.childTypeCategory().name()
		local_path = '%s/data/%s/nodes/%s/%s' % (HaocUtils.get_root_path(), HaocUtils.Config.get_ak(), cat_name, asset_upload_path)
		cloud_path = '%s/%s' % (cat_name, asset_upload_path)

		if input_name[-1] == "/":
			if not os.path.exists(local_path):
				os.makedirs(local_path)
		else:
			if os.path.exists("%s.nod" % local_path):
				button_code = HaocUtils.show_question_box(self, "This asset is already exist,do you want to replace it?")
				if button_code != QtWidgets.QMessageBox.Yes:
					return

			# Check for SopNode HardLocked status
			if len(hou.selectedNodes()) > 1:
				locked_nodes = []
				if self.network_editor.pwd().childTypeCategory() == hou.sopNodeTypeCategory():
					for node in hou.selectedNodes():
						if isinstance(node, hou.SopNode) and node.isHardLocked():
							locked_nodes.append(node)
				if len(locked_nodes) > 0:
					text = "Detected these selected nodes have had HardLocked,thus will cause asset become large, " \
						   "do you want to unlock those nodes?\n%s" % "\n".join([x.name() for x in locked_nodes])
					button_code = HaocUtils.show_question_box(self, text)
					if button_code == QtWidgets.QMessageBox.Cancel:
						return
					if button_code == QtWidgets.QMessageBox.Yes:
						for node in locked_nodes:
							node.setHardLocked(False)

			if not os.path.exists(os.path.dirname(local_path)):
				os.makedirs(os.path.dirname(local_path))
			parent.saveItemsToFile(hou.selectedItems(), "%s.nod" % local_path, self.hda_fall_backs.isChecked())
			if self.comments.toPlainText().strip() != '':
				with codecs.open("%s.hlp" % local_path, 'w', 'utf-8') as comments_file:
					comments_file.write(self.comments.toPlainText())

		# Put folder or file on cloud
		command = HaocObjects.CommandItem(1, path=cloud_path)
		commands_t = SCloudUtils.TDoCommands([command])
		commands_t.start()

	def load_nodes(self):
		if SCloudUtils.is_any_cloud_operation_running():
			print "Please wait for current cloud operation finish"
			self.close()
			return
		if self.accepted_index.row < 0:
			return
		source_selected_index = self.sort_filter.mapToSource(self.accepted_index)
		selected_item = self.sort_filter.sourceModel().itemFromIndex(source_selected_index)
		if selected_item.text()[-1] == '/':
			return
		selected_path = "%s.nod" % PopWidget.get_selected_path(selected_item)

		cat_name = self.pwd_for_load_nodes.childTypeCategory().name()
		file_path = '%s/%s/%s' % (HaocUtils.get_local_nodes_path(), cat_name, selected_path)

		if os.path.getsize(file_path) == 0:
			d = SCloudUtils.TDownloadNode("%s/%s" % (cat_name, selected_path))
			d.download_finished.connect(self.on_download_finished)
			d.start()
		else:
			self.load_asset_in_houdini(file_path)
		self.close()
		self.network_editor.homeToSelection()

	def on_download_finished(self, res):
		if res.state == SCloudUtils.ResultDataState.SUCCESS:
			self.load_asset_in_houdini(res.data)
			self.network_editor.homeToSelection()
		else:
			print "Download failed"

	def load_asset_in_houdini(self, file_path):
		try:
			hou.clearAllSelected()
			self.pwd_for_load_nodes.loadItemsFromFile(file_path, True)
			with hou.undos.disabler():
				self.move_nodes_to_clicked_position(hou.selectedItems(), self.pos_for_load_nodes)
		except hou.PermissionError as e:
			HaocUtils.show_message_box(self, e.instanceMessage())
		except hou.OperationFailed as e:
			HaocUtils.show_message_box(self, e.description())
			# If load failed it can be the asset damaged, so make it size 0 for nex time download
			open(file_path, 'w').close()
		except hou.LoadWarning as e:
			print e.description()

	@staticmethod
	def move_nodes_to_clicked_position(nodes, good_pos):
		if len(nodes) < 1:
			return
		delta_poss = []
		first_node = nodes[0]
		other_nodes = nodes[1:]
		for n in other_nodes:
			delta_poss.append(first_node.position() - n.position())

		first_node.setPosition(good_pos)
		first_node_pos = first_node.position()
		for node, delta_p in zip(other_nodes, delta_poss):
			node.setPosition(first_node_pos - delta_p)

	def refresh_tree(self):
		context = self.get_context_name()
		self.model.clear()
		HaocUtils.setup_tree_model(self.model, "%s/data/%s/nodes/%s" % (HaocUtils.get_root_path(), HaocUtils.Config.get_ak(), context))
		self.model.setHorizontalHeaderLabels(["%s/" % context])

	def closeEvent(self, event):
		self.search_bar.setText('')
		self.asset_name.setText('')
		self.tree_view.collapseAll()
		self.tree_view.selectionModel().clearSelection()
		if self.help_widget is not None:
			self.help_widget.close()

	def get_context_name(self):
		return self.network_editor.pwd().childTypeCategory().name()

	def mousePressEvent(self, e):
		if e.button() == QtCore.Qt.MouseButton.LeftButton:
			self.mouse_Press_pos = e.pos()
			if self.title.geometry().contains(self.title.mapFrom(self, e.pos())):
				self.can_move = True
				self.setFocus()
		elif self.can_move:
			self.can_move = False

	def mouseMoveEvent(self, e):
		if self.can_move:
			self.move(self.mapToGlobal(e.pos()) - self.mouse_Press_pos)
		self.help_follow_parent(self.help_widget, self)

	def keyPressEvent(self, e):
		if e.key() == QtCore.Qt.Key_Shift:
			self.is_shift_hold = True

		if e.key() == QtCore.Qt.Key_Return or e.key() == QtCore.Qt.Key_Enter:
			if self.tree_view.hasFocus():
				self.accepted_index = self.tree_view.currentIndex()
				self.pwd_for_load_nodes = self.network_editor.pwd()
				self.pos_for_load_nodes = self.network_editor.cursorPosition()
				source_selected_index = self.sort_filter.mapToSource(self.accepted_index)
				selected_item = self.sort_filter.sourceModel().itemFromIndex(source_selected_index)
				if selected_item.text()[-1] == '/':
					self.tree_view.setExpanded(self.accepted_index, not self.tree_view.isExpanded(self.accepted_index))
				else:
					self.load_nodes()

		if e.key() == QtCore.Qt.Key_Down:
			if not self.tree_view.hasFocus():
				self.tree_view.setFocus()
		if self.isVisible() and self.is_shift_hold:
			if e.key() == QtCore.Qt.Key_Down:
				self.resize(self.size().width(), self.size().height() + 3)
			elif e.key() == QtCore.Qt.Key_Up:
				self.resize(self.size().width(), self.size().height() - 3)
			if e.key() == QtCore.Qt.Key_Left:
				self.resize(self.size().width() - 1, self.size().height())
			elif e.key() == QtCore.Qt.Key_Right:
				self.resize(self.size().width() + 1, self.size().height())
			PopWidget.help_follow_parent(self.help_widget, self)

	def keyReleaseEvent(self, e):
		if e.key() == QtCore.Qt.Key_Shift:
			self.is_shift_hold = False

	def event(self, event):
		if event.type() == QtCore.QEvent.WindowDeactivate:
			self.close()
		return QtWidgets.QWidget.event(self, event)

	@staticmethod
	def help_follow_parent(follower, leader):
		if follower is not None:
			if leader.x() < follower.width():
				follower.move(leader.x() + leader.width() + 2, leader.y())
			else:
				follower.move(leader.x() - follower.width() - 2, leader.y())

	@staticmethod
	def get_selected_folder(selected_item):
		s_path = ""
		while True:
			s_path = '%s%s' % (selected_item.text(), s_path)
			if selected_item.parent():
				selected_item = selected_item.parent()
			else:
				break
		if s_path.find('/') != -1:
			if s_path[-1] != '/':
				s_path = "/".join(s_path.split('/')[:-1]) + '/'
		else:
			s_path = ""
		return s_path

	@staticmethod
	def get_selected_path(selected_item):
		if selected_item is None:
			return ""
		s_path = ""
		while True:
			s_path = '%s%s' % (selected_item.text(), s_path)
			if selected_item.parent():
				selected_item = selected_item.parent()
			else:
				break
		return s_path
