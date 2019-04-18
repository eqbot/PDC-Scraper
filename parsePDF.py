import textract
from wand.image import Image
from requests import get
from bs4 import BeautifulSoup
from contextlib import closing
from io import BytesIO
import csv
import re

def simple_get(url):
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        print('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200 
            and content_type is not None 
            and content_type.find('html') > -1)

def parsePDF(fp):
    with Image() as img:
        img.read(file = fp, resolution = 200)
        for i in img.sequence:
            i.sample(2550, 3300)
        if len(img.sequence) > 1:
            firstimg = img.sequence[0]
            rest = img.sequence[1:]
        else:
            firstimg = img
        items = []
        #parse first page
        print(firstimg.size)
        for i in range(0, 5):
            with Image(firstimg) as addressfield, Image(firstimg) as donationfield:
                addressfield.crop(188, 986 + (166*i),width = 536, height=162)
                donationfield.crop(1232, 986 + (166*i), width = 202, height=162)
                try:
                    addressfield.save(filename='tmpaddress.jpg')
                    nameAddress = textract.process('tmpaddress.jpg', encoding='ascii', method='tesseract')
                    donationfield.save(filename='tmpdonation.jpg')
                    donation = textract.process('tmpdonation.jpg', encoding='ascii', method='tesseract')
                except UnboundLocalError:
                    print("had a pipe error")
                    continue
                nameAddress = str(nameAddress, 'utf-8').rstrip()
                lines = nameAddress.splitlines()
                if len(lines) == 0:
                    continue
                name = lines[0]
                donation = str(donation, 'utf-8').strip()
                donation = re.sub('[ ,]', '', donation)
                try:
                    donation = float(donation)
                except:
                    print("Failed to get relevant data for "+name+"donation value is "+donation)
                    img.save(filename='rustypeg.jpg')
                    continue
                items.append((name, '\n'.join(lines[1:]), donation))
        if items == []:
            return None
        return items

url = "https://www.pdc.wa.gov/reports/contributions_download?filer_id=HICKT%20%20354&election_year=2016"
resp = simple_get(url)
donors = []
if resp is None:
    print("Failed to get any HTML back.")
else:
    html = BeautifulSoup(resp, 'html.parser')
    csvfile = open('output.csv', 'w')
    csvwriter = csv.writer(csvfile)
    for link in html.select('a'):
        if(link.text == 'C3'):
            pdf = get(link['href'])
            if pdf.content is None:
                print("had trouble getting PDF")
                continue
            values = parsePDF(BytesIO(pdf.content))
            if values is None:
                continue
            for donor in values:
                if not donor in donors:
                    donors.append(donor)
                    csvwriter.writerow(donor)
