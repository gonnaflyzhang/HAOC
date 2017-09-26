from PySide2 import QtCore
import os
import hou
from sinastorage.bucket import SCSBucket
import sinastorage
from haoc import HaocUtils, DBUtils, HaocObjects
from haoc.ui import ProgressBar

try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO

BUCKET_NAME = 'qq-ice'


class ResultDataState(object):
	SUCCESS = 0
	ACCESS_KEY_ERROR = 1
	SECRET_KEY_ERROR = 2
	TIMED_OUT = 3
	BAD_NETWORK = 4
	CONFLICT = 5
	UNKNOWN_ERROR = 9
	TARGET_NOT_FOUND = 10

	def __init__(self):
		object.__init__(self)
		self.state = -1
		self.data = None

	def __str__(self):
		return "   state: %s\n   data: %s" % (self.state, self.data)


class Trumpet(QtCore.QObject):
	singleton = None
	sync_done = QtCore.Signal()

	def __init__(self):
		QtCore.QObject.__init__(self)

	@staticmethod
	def setup():
		if Trumpet.singleton is None:
			Trumpet.singleton = Trumpet()
Trumpet.setup()


def catch_result(fun, times, *args):
	res = ResultDataState()
	for time in range(times):
		try:
			res.data = fun(*args)
		except sinastorage.bucket.SCSError as e:
			if e.code == 400:
				res.state = ResultDataState.ACCESS_KEY_ERROR
				return res
			elif e.code == 403:
				res.state = ResultDataState.SECRET_KEY_ERROR
				return res
			elif e.code == 404:
				res.state = ResultDataState.TARGET_NOT_FOUND
				return res
			elif e.code == 409:
				res.state = ResultDataState.CONFLICT
				return res
			elif e.code is None:
				res.state = ResultDataState.BAD_NETWORK
			else:
				res.state = ResultDataState.UNKNOWN_ERROR
		except Exception as e:
			res.state = ResultDataState.UNKNOWN_ERROR
			if time == times - 1:
				print e
		else:
			res.state = ResultDataState.SUCCESS
			return res
	return res


def login_cloud(access_key, secret_key):
	def fun(_time_out, _access_key, _secret_key):
		sinastorage.setDefaultAppInfo(_access_key, _secret_key)

		already_exist = False
		all_b = SCSBucket(timeout=_time_out)
		buckets_generator = all_b.list_buckets()
		for bucket in buckets_generator:
			if bucket[0] == BUCKET_NAME:
				already_exist = True
		if not already_exist:
			new_bucket = SCSBucket(BUCKET_NAME, timeout=_time_out)
			new_bucket.put_bucket()
			new_bucket.put('haoc/', '')

	return catch_result(fun, 2, 3, access_key, secret_key)


def set_user_name(name):
	def fun(_time_out, _name):
		ice_b = SCSBucket(BUCKET_NAME, timeout=_time_out)
		ice_b.put('user/name', _name)

	return catch_result(fun, 3, 2, name)


def get_user_name():
	def fun(_time_out):
		f = None
		try:
			ice_b = SCSBucket(BUCKET_NAME, timeout=_time_out)
			response = ice_b['user/name']
			f = StringIO(response.read())
			return f.read()
		finally:
			if f is not None:
				f.close()

	return catch_result(fun, 3, 2)


is_synchronizing = False
is_manual_sync = True


def sync_data(manual=True):
	global is_manual_sync
	is_manual_sync = manual
	global is_synchronizing
	if is_synchronizing:
		if is_manual_sync:
			print "\n--------  Synchronization is running  --------\n"
		return
	is_synchronizing = True
	agenda_lis = DBUtils.get_command_list()

	if len(agenda_lis) > 0:
		task_thread = TDoCommands(agenda_lis, True)
		task_thread.do_commands_done.connect(__on_do_commands_done)
		task_thread.start()
	else:
		__on_do_commands_done(True)


def __on_do_commands_done(b):
	if b:
		sync_t = TSyncDataToLocal([])
		sync_t.job_done.connect(__on_data_to_local_done)
		sync_t.start()
	else:
		__on_data_to_local_done(ResultDataState())


def __on_data_to_local_done(d):
	if d.state == ResultDataState.SUCCESS:
		local_lis = []
		HaocUtils.get_local_file_list(local_lis, HaocUtils.get_root_path())
		diff_set = set(local_lis) - set(d.data)
		for x in diff_set:
			f = "%s/%s" % (HaocUtils.get_local_nodes_path(), x)
			os.remove(f)
			if os.path.exists("%s.hlp" % f[:-4]):
				os.remove("%s.hlp" % f[:-4])
		if is_manual_sync:
			print "\n++++++++++  Sync done  ++++++++++\n"
		Trumpet.singleton.sync_done.emit()
		DBUtils.set_dirty(False)
	else:
		if is_manual_sync:
			print "\n++++++++++  Sync failed  ++++++++++\n"
	global is_synchronizing
	is_synchronizing = False


class TSyncDataToLocal(QtCore.QThread):
	i_want_die = QtCore.Signal(QtCore.QObject)
	job_done = QtCore.Signal(ResultDataState)

	def __init__(self, lis=None):
		QtCore.QThread.__init__(self)
		self.lis = lis
		HaocUtils.ObjectsHolder.add(self)
		self.finished.connect(self.ready_to_die)
		self.i_want_die.connect(HaocUtils.ObjectsHolder.remove)

	def ready_to_die(self):
		self.i_want_die.emit(self)

	def run(self):
		def fun(_time_out):
			if self.lis is not None:
				self.lis = []
			bucket = SCSBucket(BUCKET_NAME, timeout=_time_out)
			items_generator = bucket.listdir(prefix='haoc/nodes/', limit=10000)
			access_key = HaocUtils.Config.get_ak()
			for item in items_generator:
				common_name = item[0][11:]
				local_name = "%s/data/%s/nodes/%s" % (HaocUtils.get_root_path(), access_key, common_name)
				if self.lis is not None:
					if common_name[-1] == '/' or common_name[-4:] == '.nod':
						self.lis.append(common_name)
				if common_name[-1] == '/':
					if not os.path.exists(local_name):
						os.makedirs(local_name)
				elif common_name[-4:]:
					if os.path.exists(local_name):
						lt = int(os.path.getmtime("%s.nod" % local_name[:-4]))
						ct = int(bucket.info("%s.nod" % item[0][:-4]).get('metadata').get('lmt'))
						# Compare local file modified time with cloud file modified time
						if lt < ct:
							open(local_name, "w").close()
							if is_manual_sync:
								print "Updated: %s" % common_name
					else:
						if not os.path.exists(os.path.dirname(local_name)):
							os.makedirs(os.path.dirname(local_name))
						open(local_name, "w").close()
						if is_manual_sync:
							print "Created: %s" % common_name

		data_state = catch_result(fun, 2, 8)
		data_state.data = self.lis
		self.job_done.emit(data_state)


class TDownloadNode(QtCore.QThread):
	i_want_die = QtCore.Signal(QtCore.QObject)
	download_finished = QtCore.Signal(ResultDataState)
	is_working = False

	def __init__(self, path):
		QtCore.QThread.__init__(self)
		self.path = path
		self.progress_bar = ProgressBar.ProgressBar(os.path.basename(path), hou.qt.mainWindow(), False)

		HaocUtils.ObjectsHolder.add(self)

		self.started.connect(self.on_started)
		self.finished.connect(self.on_finished)
		self.i_want_die.connect(HaocUtils.ObjectsHolder.remove)

	def on_started(self):
		TDownloadNode.is_working = True
		self.progress_bar.show()

	def run(self):
		local_path = "%s/data/%s/nodes/%s" % (HaocUtils.get_root_path(), HaocUtils.Config.get_ak(), self.path)

		def fun():
			cloud_path = "haoc/nodes/%s" % self.path
			bucket = SCSBucket(BUCKET_NAME)
			# info = bucket.info(cloud_path)
			total_size = 0
			response = bucket[cloud_path]
			CHUNK = 16 * 1024
			download_size = 0
			with open(local_path, 'wb') as fp:
				while True:
					chunk = response.read(CHUNK)
					if download_size == 0:
						total_size = long(response.info().dict.get('content-length', 0))
					download_size += CHUNK
					self.progress_bar.set_progress(download_size, total_size)
					if not chunk:
						break
					fp.write(chunk)

			if os.path.exists("%s.hlp" % local_path[:-4]):
				response = bucket["%s.hlp" % cloud_path[:-4]]
				with open("%s.hlp" % local_path[:-4], 'wb') as fp:
					while True:
						chunk = response.read(CHUNK)
						if not chunk:
							break
						fp.write(chunk)
		data_state = catch_result(fun, 2)
		if data_state.state != ResultDataState.SUCCESS:
			if data_state.state == ResultDataState.TARGET_NOT_FOUND:
				os.remove(local_path)
				if os.path.exists("%s.hlp" % local_path[:-4]):
					os.remove("%s.hlp" % local_path[:-4])
			else:
				with open(local_path, 'wb'):
					pass
				if os.path.exists("%s.hlp" % local_path[:-4]):
					with open("%s.hlp" % local_path[:-4], 'w'):
						pass
		data_state.data = local_path
		self.download_finished.emit(data_state)

	def on_finished(self):
		TDownloadNode.is_working = False
		self.progress_bar.close()
		self.i_want_die.emit(self)


class TDoCommands(QtCore.QThread):
	i_want_die = QtCore.Signal(QtCore.QObject)
	new_item_start = QtCore.Signal(str)
	do_commands_done = QtCore.Signal(bool)
	is_working = False

	def __init__(self, commands, from_agenda=False):
		QtCore.QThread.__init__(self)
		self.commands = commands
		self.from_agenda = from_agenda

		self.progress_bar = ProgressBar.ProgressBar("", leader=hou.qt.mainWindow(), is_up=True)
		HaocUtils.ObjectsHolder.add(self)
		self.new_item_start.connect(self.on_new_item_start)
		self.started.connect(self.on_started)
		self.finished.connect(self.on_finished)
		self.i_want_die.connect(HaocUtils.ObjectsHolder.remove)

	def delete(self, com, time_out):
		cloud_path = "haoc/nodes/%s" % com.path
		bucket = SCSBucket(BUCKET_NAME, timeout=time_out)
		if cloud_path[-1] == '/':
			del bucket[cloud_path]
		else:
			shall_do = True
			if self.from_agenda:
				try:
					bucket["%s.nod" % cloud_path]
				except sinastorage.bucket.KeyNotFound:
					return
				else:
					info = bucket.info("%s.nod" % cloud_path)
					ct = HaocUtils.utc_to_local_stamp(info['modify'])
					if com.op_time < ct:
						shall_do = False
			if shall_do:
				del bucket["%s.nod" % cloud_path]
				del bucket["%s.hlp" % cloud_path]

	def create(self, com):
		if com.path[-1] != '/':
			self.new_item_start.emit(os.path.basename(com.path))
		cloud_path = "haoc/nodes/%s" % com.path
		bucket = SCSBucket(BUCKET_NAME)
		local_path = "%s/data/%s/nodes/%s" % (HaocUtils.get_root_path(), HaocUtils.Config.get_ak(), com.path)
		if cloud_path[-1] == '/':
			bucket.put(cloud_path, '')
		else:
			shall_upload = True
			if not os.path.exists("%s.nod" % local_path):
				print "File not found:%s" % local_path
				return
			lt = int(os.path.getmtime("%s.nod" % local_path))

			if self.from_agenda:
				try:
					bucket["%s.nod" % cloud_path]
				except sinastorage.bucket.KeyNotFound:
					pass
				else:
					info = bucket.info("%s.nod" % cloud_path)
					ct = int(info.get('metadata').get('lmt'))
					if lt < ct:
						shall_upload = False

			if shall_upload:
				bucket.putFile("%s.nod" % cloud_path, "%s.nod" % local_path, self.call_back)
				bucket.update_meta("%s.nod" % cloud_path, {'lmt': str(lt)})
				bucket.update_meta("%s.nod" % cloud_path, {'hver': hou.applicationVersionString()})
				if os.path.exists("%s.hlp" % local_path):
					bucket.putFile("%s.hlp" % cloud_path, "%s.hlp" % local_path)
			else:
				open("%s.nod" % local_path, 'w').close()

	def rename(self, com, time_out):
		old_cloud_name = "haoc/nodes/%s" % com.old_name
		new_cloud_name = "haoc/nodes/%s" % com.new_name
		bucket = SCSBucket(BUCKET_NAME, timeout=time_out)
		try:
			if new_cloud_name[-1] == '/':
				bucket.copy(source="/%s/%s" % (BUCKET_NAME, old_cloud_name), key=new_cloud_name)
				del bucket[old_cloud_name]
			else:
				shall_do = True
				if self.from_agenda:
					try:
						bucket["%s.nod" % new_cloud_name]
					except sinastorage.bucket.KeyNotFound:
						pass
					else:
						info = bucket.info("%s.nod" % new_cloud_name)
						ct = float(info.get('metadata').get('lmt'))
						if com.op_time < ct:
							shall_do = False
				if shall_do:
					bucket.copy(source="/%s/%s.nod" % (BUCKET_NAME, old_cloud_name), key="%s.nod" % new_cloud_name)
					del bucket["%s.nod" % old_cloud_name]
					bucket.copy(source="/%s/%s.hlp" % (BUCKET_NAME, old_cloud_name), key="%s.hlp" % new_cloud_name)
					del bucket["%s.hlp" % old_cloud_name]
		except sinastorage.bucket.KeyNotFound:
			pass

	def run(self):
		data_state = None
		for command in self.commands:
			if command.op_type == HaocObjects.CommandItem.CREATE:
				data_state = catch_result(self.create, 2, command)
				if self.from_agenda:
					if data_state.state == ResultDataState.SUCCESS:
						DBUtils.remove_com(command.op_id, HaocObjects.CommandItem.CREATE)
					else:
						break
				else:
					if data_state.state != ResultDataState.SUCCESS:
						DBUtils.record_create(command.path)
						DBUtils.set_dirty(True)
			elif command.op_type == HaocObjects.CommandItem.DELETE:
				data_state = catch_result(self.delete, 3, command, 2)
				if self.from_agenda:
					if data_state.state == ResultDataState.SUCCESS:
						DBUtils.remove_com(command.op_id, HaocObjects.CommandItem.DELETE)
					else:
						break
				else:
					if data_state.state != ResultDataState.SUCCESS:
						DBUtils.record_delete(command.path)
						DBUtils.set_dirty(True)
			elif command.op_type == HaocObjects.CommandItem.RENAME:
				data_state = catch_result(self.rename, 3, command, 2)
				if self.from_agenda:
					if data_state.state == ResultDataState.SUCCESS:
						DBUtils.remove_com(command.op_id, HaocObjects.CommandItem.RENAME)
					else:
						break
				else:
					if data_state.state != ResultDataState.SUCCESS:
						DBUtils.record_rename(command.old_name, command.new_name)
						DBUtils.set_dirty(True)
		self.do_commands_done.emit(data_state.state == ResultDataState.SUCCESS)

	@staticmethod
	def on_started():
		TDoCommands.is_working = True

	def on_finished(self):
		self.progress_bar.close()
		self.i_want_die.emit(self)
		TDoCommands.is_working = False

	def on_new_item_start(self, name):
		self.progress_bar.show()
		self.progress_bar.set_text(name)

	def call_back(self, **cb_kwargs):
		self.progress_bar.set_progress(cb_kwargs['progress'], cb_kwargs['size'])


class TUploadHlp(QtCore.QThread):
	is_working = False

	def __init__(self, path):
		QtCore.QThread.__init__(self)
		self.path = path
		self.started.connect(self.on_started)
		self.finished.connect(self.on_finished)
		HaocUtils.ObjectsHolder.add(self)

	@staticmethod
	def on_started():
		TUploadHlp.is_working = True

	def run(self):
		local_path = "%s/%s.hlp" % (HaocUtils.get_local_nodes_path(), self.path)

		def fun(_time_out):
			cloud_path = "haoc/nodes/%s.hlp" % self.path
			bucket = SCSBucket(BUCKET_NAME, timeout=_time_out)
			bucket.putFile(cloud_path, local_path)
		catch_result(fun, 3, 2)

	def on_finished(self):
		TUploadHlp.is_working = False
		HaocUtils.ObjectsHolder.remove(self)


def is_any_cloud_operation_running():
	return is_synchronizing or TDownloadNode.is_working or TDoCommands.is_working or TUploadHlp.is_working
