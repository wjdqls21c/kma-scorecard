import datetime as dt,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"collector"))
import seoul_october as m
class OctoberTests(unittest.TestCase):
    def test_exact_month_and_horizon(self):
        rows=[r for d in range(1,32) for r in m.requests_for_day(d)]
        self.assertEqual(len(rows),992)
        self.assertEqual(len({r[0] for r in rows}),248)
        self.assertTrue(all((v-i)==dt.timedelta(hours=24) for v,i,*_ in rows))
        self.assertEqual(rows[0][0].isoformat(),"2026-10-01T02:00:00+09:00")
        self.assertEqual(rows[-1][0].isoformat(),"2026-10-31T23:00:00+09:00")
    def test_build_and_missing_date_gate(self):
        old=m.DIR
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m.DIR=root/"archive";dist=root/"dist"
            try:
                with self.assertRaises(ValueError):m.build(dist)
                for day in range(1,32):
                    responses={}
                    for valid,issued,kind,endpoint,params in m.requests_for_day(day):
                        responses[valid.strftime("%Y%m%d%H")+"-"+kind]=dict(value=18 if kind in ("TMP","T1H") else 0,sha256="a"*64,bytes=341297,endpoint=endpoint,parameters=params)
                    m.write(m.DIR/f"{day:02}.json",dict(complete=True,responses=responses,usage=dict(attempts=32,receivedBytes=32*341297,failedAttempts=0)))
                report=m.build(dist)
                self.assertEqual(report["attempts"],992)
                d=json.loads((dist/"history/2026-10-api/seoul.json").read_text())
                self.assertEqual(len(d["forecasts"]),248)
                self.assertEqual(d["observations"][0]["temp"],18)
                day=m.read(m.DIR/"01.json",{});next(iter(day["responses"].values()))["parameters"]={}
                m.write(m.DIR/"01.json",day)
                with self.assertRaisesRegex(ValueError,"provenance"):m.build(dist)
            finally:m.DIR=old
if __name__=="__main__":unittest.main()
