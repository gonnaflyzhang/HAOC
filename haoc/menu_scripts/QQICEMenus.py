import hou, sys
from haoc import HaocUtils, PicToTxt
from haoc.ui import Login
from haoc.ui import AssetManage


click_pos = hou.qt.mainWindow().cursor().pos()
if sys.argv.count('haoc') > 0:
	if HaocUtils.Config.get_ak() == '' or HaocUtils.Config.get_sk() == '':
		if not Login.LoginWidget.is_occupied:
			login = Login.LoginWidget()
			login.setStyleSheet(hou.qt.styleSheet())
			login.move(click_pos)
			login.show()
	else:
		if not AssetManage.AssetMangeWidget.is_occupied:
			asset_manage_w = AssetManage.AssetMangeWidget(HaocUtils.Config.get_name())
			asset_manage_w.setStyleSheet(hou.qt.styleSheet())
			asset_manage_w.move(click_pos)
			asset_manage_w.show()
elif sys.argv.count('about_author') > 0:
	path = "%s/about/author.emo" % (HaocUtils.get_root_path())
	print PicToTxt.get_txt(path)
