# coding: utf-8
'''
Created on 20.06.2012

@author: Indrek
'''
import httplib, urllib, urllib2
from datetime import date 

class Currency(object):
    '''
    Klass valuutakursside leidmiseks ja valuutade teisendamiseks.
    '''
    breakpoint = date(2011,1,1) # Eurole üleminek

    def __init__(self):
        pass
    
    def ask_page(self, token, tval, on_date):
        #print '++ ask_page ', on_date.strftime('%d.%m.%Y'), on_date
        params = urllib.urlencode({token: tval
            , 'pageId': 'private.d2d.payments.rates.archive'
            , 'encoding': 'UTF-8'
            , 'language': 'EST'
            , 'raw': 'false'
            , 'selectType': '1'
            , 'dateBeg': on_date.strftime('%d.%m.%Y') 
            , 'send': 'Saada päring'})
        headers = {"Content-type": "application/x-www-form-urlencoded",
                "Accept": "text/plain"}
        req = urllib2.Request("https://www.swedbank.ee/private/d2d/payments/rates/archive", params, headers)
        r = urllib2.urlopen(req)
        page = r.read()
        r.close()
        return page
                
    def rate(self, on_date, from_cur, to_cur):
        token = 'SWEDTKK3OFQ6SWM5GLYML44UMSCBNOQB2W2OX'
        tval = '012810'
        page = self.ask_page(token, tval, on_date)
        #print page
        #print len(page)
        s = page.find("tblRates")
        counts = 10
        while s < 0 and counts > 0:
            # vaja võtta uus token ja küsida uuesti
            tokv_s = page.find("mainForm\">")
            #print page[tokv_s:tokv_s+50]
            tokv_s = page.find('value=', tokv_s)
            tokv_s = page.find('"', tokv_s)
            tokv_e = page.find('"', tokv_s+1)
            tval = page[tokv_s+1:tokv_e]
            tokv_s = page.find('name=', tokv_s)
            tokv_s = page.find('"', tokv_s)
            tokv_e = page.find('"', tokv_s+1)
            token = page[tokv_s+1:tokv_e]
            #print token, tval
            page = self.ask_page(token, tval, on_date)
            s = page.find("tblRates")
            counts -= 1
        if s < 0:
            print ' Viga?', on_date, from_cur, to_cur
            return 0
        #print page
        #print s
        if on_date >= self.breakpoint:
            current = 'EUR'
        else:
            current = 'EEK'
        from_rate = 1.0
        if from_cur.upper() != current: 
            from_s = page.find(from_cur.upper(), s)
            #print from_cur, from_s
            if from_s > s:
                for i in range(1,5):
                    from_s = page.find('<td', from_s+3)
                from_s = page.find('>', from_s)
                from_e = page.find('<', from_s)
                from_rate = page[from_s+1:from_e]
        to_rate = 1.0
        if to_cur.upper() != current: 
            to_s = page.find(to_cur.upper(), s)
            #print to_cur, to_s
            if to_s > s:
                for i in range(1,5):
                    to_s = page.find('<td', to_s+3)
                to_s = page.find('>', to_s)
                to_e = page.find('<', to_s)
                to_rate = page[to_s+1:to_e]
        #print ' rates:', from_rate, to_rate
        if current == 'EUR':
            rate = 1/float(from_rate) * float(to_rate)
        else:
            rate = (float(from_rate) * 1/float(to_rate))
        #print ' rate:', on_date, from_cur, to_cur, '->', rate
        return rate
    
    def convert(self, on_date, from_cur, to_cur, from_val):
        to_val = from_val * self.rate(on_date, from_cur, to_cur)
        #print ' convert:', on_date, from_cur, to_cur, from_val, '->', to_val
        return to_val
    
