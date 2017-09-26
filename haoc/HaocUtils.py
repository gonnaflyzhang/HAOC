import os
import haoc
import re
import json
from PySide2 import QtCore, QtWidgets, QtGui
import time
import datetime

is_login = False

desktop_rect = QtGui.QGuiApplication.instance().desktop().availableGeometry()


def utc_to_local_stamp(t):
	return time.mktime((t - datetime.timedelta(seconds=time.timezone)).timetuple())


class ObjectsHolder:
	# Protect objects from garbage collection
	objects = []

	@classmethod
	def add(cls, obj):
		cls.objects.append(obj)

	@classmethod
	def remove(cls, obj):
		if obj in cls.objects:
			cls.objects.remove(obj)

	def __init__(self):
		pass


def get_local_nodes_path():
	return "%s/data/%s/nodes" % (get_root_path(), Config.get_ak())


def get_root_path():
	return os.path.dirname(haoc.__file__).replace('\\', '/')


class Config:
	path = get_root_path() + '/data/u_info.json'
	access_key = None

	def __init__(self, ak="", sk="", n=""):
		self.ak = ak
		self.sk = sk
		self.name = n

	@staticmethod
	def config_to_dict(config):
		return {'ak': config.ak, 'sk': config.sk, 'name': config.name}

	@staticmethod
	def dict_to_config(d):
		config = Config()
		config.ak = d['ak']
		config.sk = d['sk']
		config.name = d['name']
		return config

	def save(self):
		with open(Config.path, 'w') as f:
			json.dump(self, f, default=Config.config_to_dict)

	@staticmethod
	def read():
		if not os.path.exists(Config.path):
			if not os.path.exists(os.path.dirname(Config.path)):
				os.makedirs(os.path.dirname(Config.path))
			c = Config()
			c.save()
		with open(Config.path, 'r') as f:
			obj = json.load(f, object_hook=Config.dict_to_config)
			return obj

	@staticmethod
	def get_ak():
		if Config.access_key is None or Config.access_key == '':
			Config.access_key = Config.read().ak
		return Config.access_key

	@staticmethod
	def get_sk():
		return Config.read().sk

	@staticmethod
	def get_name():
		return Config.read().name

	def __str__(self):
		return "name:%s, access_key:%s ,secret_key:%s" % (self.name, self.ak, self.sk)


def show_message_box(parent, message):
	msg_box = QtWidgets.QMessageBox()
	msg_box.setText(message)
	msg_box.setParent(parent, QtCore.Qt.Window)
	msg_box.exec_()


def show_question_box(parent, message):
	msg_box = QtWidgets.QMessageBox(parent)
	msg_box.setText(message)
	msg_box.addButton(QtWidgets.QMessageBox.Yes)
	msg_box.addButton(QtWidgets.QMessageBox.No)
	msg_box.addButton(QtWidgets.QMessageBox.Cancel)
	msg_box.setEscapeButton(QtWidgets.QMessageBox.Cancel)
	return msg_box.exec_()


def get_local_file_list(lis, root):
	for f in os.listdir(root):
		full_path = os.path.join(root, f)
		if os.path.isdir(full_path):
			# lis.append(full_path.replace('\\', '/'))
			get_local_file_list(lis, full_path)
		else:
			if full_path[-4:] == '.nod':
				lis.append(full_path.replace('\\', '/')[len(get_local_nodes_path())+1:])


class TreeItem(QtGui.QStandardItem):
	def __init__(self, text, is_downloaded=True):
		QtGui.QStandardItem.__init__(self, text)
		self.is_downloaded = is_downloaded
		self.set_downloaded(is_downloaded)

	def set_downloaded(self, tof):
		self.is_downloaded = tof
		font = self.font()
		font.setItalic(not tof)
		self.setFont(font)


def setup_tree_model(parent, path):
	if not os.path.exists(path):
		os.makedirs(path)
	for f in os.listdir(path):
		full_path = os.path.join(path, f)
		if os.path.isdir(full_path):
			item = TreeItem(os.path.basename(full_path) + "/")
			parent.appendRow(item)
			setup_tree_model(item, full_path)
		else:
			if full_path[-4:] == '.nod':
				is_d = os.path.getsize(full_path) != 0
				item = TreeItem(os.path.basename(full_path)[:-4], is_downloaded=is_d)
				parent.appendRow(item)


def check_name_ok(s):
	pattern = re.compile("^/|//+|[^a-zA-Z0-9/\s_\-+,'!@#$%^&`~()\[\]]+")
	res = pattern.findall(s)
	return " ".join(res)

