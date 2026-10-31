import datetime as dt
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('collector',Path(__file__).resolve().parents[1]/'collector/collect.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class CollectorTests(unittest.TestCase):
    def test_publication_delay(self):
        now=dt.datetime(2026,11,1,2,20,tzinfo=c.KST)
        self.assertEqual(c.forecast_base(now).isoformat(),'2026-10-31T23:00:00+09:00')
    def test_missing_not_zero(self):
        for value in ('',None,'-999','강수없음','1mm 미만','nan'):
            self.assertIsNone(c.numeric(value,0,1000))
        self.assertEqual(c.numeric('0',0,1000),0)
    def test_forecast_join_and_grid_guard(self):
        base=dt.datetime(2026,10,31,23,tzinfo=c.KST)
        rows=[dict(baseDate='20261031',baseTime='2300',fcstDate='20261101',fcstTime='2300',nx=71,ny=121,category=k,fcstValue=v) for k,v in [('TMP','15'),('POP','60')]]
        parsed=c.parse_forecast(rows,'yeoju',base,base+dt.timedelta(hours=1),71,121)
        self.assertEqual(len(parsed),1);self.assertEqual(parsed[0]['temp'],15)
        with self.assertRaises(ValueError): c.parse_forecast(rows,'yeoju',base,base,60,127)
        with self.assertRaises(ValueError): c.parse_forecast(rows,'yeoju',base,base+dt.timedelta(days=1),71,121)
    def test_observation_timestamp(self):
        valid=dt.datetime(2026,11,1,23,tzinfo=c.KST)
        rows=[dict(baseDate='20261101',baseTime='2300',nx=71,ny=121,category=k,obsrValue=v) for k,v in [('T1H','15'),('RN1','-999')]]
        o=c.parse_observation(rows,'yeoju',valid,71,121)
        self.assertEqual(o['temp'],15);self.assertIsNone(o['rainMm'])
        with self.assertRaises(ValueError): c.parse_observation(rows,'yeoju',valid-dt.timedelta(hours=1),71,121)
if __name__=='__main__':unittest.main()
