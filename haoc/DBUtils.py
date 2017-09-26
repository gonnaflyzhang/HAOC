import sqlite3
import os

import HaocObjects
import HaocUtils
import time


def get_command_list():
	db = __connect_db()
	c = db.cursor()
	res = []
	cursor = c.execute("SELECT id,op_time, path FROM create_tb")
	for x in cursor:
		res.append(HaocObjects.CommandItem(1, x[0], x[1], path=x[2]))
	cursor = c.execute("SELECT id,op_time, path FROM delete_tb")
	for x in cursor:
		res.append(HaocObjects.CommandItem(2, x[0], x[1], path=x[2]))
	cursor = c.execute("SELECT id,op_time,old_name,new_name FROM rename_tb")
	for x in cursor:
		res.append(HaocObjects.CommandItem(3, x[0], x[1], old_name=x[2], new_name=x[3]))
	c.close()
	db.close()
	res.sort()
	return res


def __connect_db():
	db_path = "%s/data/%s/%s" % (HaocUtils.get_root_path(), HaocUtils.Config.get_ak(), "agenda.db")
	if os.path.exists(db_path):
		return sqlite3.connect(db_path)
	else:
		if not os.path.exists(os.path.dirname(db_path)):
			os.makedirs(os.path.dirname(db_path))
		db = sqlite3.connect(db_path)
		c = db.cursor()
		c.execute("CREATE  TABLE create_tb ('id' INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL  UNIQUE , 'path' TEXT NOT NULL UNIQUE, 'op_time' INTEGER NOT NULL)")
		c.execute("CREATE  TABLE delete_tb ('id' INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL  UNIQUE , 'path' TEXT NOT NULL UNIQUE, 'op_time' INTEGER NOT NULL)")
		c.execute("CREATE  TABLE rename_tb ('id' INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL  UNIQUE , 'old_name' TEXT NOT NULL UNIQUE,  'new_name' TEXT NOT NULL UNIQUE, 'op_time' INTEGER NOT NULL)")
		c.execute("CREATE  TABLE config_tb ('id' INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL  UNIQUE , 'is_dirty' INTEGER NOT NULL, 'launch_with_sync' INTEGER NOT NULL)")
		c.execute("INSERT INTO config_tb (is_dirty,launch_with_sync) VALUES (%d,%d)" % (0, 0))
		db.commit()
		c.close()
		return db


def is_dirty():
	db = __connect_db()
	c = db.cursor()
	cursor = c.execute("SELECT is_dirty FROM config_tb")
	_is = False
	for x in cursor:
		_is = x[0] == 1
	c.close()
	db.close()
	return _is


def set_dirty(b):
	db = __connect_db()
	c = db.cursor()
	c.execute("UPDATE config_tb set is_dirty=%d where id=1" % (1 if b else 0))
	db.commit()
	c.close()
	db.close()


def is_launch_with_sync():
	db = __connect_db()
	c = db.cursor()
	cursor = c.execute("SELECT launch_with_sync FROM config_tb")
	_is = False
	for x in cursor:
		_is = x[0] == 1
	c.close()
	db.close()
	return _is


def set_launch_with_sync(b):
	db = __connect_db()
	c = db.cursor()
	c.execute("UPDATE config_tb set launch_with_sync=%d where id=1" % (1 if b else 0))
	db.commit()
	c.close()
	db.close()


def record_create(path):
	path = path.replace("'", "''")
	db = __connect_db()
	c = db.cursor()

	cursor = c.execute("SELECT id FROM create_tb WHERE path='%s'" % path)
	_id = -1
	for x in cursor:
		_id = x[0]
	if _id == -1:
		c.execute("INSERT INTO create_tb (path,op_time) VALUES ('%s',%d)" % (path, get_now()))
	else:
		c.execute("UPDATE create_tb set op_time = %d where id=%d" % (get_now(), _id))

	db.commit()
	c.close()
	db.close()


def record_delete(path):
	path = path.replace("'", "''")
	db = __connect_db()
	c = db.cursor()

	cursor = c.execute("SELECT id FROM create_tb WHERE path='%s'" % path)
	_id = -1
	for x in cursor:
		_id = x[0]
	if _id != -1:
		c.execute("DELETE from create_tb where id=%d" % _id)
	else:
		# If we first rename A to B ,and then we delete B,So on cloud we just delete A
		cursor = c.execute("SELECT old_name FROM rename_tb WHERE new_name='%s'" % path)
		count = 0
		old_name = None
		for x in cursor:
			count += 1
			old_name = x[0]
		if count > 0:
			c.execute("DELETE from rename_tb where new_name='%s'" % path)
			c.execute("INSERT INTO delete_tb (path,op_time) VALUES ('%s',%d)" % (old_name, get_now()))
		else:
			c.execute("INSERT INTO delete_tb (path,op_time) VALUES ('%s',%d)" % (path, get_now()))

	db.commit()
	c.close()
	db.close()


def record_rename(old_name, new_name):
	old_name = old_name.replace("'", "''")
	new_name = new_name.replace("'", "''")
	db = __connect_db()
	c = db.cursor()

	cursor = c.execute("SELECT id FROM create_tb WHERE path='%s'" % old_name)
	_id = -1
	for x in cursor:
		_id = x[0]
	if _id != -1:
		c.execute("UPDATE create_tb set path = '%s',op_time = %d where id=%d" % (new_name, get_now(), _id))
	else:
		c.execute("INSERT INTO rename_tb (old_name,new_name,op_time) VALUES ('%s','%s',%d)" % (old_name, new_name, get_now()))

	cursor = c.execute("SELECT id FROM rename_tb WHERE new_name='%s'" % old_name)
	_id = -1
	for x in cursor:
		_id = x[0]
	if _id != -1:
		c.execute("UPDATE rename_tb set new_name = '%s',op_time = %d where id=%d" % (new_name, get_now(), _id))

	db.commit()
	c.close()
	db.close()


def remove_com(_id, _type):
	db = __connect_db()
	c = db.cursor()
	if _type == 1:
		c.execute("DELETE from create_tb where id=%d" % _id)
	elif _type == 2:
		c.execute("DELETE from delete_tb where id=%d" % _id)
	elif _type == 3:
		c.execute("DELETE from rename_tb where id=%d" % _id)
	db.commit()
	c.close()
	db.close()


def get_now():
	return int(time.time())

