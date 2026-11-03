import os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"collector"))
import seoul_month_recovery as r
class RetryCheckpointTests(unittest.TestCase):
    def test_transient_push_is_retried(self):
        pushes=[]
        def run(args,**kwargs):
            if args[1]=="push":
                pushes.append(args)
                return SimpleNamespace(returncode=0 if len(pushes)==3 else 1)
            return SimpleNamespace(returncode=1 if args[1]=="diff" else 0)
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"true"}),patch.object(r.subprocess,"run",side_effect=run),patch.object(r.time,"sleep"):
            self.assertTrue(r.save_checkpoint(1))
        self.assertEqual(len(pushes),3)
    def test_persistent_push_does_not_abort_data_collection(self):
        def run(args,**kwargs):return SimpleNamespace(returncode=1 if args[1]=="push" else 0)
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"true"}),patch.object(r.subprocess,"run",side_effect=run),patch.object(r.time,"sleep"):
            self.assertFalse(r.save_checkpoint(1))
if __name__=="__main__":unittest.main()
