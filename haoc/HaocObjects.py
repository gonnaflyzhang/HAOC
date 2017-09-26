from PySide2 import QtWidgets, QtCore, QtGui


class CommandItem(object):
	CREATE = 1
	DELETE = 2
	RENAME = 3

	def __init__(self, op_type, op_id=0, op_time=0.0, path=None, old_name=None, new_name=None):
		object.__init__(self)
		self.op_type = op_type
		self.op_id = op_id
		self.op_time = op_time
		self.path = path
		self.old_name = old_name
		self.new_name = new_name

	def __cmp__(self, other):
		return cmp(self.op_time, other.op_time)


class TreeViewSortFilterProxyModel(QtCore.QSortFilterProxyModel):
	def __init__(self):
		QtCore.QSortFilterProxyModel.__init__(self)
		self.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

	def filterAcceptsRow(self, source_row, source_parent):
		if not QtCore.QSortFilterProxyModel.filterAcceptsRow(self, source_row, source_parent):
			source_index = self.sourceModel().index(source_row, 0, source_parent)
			for i in range(self.sourceModel().rowCount(source_index)):
				if self.filterAcceptsRow(i, source_index):
					return True
		else:
			return True
		return False


class HaocTreeView(QtWidgets.QTreeView):
	def __init__(self, parent=None):
		QtWidgets.QTreeView.__init__(self, parent)

		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
		self.collapsed.connect(self.on_resize_column)
		self.expanded.connect(self.on_resize_column)

		self.source_model = QtGui.QStandardItemModel()
		self.sort_filter = TreeViewSortFilterProxyModel()
		self.sort_filter.setSourceModel(self.source_model)
		self.setModel(self.sort_filter)

	def on_resize_column(self):
		self.resizeColumnToContents(0)

	def selectionChanged(self, selected, deselected):
		selected_indexes = selected.indexes()
		if len(selected_indexes) == 0:
			return
		index = self.sort_filter.mapToSource(selected_indexes[0])
		selected_item = self.sort_filter.sourceModel().itemFromIndex(index)
		selected_path = get_selected_path(selected_item)
		self.source_model.setHorizontalHeaderLabels([selected_path if selected_path[-1] == '/' else selected_path + '.nod'])


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
