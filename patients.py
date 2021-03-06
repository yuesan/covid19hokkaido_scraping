import re
import datetime
import urllib.request
from bs4 import BeautifulSoup

START_YEAR = 2020
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')


class PatientsReader:
    def __init__(self, url='http://www.pref.hokkaido.lg.jp/hf/kth/kak/hasseijoukyou.htm'):
        opener = urllib.request.build_opener()
        opener.addheaders = [
            ('Referer', 'http://localhost'),
            ('User-Agent',
             'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36 Edg/79.0.309.65'),
        ]

        html = opener.open(url)
        bs = BeautifulSoup(html, 'html.parser')

        table = bs.findAll('table')[0]
        trs = table.findAll('tr')

        table_data = []
        for i in range(len(trs)):
            cells = trs[i].findAll(['td', 'th'])
            row = []
            for cell in cells:
                cell_str = cell.get_text()
                # header cleaning
                if i == 0:
                    cell_str = cell_str.replace(' ', '').replace(' ', '')
                row.append(cell_str)
            table_data.append(row)

        self.data = table_data
        self.date = datetime.datetime.now(JST).isoformat()

    def make_patients_dict(self):
        patients = {
            'last_update': self.date,
            'data': []
        }

        # patients data
        headers = self.data[0]
        maindatas = self.data[1:]
        patients_data = []

        # rewrite header 公表日 as リリース日
        for i in range(len(headers)):
            if headers[i] == '公表日':
                headers[i] = 'リリース日'
                break

        prev_month = 0  # to judge whether now is 2020 or more
        for data in maindatas:
            dic = {}
            for i in range(len(headers)):
                # translate MM/DD to ISO-8601 datetime
                if headers[i] == 'リリース日':
                    md = data[i].split('/')
                    year = START_YEAR
                    month = int(md[0])
                    day = int(md[1])

                    # 2021 or more
                    if month < prev_month:
                        year = START_YEAR + 1

                    date = datetime.datetime(year, month, day, tzinfo=JST)
                    date_str = date.isoformat()
                    prev_month = month
                    # rewrite 公表日 as リリース日
                    dic['date'] = date_str
                elif headers[i] == 'No.':
                    dic['no'] = int(
                        data[i].translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})))
                elif headers[i] == '年代':
                    dic['age'] = data[i]
                elif headers[i] == '性別':
                    dic['sex'] = data[i].strip()
                elif headers[i] == '居住地':
                    dic['place'] = data[i].replace('\n', '').replace('\r', '')
                elif headers[i] == '周囲の患者の発生':
                    dic['other_patient'] = data[i].replace('\n', ' ').replace('\r', '')
                elif headers[i] == '濃厚接触者の状況':
                    dic['contact_person'] = data[i].replace('\n', '').replace('\r', '')
                else:
                    dic['others'] = data[i]

            patients_data.append(dic)

        patients['data'] = patients_data
        return patients

    def make_patients_summary_dict(self):
        patients = self.make_patients_dict()
        summary = self.calc_patients_summary(patients)
        patients_summary = {'data': summary, 'last_update': self.date}
        return patients_summary

    # sample:最終更新日：2020年3月05日（木）
    def parse_datetext(self, datetext: str) -> str:
        parsed_date = re.split('[^0-9]+', datetext)[1:4]
        year = int(parsed_date[0])
        month = int(parsed_date[1])
        day = int(parsed_date[2])
        date = datetime.datetime(year, month, day, tzinfo=JST)
        date_str = date.isoformat()
        return date_str

    def calc_patients_summary(self, patients: dict) -> list:
        summary = []

        start_day = patients['data'][0]['date']
        start_datetime = datetime.datetime.fromisoformat(start_day)

        end_datetime = datetime.datetime.fromisoformat(patients['last_update'])
        while start_datetime <= end_datetime:
            day = {
                'date': '',
                'subtotal': 0
            }
            day['date'] = start_datetime.isoformat()

            for p in patients['data']:
                if p['date'] == day['date']:
                    day['subtotal'] = day['subtotal'] + 1

            summary.append(day)
            start_datetime = start_datetime + datetime.timedelta(days=1)

        return summary
