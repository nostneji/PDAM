# coding: utf-8

'''
Created on 08.11.2011

@author: Indrek
'''
from models import Pangadokument, Pangakirje, Konto, Tehingutyyp, Kontokasutus, Vara, Varatehing, Pearaamat, Tehing, Kanne, Algsaldo, date2str
from datetime import datetime, date
from varahaldur import VaraHaldur
from django.utils.encoding import smart_unicode
import re

def nvl(x, v):
    return v if x is None else x

def date2smart_unicode(d):
    return smart_unicode(d.day)+'.'+smart_unicode(d.month)+'.'+smart_unicode(d.year)

class BankLoader:
    '''
    Klass pangatehingute failide sisselugemiseks.
    Esimesel real on väljade nimed:
      "Kliendi konto";"Reatüüp";"Kuupäev";"Saaja/Maksja";"Selgitus";"Summa";
      "Valuuta";"Deebet/Kreedit";"Arhiveerimistunnus";"Tehingu tüüp";
      "Viitenumber";"Dokumendi number";
    '''

    def __init__(self):
        pass
    
    def make_pd(self, file_name):
        pd = Pangadokument()
        pd.import_aeg =  datetime.now()
        pd.failinimi = file_name
        pd.save()
        return pd.pk
        
    def read_csv(self, csv_file, pd_id):
        first = True
        pd = Pangadokument.objects.get(pk=pd_id)
        for l in csv_file:
            r = l.split(';')
            for i in range(len(r)):
                r[i] = str.strip(r[i],'"')
            if first: # First line is heading
                if r[0] == 'Kliendi konto':
                    first = False
            else:
                try:
                    k = Pangakirje()
                    k.pangakonto = r[0]
                    if r[1].isdigit():
                        k.reatyyp = int(r[1])
                    else:
                        k.reatyyp = 0
                    k.kuupaev = datetime.strptime(r[2],'%d.%m.%Y')
                    k.partner = r[3]
                    k.selgitus = r[4]
                    k.summa = r[5].replace(',', '.')
                    k.valuuta = r[6]
                    k.deebet = r[7]
                    k.arhiveerimistunnus = r[8]
                    k.tunnus = r[9]
                    k.viitenumber = r[10]
                    k.dokument = r[11]
                    k.arvestatud = 'N'
                    k.allikas = pd
                    k.save()
                except:
                    print k
                
class KontoLoader:
    '''
    Klass konto definitsioonide importimiseks ja eksportimiseks.
    '''                
    def import_kontoplaan(self, csv_file):
        for l in csv_file:
            if len(l.rstrip()) > 0:
                r = l.split(';')
                print r
                try:
                    k = Konto.objects.get(pk=r[1])
                    k.osa = r[0]
                    k.nimetus = r[2]
                    k.valuuta = r[3]
                    k.pangakonto = r[4].rstrip()
                except:
                    k = Konto(osa=r[0],kontonumber=r[1],nimetus=r[2],valuuta=r[3],pangakonto=r[4])
                k.save()
        return True
            
    def export_kontoplaan(self, csv_file):
        ks = Konto.objects.all().order_by('kontonumber')
        if csv_file.closed:
            return False
        for k in ks:
            csv_file.write(k.osa+';'+k.kontonumber+';'+k.nimetus.rstrip()+';'+k.valuuta+';'+nvl(k.pangakonto,'').rstrip()+'\n')
        csv_file.close()
        return True

class RuleLoader:
    '''
    Klass reeglite definitsioonide importimiseks ja eksportimiseks.
    '''                
    def import_rules(self, csv_file):
        tt_id = -1
        mtt = ''
        for l in csv_file:
            if len(l.rstrip()) > 0:
                r = l.split(';')
                print r
                if r[0] == 'TT':
                    if len(r) == 6 and r[5].rstrip() != '':
                        try:
                            tt = Tehingutyyp.objects.get(id=int(r[5].rstrip()))
                            tt.kirjeldus = r[1]
                            tt.reatyyp = int(r[2])
                            tt.tunnus = r[3]
                            tt.triger = r[4]
                            Kontokasutus.objects.all().filter(tehingutyyp=tt).delete()
                        except:
                            tts = Tehingutyyp.objects.all().filter(kirjeldus=r[1])
                            for t in tts:
                                Kontokasutus.objects.all().filter(tehingutyyp=t).delete()
                                t.delete()
                            tt = Tehingutyyp(kirjeldus=r[1], reatyyp=int(r[2]), tunnus=r[3], triger=r[4])
                    else:
                        tts = Tehingutyyp.objects.all().filter(kirjeldus=r[1])
                        for t in tts:
                            Kontokasutus.objects.all().filter(tehingutyyp=t).delete()
                            t.delete()
                        tt = Tehingutyyp(kirjeldus=r[1], reatyyp=int(r[2]), tunnus=r[3], triger=r[4])
                    tt.save()
                    tt_id = tt.id
                    mtt = tt
                elif r[0] == 'KK' and tt_id > 0:    
                    k = Konto.objects.get(pk=r[1])
                    Kontokasutus.objects.create(tehingutyyp=mtt, konto=k, on_deebet=(r[2]=='D'), valem=r[3].rstrip())
        return True
            
    def export_rules(self, csv_file):
        tts = Tehingutyyp.objects.all().order_by('kirjeldus')
        if csv_file.closed:
            return False
        for tt in tts:
            csv_file.write('TT;'+tt.kirjeldus+';'+smart_unicode(tt.reatyyp)+';'+nvl(tt.tunnus,'')+';'+nvl(tt.triger,'').rstrip()+';'+smart_unicode(tt.pk)+'\n')
            kks = Kontokasutus.objects.all().filter(tehingutyyp=tt).order_by('on_deebet')
            for kk in kks:
                csv_file.write('KK;'+kk.konto.kontonumber+';'+('D' if kk.on_deebet else 'K')+';'+nvl(kk.valem,'').rstrip()+'\n')
        csv_file.close()
        return True

class AssetLoader:
    '''
    Klass varatehingute importimiseks ja eksportimiseks.
    
    --> Formaat alates 2012 aastast:
    ['Tehingu ref.', 'Tehingu tüüp', 'Väärtuspäev', 'Teenustasu', 'V', 'Komisjoni tasu', 'V', 'Välisturu tasu', 'V', 'Finantstehingu maks', 'V', 'Tehingu summa', 'V', 'Hind', 'V', 'Kogus']

    '''                
    jooksev_aasta = date.today().year
    
    def setYear(self, year):
        self.jooksev_aasta = year

    def import_assets(self, csv_file):
        vh = VaraHaldur()
        vrec = {} # {nimetus, aldsaldo, id}
        trec = [] # (*tehing*)
        v_id = -1
        v = None
        delta = 0
        if self.jooksev_aasta >= 2012:
            delta = 2
        for l in csv_file:
            if len(l.rstrip()) > 0:
                r = l.split(';')
                for i in range(len(r)):
                    r[i] = r[i].strip('\"')
                print r[12+delta], r[12+delta].decode('utf8')
                if len(r) < 17: # vanemat tüüpi formaadiga fail
                    delta = 0
                if r[0] == 'Tehingu ref.': # faili päis
                    pass
                elif r[0].isdigit() and v_id >= 0: # tehingu kirje
                    print '>>> tehing'
                    if float(r[13+delta]) != 0:
                        if re.search('\+',r[1]):
                            tyyp = 'O'
                        elif re.search('-',r[1]):
                            tyyp = 'M'
                        elif re.search('%',r[1]):
                            tyyp = 'H'
                        elif float(r[13+delta]) > 0:
                            tyyp = 'O'
                        elif float(r[13+delta]) < 0:
                            tyyp = 'M'
                        s = r[2].split('.')
                        vkpv = date(int(s[2]), int(s[1]), int(s[0]))
                        summa = float(r[9+delta])
                        valuuta = r[10+delta]
                        kogus = float(r[13+delta])
                        trec.append({u'tüüp':tyyp, 'vkpv':vkpv, 'summa':summa, 'valuuta':valuuta, 'kogus':kogus})
                        print ' * ', trec
                elif r[0] == '' and r[12+delta] == 'Lõppsaldo' and v_id >= 0: # lõppsaldo
                    print '>>> lõpp ', vrec['algsaldo'], ' -> ', r[13+delta]
                    add_vt = False
                    if v_id == 0 and add_vt and float(r[13+delta]) > 0 and float(vrec['algsaldo']) > 0:
                        print 'WARNING: Missing previous data for ', vrec['nimetus'], vrec['algsaldo'], ' -> ', r[13+delta]
                    if v_id > 0:
                        add_vt = True
                    else:
                        for t in trec:
                            add_vt = add_vt or t['vkpv'].year >= self.jooksev_aasta
                    if v_id == 0 and float(vrec['algsaldo']) == 0:
                        lyh = vrec['lyhend'] if vrec['lyhend'] != '' else '?'
                        typ = vrec[u'tüüp'] if vrec[u'tüüp'] != '' else 'A'
                        v = Vara.objects.create(nimetus=vrec['nimetus'], vp_tyyp=typ, lyhend=lyh)
                        v_id = v.id
                        add_vt = True
                    print ' ** ', len(trec)
                    if add_vt: 
                        for t in trec:
                            if t[u'tüüp'] == 'O':
                                vh.buy(v.id, t['vkpv'], t['vkpv'], t['kogus'], t['summa'], t['valuuta'])   
                            elif t[u'tüüp'] == 'M':
                                vh.sell(v.id, t['vkpv'], t['vkpv'], t['kogus'], t['summa'], t['valuuta'])
                            elif t[u'tüüp'] == 'H':
                                vh.reprize(v.id, t['vkpv'], t['kogus'], t['summa'], t['valuuta'])
                    else:
                        print ' # Not added: ', vrec['nimetus']
                elif r[12+delta] == 'Algsaldo': # vara nimetus ja algsaldo
                    print '>>> algus'
                    try:
                        trec = []
                        v = Vara.objects.get(nimetus=r[0])
                        v_id = v.id
                        if r[8] == '':
                            r[8] = v.vp_tyyp
                        if r[10] == '':
                            r[10] = v.lyhend
                        print ' # Found: ', r[0]
                    except:
                        print ' # Not found, will create: ', r[0]
                        v = Vara.objects.create(nimetus=r[0], vp_tyyp=r[8], lyhend=r[10])
                        v_id = v.id
                    vrec = {'nimetus':r[0], 'algsaldo':r[13+delta], 'id':v_id, u'tüüp':r[8], 'lyhend':r[10]}
                    print vrec
                        
        return True
            
    def export_assetdeals(self, csv_file):
        delta = ''
        if self.jooksev_aasta >= 2012:
            delta = ';;'
        tts = Vara.objects.all().order_by('nimetus')
        if csv_file.closed:
            return False
        for tt in tts:
            csv_file.write(tt.nimetus+';;;;;;;;'+smart_unicode(tt.vp_tyyp)+';;'+tt.lyhend+delta+';;Algsaldo;0;\n'.encode('utf8'))
            kks = Varatehing.objects.all().filter(vara=tt).order_by('vaartuspaev','-tyyp','-kogus')
            lk = None
            for kk in kks:
                lk = kk
                if kk.tyyp == 'O':
                    tyyp = '+'
                elif kk.tyyp == 'M':
                    tyyp = '-'
                elif kk.tyyp == 'H':
                    tyyp = '%'
                csv_file.write('123;'+tyyp+';'+smart_unicode(kk.vaartuspaev.day)+'.'+smart_unicode(kk.vaartuspaev.month)+'.'+smart_unicode(kk.vaartuspaev.year)+
                               delta+';;;;;;;'+smart_unicode(kk.summa)+';'+kk.valuuta+';;;'+smart_unicode(kk.kogus)+';\n'.encode('utf8'))
            if lk != None:
                csv_file.write(delta+u';;;;;;;;;;;;Lõppsaldo;'+smart_unicode(lk.yldkogus)+';\n'.encode('utf8'))
        csv_file.close()
        return True
    
    def export_assets(self, kpv, csv_file):
        tts = Vara.objects.all().order_by('nimetus')
        if csv_file.closed:
            return False
        csv_file.write(u'POLARDATA OÜ VARAD seisuga '+smart_unicode(kpv.day)+'.'+smart_unicode(kpv.month)+'.'+smart_unicode(kpv.year)+'\n\n')
        tsh = 0
        tth = 0
        ash = 0
        ath = 0
        vsh = 0
        vth = 0
        ish = 0
        ith = 0
        for tt in tts:
            kks = Varatehing.objects.all().filter(vara=tt, vaartuspaev__lte=kpv).order_by('vaartuspaev','-tyyp','-kogus')
            lk = None
            for kk in kks:
                lk = kk
            if lk != None:
                if lk.yldkogus > 0:
                    tsh += float(lk.soetushind)
                    tth += float(lk.turuhind)
                    if tt.vp_tyyp == 'A':
                        ash += float(lk.soetushind)
                        ath += float(lk.turuhind)
                    elif tt.vp_tyyp == 'V':
                        vsh += float(lk.soetushind)
                        vth += float(lk.turuhind)
                    elif tt.vp_tyyp == 'I':
                        ish += float(lk.soetushind)
                        ith += float(lk.turuhind)
                    csv_file.write(tt.nimetus+'\t'+tt.vp_tyyp+'\t'+tt.lyhend+'\t'+smart_unicode(lk.yldkogus)+'\t'+
                                   smart_unicode(lk.soetushind)+'\t'+smart_unicode(lk.turuhind)+'\n'.encode('utf8'))
        csv_file.write(u'\nAktsiad:\t\t\t\t'+smart_unicode(ash)+'\t'+smart_unicode(ath)+'\n'.encode('utf8'))
        csv_file.write(u'Võlakirjad:\t\t\t\t'+smart_unicode(vsh)+'\t'+smart_unicode(vth)+'\n'.encode('utf8'))
        csv_file.write(u'Alt.inv.:\t\t\t\t'+smart_unicode(ish)+'\t'+smart_unicode(ith)+'\n'.encode('utf8'))
        csv_file.write(u'KOKKU:\t\t\t\t'+smart_unicode(tsh)+'\t'+smart_unicode(tth)+'\n'.encode('utf8'))

        csv_file.close()
        return True

class LedgerLoader:
    '''
    Klass pearaamatu kannete importimiseks ja eksportimiseks.
    '''                
    def import_ledger(self, csv_file):
        t_id = -1
        mt = None
        for l in csv_file:
            if len(l.rstrip()) > 0:
                r = l.split(';')
                print r
                if r[0] == 'T': # tehing
                    if len(r) == 8 and r[2].rstrip() != '':
                        t = None
                        try:
                            pr = Pearaamat.objects.get(aasta=int(r[1]))
                        except:
                            pr = Pearaamat()
                            pr.aasta = int(r[1])
                            pr.on_avatud = False
                            pr.save()
                        try:
                            tt = Tehingutyyp.objects.get(kirjeldus=r[2])
                        except:
                            tt = Tehingutyyp()
                            tt.kirjeldus = r[2]
                            tt.save()
                        try:
                            d = r[5].split('.')
                            vkpv = date(int(d[2]), int(d[1]), int(d[0]))
                            d = r[4].split('.')
                            tkpv = date(int(d[2]), int(d[1]), int(d[0]))
                            t = Tehing.objects.get(pearaamat=pr, tehingutyyp=tt, maksepaev=vkpv, sisu=r[3])
                            t.tehingupaev = tkpv
                            t.on_manual = r[6] == 'M'
                            Kanne.objects.all().filter(tehing=t).delete()
                        except:
                            t = Tehing(pearaamat=pr, tehingutyyp=tt, sisu=r[3], tehingupaev=tkpv, maksepaev=vkpv, on_manual=(r[6]=='M'))
                        finally:
                            t.save()
                            t_id = t.id
                            mt = t
                elif r[0] == 'K' and t_id > 0: # kanne    
                    k = Konto.objects.get(pk=r[1])
                    Kanne.objects.create(tehing=mt, konto=k, on_deebet=(r[2]=='D'), summa=float(r[3]), on_manual=(r[4]=='M'))
        return True
            
    def export_ledger(self, csv_file):
        ts = Tehing.objects.all().order_by('maksepaev')
        if csv_file.closed:
            return False
        for t in ts:
            csv_file.write('T;'+smart_unicode(t.pearaamat.aasta)+';'+t.tehingutyyp.kirjeldus+';'+t.sisu+';'+
                           date2smart_unicode(t.tehingupaev)+';'+date2smart_unicode(t.maksepaev)+';'+('M' if t.on_manual else 'A')+';\n')
            ks = Kanne.objects.all().filter(tehing=t).order_by('on_deebet')
            for k in ks:
                csv_file.write('K;'+k.konto.kontonumber+';'+('D' if k.on_deebet else 'K')+';'+smart_unicode(k.summa)+';'+
                               ('M' if k.on_manual else 'A')+';\n')
        csv_file.close()
        return True

    def export_ledger_table(self, csv_file, pr):
        if csv_file.closed:
            return False
        ts = Tehing.objects.all().filter(pearaamat=pr).order_by('maksepaev')
        ks = Konto.objects.all()
        # päis
        line = u'Kuupäev;Tehing;'
        for k in ks:
            if len(k.kontonumber) > 2:
                line = line + 'D-'+k.kontonumber+ ';K-'+k.kontonumber+';'
        csv_file.write(line+'\n')
        # algsaldo
        line = '1.1.'+smart_unicode(pr.aasta)+';ALGSALDO;'
        for k in ks:
            if len(k.kontonumber) > 2:
                sk = 0
                sd = 0
                kns = Algsaldo.objects.all().filter(pearaamat= pr,konto=k)
                for kn in kns:
                    if kn.on_deebet:
                        sd += float(kn.summa)
                    else:
                        sk += float(kn.summa)
                line = line + smart_unicode(round(sd,2)).replace('.', ',') + ';' + smart_unicode(round(sk,2)).replace('.', ',') + ';'
        csv_file.write(line+'\n')

        # tehingud
        kuu = 2
        ctrld = date(pr.aasta, kuu, 1)
        for t in ts:
            # vahesaldo
            if t.maksepaev >= ctrld:
                line = date2str(ctrld)+';SALDO '+smart_unicode(kuu-1)+u'. kuu järel;'
                for k in ks:
                    if len(k.kontonumber) > 2:
                        sk = 0
                        sd = 0
                        kns = Algsaldo.objects.all().filter(pearaamat= pr,konto=k)
                        for kn in kns:
                            if kn.on_deebet:
                                sd += float(kn.summa)
                            else:
                                sk += float(kn.summa)
                        kns = Kanne.objects.all().filter(tehing__pearaamat=pr, tehing__maksepaev__lt=ctrld, konto=k)
                        for kn in kns:
                            if kn.on_deebet:
                                sd += float(kn.summa)
                            else:
                                sk += float(kn.summa)
                        if k.osa in ('A','K'):
                            sld = sd - sk
                            if sld > 0:
                                sd = sld
                                sk = 0
                            else:
                                sk = abs(sld)
                                sd = 0
                        else:
                            sld = sk - sd
                            if sld > 0:
                                sk = sld
                                sd = 0
                            else:
                                sd = abs(sld)
                                sk = 0
                        line = line + smart_unicode(round(sd,2)).replace('.', ',') + ';' + smart_unicode(round(sk,2)).replace('.', ',') + ';'
                csv_file.write(line+'\n')
                if kuu < 12:
                    kuu += 1
                    ctrld = date(pr.aasta, kuu, 1)
                else:
                    ctrld = date(pr.aasta+1, 1, 1)
            # tehing    
            line = date2str(t.maksepaev)+';'+smart_unicode(t.sisu)+';'
            for k in ks:
                if len(k.kontonumber) > 2:
                    sk = 0
                    sd = 0
                    kns = Kanne.objects.all().filter(tehing=t,konto=k)
                    for kn in kns:
                        if kn.on_deebet:
                            sd += float(kn.summa)
                        else:
                            sk += float(kn.summa)
                    line = line + smart_unicode(round(sd,2)).replace('.', ',') + ';' + smart_unicode(round(sk,2)).replace('.', ',') + ';'
                    
            csv_file.write(line+'\n')
        # lõppsaldo
        line = '31.12.'+smart_unicode(pr.aasta)+u';LÕPPSALDO;'
        for k in ks:
            if len(k.kontonumber) > 2:
                sk = 0
                sd = 0
                kns = Algsaldo.objects.all().filter(pearaamat= pr,konto=k)
                for kn in kns:
                    if kn.on_deebet:
                        sd += float(kn.summa)
                    else:
                        sk += float(kn.summa)
                kns = Kanne.objects.all().filter(tehing__pearaamat=pr, konto=k)
                for kn in kns:
                    if kn.on_deebet:
                        sd += float(kn.summa)
                    else:
                        sk += float(kn.summa)
                if k.osa in ('A','K'):
                    sld = sd - sk
                    if sld > 0:
                        sd = sld
                        sk = 0
                    else:
                        sk = abs(sld)
                        sd = 0
                else:
                    sld = sk - sd
                    if sld > 0:
                        sk = sld
                        sd = 0
                    else:
                        sd = abs(sld)
                        sk = 0
                line = line + smart_unicode(round(sd,2)).replace('.', ',') + ';' + smart_unicode(round(sk,2)).replace('.', ',') + ';'
        csv_file.write(line+'\n')
        csv_file.close()
        return True

