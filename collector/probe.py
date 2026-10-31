"""One short API check; emit only an allowlisted diagnostic status."""
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collect import BASE,KST,forecast_base
key=os.environ.get('KMA_SERVICE_KEY','').strip()
if not key:
    print('KMA_PROBE: MISSING_SECRET')
    raise SystemExit(1)
now=dt.datetime.now(KST);base=forecast_base(now)
params=dict(serviceKey=urllib.parse.unquote(key),dataType='JSON',numOfRows=10,pageNo=1,base_date=base.strftime('%Y%m%d'),base_time=base.strftime('%H%M'),nx=71,ny=121)
try:
    request=urllib.request.Request(BASE+'getVilageFcst?'+urllib.parse.urlencode(params),headers={'User-Agent':'KMA-scorecard/0.1'})
    with urllib.request.urlopen(request,timeout=12) as res:
        body=res.read(100000)
    try:
        data=json.loads(body)['response'];code=str(data['header']['resultCode'])
        safe_code=code if code.isdigit() and len(code)<=5 else 'OTHER'
        print('KMA_PROBE: API_CODE_'+safe_code)
        if code=='00':
            rows=data['body'].get('items',{}).get('item',[])
            print('KMA_PROBE: VALID_FORECAST_ROWS_'+str(len(rows)))
            raise SystemExit(0)
    except (ValueError,KeyError,TypeError):
        # XML errors also use a known numeric result code; do not print response text.
        print('KMA_PROBE: NON_JSON_RESPONSE')
except urllib.error.HTTPError as error:
    print('KMA_PROBE: HTTP_'+str(error.code))
    body=error.read(100000)
    known=('SERVICE_KEY_IS_NOT_REGISTERED_ERROR','SERVICE_KEY_IS_NOT_REGISTED_ERROR','SERVICE_ACCESS_DENIED_ERROR','IP_IS_NOT_REGISTERED_ERROR','LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR','SERVICE_KEY_IS_NOT_AVAILABLE_ERROR','HTTP_ROUTING_ERROR')
    decoded=body.decode('utf-8',errors='replace')
    found=False
    for message in known:
        if message in decoded:
            print('KMA_PROBE: '+message);found=True
    try:
        root=ET.fromstring(body)
        for tag in ('returnReasonCode','returnAuthMsg','resultCode'):
            value=root.findtext('.//'+tag,'')
            if value.isdigit() and len(value)<=5:
                print('KMA_PROBE: XML_CODE_'+value);found=True
    except ET.ParseError:pass
    if not found:print('KMA_PROBE: UNCLASSIFIED_HTTP_ERROR')
except Exception as error:
    print('KMA_PROBE: TRANSPORT_FAILURE_'+type(error).__name__)
raise SystemExit(1)
