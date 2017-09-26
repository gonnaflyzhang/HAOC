import hou
import sinastorage
from haoc import HaocUtils,DBUtils,SCloudUtils
from haoc import HaocEventFilter

hou.putenv("HAOCROOTPATH", HaocUtils.get_root_path())

config = HaocUtils.Config.read()
if not (config.ak=='' or config.sk==''):
	sinastorage.setDefaultAppInfo(config.ak,config.sk)
	HaocEventFilter.HaocEventF.installHaocEventF()
	if DBUtils.is_launch_with_sync():
		SCloudUtils.sync_data(False)
