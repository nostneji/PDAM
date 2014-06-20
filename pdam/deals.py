# coding: utf-8

'''
Created on 20.06.2012

@author: Indrek
'''
from models import Pangadokument, Pangakirje, Konto, Tehingutyyp, Kontokasutus, Pearaamat, Tehing, Kanne, Vara, Algsaldo
from django.db import transaction
from datetime import date
from currencies import Currency
from django.db.models import Sum
from decimal import Decimal
from varahaldur import VaraHaldur
from datalog import Datalog
from django.utils.encoding import smart_unicode
import re
import codecs
import ast

def nvl(x, v):
    return v if x is None else x

def RP_korras(tehing):
    '''
    Kontrollime RP võrrandi (Vara + Kulud = Kohustised + Omakapital + Tulud) kehtivust.
    '''
    if re.search('Tehing', str(type(tehing))):
        AD = Kanne.objects.filter(tehing=tehing, konto__valuuta='EUR', konto__osa='A', on_deebet=True).aggregate(Sum('summa'))['summa__sum']
        AK = Kanne.objects.filter(tehing=tehing, konto__valuuta='EUR', konto__osa='A', on_deebet=False).aggregate(Sum('summa'))['summa__sum']
        AS = nvl(AD,0) - nvl(AK,0)
        PK = Kanne.objects.filter(tehing=tehing, konto__valuuta='EUR', konto__osa='P', on_deebet=False).aggregate(Sum('summa'))['summa__sum']
        PD = Kanne.objects.filter(tehing=tehing, konto__valuuta='EUR', konto__osa='P', on_deebet=True).aggregate(Sum('summa'))['summa__sum']
        PS = nvl(PK,0) - nvl(PD,0)
        KD = Kanne.objects.filter(tehing=tehing, konto__valuuta='EUR', konto__osa='K', on_deebet=True).aggregate(Sum('summa'))['summa__sum']
        KK = Kanne.objects.filter(tehing=tehing, konto__valuuta='EUR', konto__osa='K', on_deebet=False).aggregate(Sum('summa'))['summa__sum']
        KS = nvl(KD,0) - nvl(KK,0)
        TK = Kanne.objects.filter(tehing=tehing, konto__valuuta='EUR', konto__osa='T', on_deebet=False).aggregate(Sum('summa'))['summa__sum']
        TD = Kanne.objects.filter(tehing=tehing, konto__valuuta='EUR', konto__osa='T', on_deebet=True).aggregate(Sum('summa'))['summa__sum']
        TS = nvl(TK,0) - nvl(TD,0)
    elif re.search('Pearaamat', str(type(tehing))):
        AD = Algsaldo.objects.filter(pearaamat=tehing, konto__valuuta='EUR', konto__osa='A', on_deebet=True).aggregate(Sum('summa'))['summa__sum']
        AK = Algsaldo.objects.filter(pearaamat=tehing, konto__valuuta='EUR', konto__osa='A', on_deebet=False).aggregate(Sum('summa'))['summa__sum']
        AS = nvl(AD,0) - nvl(AK,0)
        PK = Algsaldo.objects.filter(pearaamat=tehing, konto__valuuta='EUR', konto__osa='P', on_deebet=False).aggregate(Sum('summa'))['summa__sum']
        PD = Algsaldo.objects.filter(pearaamat=tehing, konto__valuuta='EUR', konto__osa='P', on_deebet=True).aggregate(Sum('summa'))['summa__sum']
        PS = nvl(PK,0) - nvl(PD,0)
        KD = Algsaldo.objects.filter(pearaamat=tehing, konto__valuuta='EUR', konto__osa='K', on_deebet=True).aggregate(Sum('summa'))['summa__sum']
        KK = Algsaldo.objects.filter(pearaamat=tehing, konto__valuuta='EUR', konto__osa='K', on_deebet=False).aggregate(Sum('summa'))['summa__sum']
        KS = nvl(KD,0) - nvl(KK,0)
        TK = Algsaldo.objects.filter(pearaamat=tehing, konto__valuuta='EUR', konto__osa='T', on_deebet=False).aggregate(Sum('summa'))['summa__sum']
        TD = Algsaldo.objects.filter(pearaamat=tehing, konto__valuuta='EUR', konto__osa='T', on_deebet=True).aggregate(Sum('summa'))['summa__sum']
        TS = nvl(TK,0) - nvl(TD,0)
         
    result = {'Aktiva':float(AS), 'Passiva':float(PS), 'Tulud':float(TS), 'Kulud':float(KS), 
              'RP': round(float(AS) + float(KS) - float(PS) - float(TS),2)}
    return result

def findBIL(pr):
    akpv = date(pr.aasta, 1, 1)
    lkpv = date(pr.aasta, 12, 31)
    vtx = []
    tot = []
    # Aktiva
    mks = Konto.objects.all().filter(valuuta='EUR', osa='A')
    KAS = Decimal(0)
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                AD = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                AK = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                SK = nvl(AD,0) - nvl(AK,0) + nvl(DS,0) - nvl(KS,0)
                tot.append({'osa':k.osa,'konto': k.kontonumber + ':'+ k.nimetus, 'summa': float(SK), 'pk':k.kontonumber})
                MA = MA + SK
            if round(float(MA),0) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': float(MA)})
                KAS = KAS + MA
    vtx.append({'osa':'A','konto': 'AKTIVA KOKKU', 'summa': float(KAS)})
    # Passiva
    mks = Konto.objects.all().filter(valuuta='EUR', osa='P')
    KAS = Decimal(0)
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                AD = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                AK = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                SK = nvl(AK,0) - nvl(AD,0) + nvl(KS,0) - nvl(DS,0) 
                tot.append({'osa':k.osa,'konto': k.kontonumber + ':'+ k.nimetus, 'summa': float(SK), 'pk':k.kontonumber})
                MA = MA + SK
            if round(float(MA),0) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': float(MA)})
                KAS = KAS + MA
    vtx.append({'osa':'P','konto': 'PASSIVA KOKKU', 'summa': float(KAS)})
    # Tulud
    mks = Konto.objects.all().filter(valuuta='EUR', osa='T')
    KAS = Decimal(0)
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                AD = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                AK = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                SK = nvl(AK,0) - nvl(AD,0) + nvl(KS,0) - nvl(DS,0) 
                tot.append({'osa':k.osa,'konto': k.kontonumber + ':'+ k.nimetus, 'summa': float(SK), 'pk':k.kontonumber})
                MA = MA + SK
            if round(float(MA),0) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': float(MA)})
                KAS = KAS + MA
    vtx.append({'osa':'T','konto': 'TULUD KOKKU', 'summa': float(KAS)})
    # Kulud
    mks = Konto.objects.all().filter(valuuta='EUR', osa='K')
    KAS = Decimal(0)
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                AD = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                AK = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                SK = nvl(AD,0) - nvl(AK,0) + nvl(DS,0) - nvl(KS,0)
                tot.append({'osa':k.osa,'konto': k.kontonumber + ':'+ k.nimetus, 'summa': float(SK), 'pk':k.kontonumber})
                MA = MA + SK
            if round(float(MA),0) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': float(MA)})
                KAS = KAS + MA
    vtx.append({'osa':'K','konto': 'KULUD KOKKU', 'summa': float(KAS)})
    return (vtx, tot)

def aastaSulgemine(cpr):
    if cpr.on_avatud:
        cpr.on_avatud = False
        cpr.save()
        prs = Pearaamat.objects.all().filter(aasta=cpr.aasta+1)
        if len(prs) == 0:
            npr = Pearaamat.objects.create(aasta=cpr.aasta+1, on_avatud=True)
        else:
            npr = Pearaamat.objects.get(aasta=cpr.aasta+1, on_avatud=True)
    else:
        npr = Pearaamat.objects.get(aasta=cpr.aasta+1, on_avatud=True)
    data = findBIL(cpr)
    ks = data[1]
    for k in ks:
        if k['summa'] != 0 and k['osa'] in ('A','P'):
            kt = Konto.objects.get(pk=k['pk'])
            if k['osa'] == 'A':
                l_deebet = k['summa'] > 0
            elif k['osa'] == 'P':
                l_deebet = k['summa'] < 0
            try:
                ask = Algsaldo.objects.get(pearaamat=npr, konto=kt, on_deebet=l_deebet)
                if not ask.on_manual and not ask.on_fikseeritud:
                    ask.summa = abs(k['summa'])
                    ask.save()
            except Algsaldo.DoesNotExist:
                Algsaldo.objects.create(pearaamat=npr, konto=kt, on_deebet=l_deebet, summa=abs(k['summa']), on_manual=False, on_fikseeritud=False)
    return
    
def tuluKuluSulgemine(pr):
    tt = Tehingutyyp.objects.get(kirjeldus='Tulu- ja kulukontode sulgemine')
    dt = date(pr.aasta, 12, 31)
    tse = Tehing.objects.all().filter(pearaamat=pr, tehingutyyp=tt, tehingupaev=dt, maksepaev=dt, on_manual=True)
    for ts in tse:
        Kanne.objects.all().filter(tehing=ts).delete()
        ts.delete()
    data = findBIL(pr)
    ks = data[1]
    t = Tehing.objects.create(pearaamat=pr, tehingutyyp=tt, sisu=tt.kirjeldus, tehingupaev=dt, maksepaev=dt, on_manual=True)
    TDS = 0
    KKS = 0
    for k in ks:
        l_deebet = True
        l_summa = 0
        kt = Konto.objects.get(pk=k['pk'])
        if k['osa'] == 'T':
            if k['summa'] != 0:
                l_summa=k['summa']
                TDS += l_summa
        elif k['osa'] == 'K':
            if k['summa'] != 0:
                l_summa=k['summa']
                l_deebet = False
                KKS += l_summa
        if l_summa != 0:
            Kanne.objects.create(tehing=t, konto=kt, on_deebet=l_deebet, summa=l_summa, on_manual=True)
    kt = Konto.objects.get(pk='272')
    # kulud 272 D
    Kanne.objects.create(tehing=t, konto=kt, on_deebet=True, summa=KKS, on_manual=True)
    # tulud 272 K
    Kanne.objects.create(tehing=t, konto=kt, on_deebet=False, summa=TDS, on_manual=True)
    return

def kasumiAruanne(pr):
    skeem1 = ((u'  Müügitulu', 'I', '31'),
              (u'  Muud äritulud', 'I', '32', '34'),
              (u' Tulud kokku', 'S', '31', '32', '34'),
              (u'  Kaubad, toore, materjal, teenused', 'I', '41'),
              (u'  Mitmesugused tegevuskulud', 'I', '42'),
              (u'  Tööjõu kulud', 'I', '43'),
              (u'  Põhivara kulum', 'I', '44'),
              (u'  Muud ärikulud', 'I', '45', '47'),
              (u' Kulud kokku', 'S', '41', '42', '43', '44', '45', '47'),
              (u'Ärikasum (-kahjum)', 'T', '31', '32', '34', '41', '42', '43', '44', '45', '47'),
              (u' Finantstulud ja -kulud', 'S', '33', '46'),
              (u'Kasum (kahjum) enne tulumaksustamist', 'T', '31', '32', '34', '41', '42', '43', '44', '45', '47', '33', '46'),
              (u'Aruandeaasta kasum (kahjum)', 'T', '31', '32', '34', '41', '42', '43', '44', '45', '47', '33', '46'),
              )
    fin = ((u'Intressitulud','I','337'),
           (u'Kasum (kahjum) valuutakursi muutustest', 'I', '3361', '4661'),
           (u'Muud finantstulud ja -kulud', 'I', '3351','3352','339','468','469'),
           (u'Väärtpaberite müügikasum', 'I', '338'),
           (u'Väärtpaberite müügikahjum', 'I', '467'), 
           (u'Kokku finantstulud ja -kulud', 'T', '337', '3361', '4661', '3351','3352','339','468','469', '338', '467')
           )    
    akpv = date(pr.aasta, 1, 1)
    lkpv = date(pr.aasta, 12, 31)
    vtx = []
    tot = []
    txs = Tehing.objects.all().filter(pearaamat=pr, tehingutyyp__kirjeldus='Tulu- ja kulukontode sulgemine')
    TX = 0
    for x in txs:
        TX = x
    # Tulud
    mks = Konto.objects.all().filter(valuuta='EUR', osa='T')
    KAS = Decimal(0)
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                AD = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                AK = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                SK = nvl(AK,0) - nvl(AD,0) + nvl(KS,0) - nvl(DS,0) 
                tot.append({'osa':k.osa,'konto': k.nimetus, 'summa': float(SK), 'pk':k.kontonumber})
                MA = MA + SK
            if round(float(MA),0) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': float(MA), 'pk': mk.kontonumber})
                KAS = KAS + MA
    vtx.append({'osa':'T','konto': 'TULUD KOKKU', 'summa': float(KAS), 'pk': mk.kontonumber[0]})
    # Kulud
    mks = Konto.objects.all().filter(valuuta='EUR', osa='K')
    KAS = Decimal(0)
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                AD = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                AK = Algsaldo.objects.filter(pearaamat=pr, konto=k, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                SK = nvl(AD,0) - nvl(AK,0) + nvl(DS,0) - nvl(KS,0)
                tot.append({'osa':k.osa,'konto': k.nimetus, 'summa': float(SK), 'pk':k.kontonumber})
                MA = MA + SK
            if round(float(MA),0) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': float(MA), 'pk': mk.kontonumber})
                KAS = KAS + MA
    vtx.append({'osa':'K','konto': 'KULUD KOKKU', 'summa': float(KAS), 'pk': mk.kontonumber[0]})
    
    kas = []
    for r in skeem1:
        r_sum = 0
        for s in vtx:
            x = s['pk'] 
            if x in r[2:]:
                r_sum += s['summa'] * (-1 if s['osa']=='K' else 1)
        if r_sum != 0:
            kas.append({'konto': r[0], 'Fmt': r[1], 'summa': float(r_sum)})
            
    ftk = []
    for r in fin:
        r_sum = 0
        for s in tot:
            x = s['pk'] 
            if x in r[2:]:
                r_sum += s['summa'] * (-1 if s['osa']=='K' else 1)
        if r_sum != 0:
            ftk.append({'konto': r[0], 'Fmt': r[1], 'summa': float(r_sum)})
            
    return (kas, ftk, tot)
    
def rahavoogudeAruanne(pr):
    sk = ((u'Väljamaksed tarnijatele kaupade ja teenuste eest','I', '#a', '41' ),
          (u'Väljamaksed töötajatele','I', '#b', '4311'),
          (u'Muud rahavood äritegevusest','I', '#c','4321','4322','4323','4324','4325','4351','4353','4355'),
          (u'Kokku rahavood äritegevusest','S', '#d','41','43'),
          (u'Tasutud muude finantsinvesteeringute soetamisel','I', '#e','?OstSum'),
          (u'Laekunud muude finantsinvesteeringute müügist','I', '#f','?MyykSum'),
          (u'Laekunud intressid','I', '#g','337'),
          (u'Laekunud dividendid','I', '#h','3352'),
          (u'Muud laekumised investeerimistegevusest','I', '#u','339' ),
          (u'Muud väljamaksed investeerimistegevusest','I', '#i','4264','469' ),
          (u'Kokku rahavood investeerimistegevusest','S', '#j', ':e',':f',':g',':h',':i',':u'),
          (u'Saadud laenud','I', '#k', '?K251'),
          (u'Saadud laenude tagasimaksed','I', '#l', '?D251'),
          (u'Kokku rahavood finantseerimistegevusest','S', '#m', ':k', ':l'),
          (u'Kokku rahavood','T', '#n', ':d', ':j', ':m'),
          (u'Raha ja raha ekvivalendid perioodi alguses','I', '#o', '?A1131', '?A1132', '?A1133','?A115'),
          (u'Valuutakursside muutuste mõju','I', '#r', '3361', '4661'),
          (u'Raha ja raha ekvivalentide muutus','T', '#p', '1131', '1132', '1133', '115', ':r-'),
          (u'Raha ja raha ekvivalendid perioodi lõpus','I', '#s', ':o', ':p', ':r' ),
          (u'Kontroll: rahavood vs raha muutus','I', '#t', ':n', ':p-')
          )
    akpv = date(pr.aasta, 1, 1)
    lkpv = date(pr.aasta, 12, 31)
    vtx = []
    tot = []
    txs = Tehing.objects.all().filter(pearaamat=pr, tehingutyyp__kirjeldus='Tulu- ja kulukontode sulgemine')
    TX = 0
    for x in txs:
        TX = x
    # Aktiva
    mks = Konto.objects.all().filter(valuuta='EUR', osa='A')
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                if len(k.kontonumber) > 2:
                    DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                    KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                    SK = nvl(DS,0) - nvl(KS,0)
                    tot.append({'osa':k.osa,'konto': k.nimetus, 'summa': round(float(SK),2), 'pk':k.kontonumber})
                    MA = MA + SK
            if round(float(MA),2) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': round(float(MA),2), 'pk': mk.kontonumber})
    # Tulud
    mks = Konto.objects.all().filter(valuuta='EUR', osa='T')
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                if len(k.kontonumber) > 2:
                    DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                    KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                    SK = nvl(KS,0) - nvl(DS,0) 
                    tot.append({'osa':k.osa,'konto': k.nimetus, 'summa': round(float(SK),2), 'pk':k.kontonumber})
                    MA = MA + SK
            if round(float(MA),2) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': round(float(MA),2), 'pk': mk.kontonumber})
    # Kulud
    mks = Konto.objects.all().filter(valuuta='EUR', osa='K')
    for mk in mks:
        if len(mk.kontonumber) == 2:
            ks = Konto.objects.all().filter(valuuta='EUR', osa=mk.osa, kontonumber__startswith=mk.kontonumber)
            MA = Decimal(0)
            for k in ks:
                if len(k.kontonumber) > 2:
                    DS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                    KS = Kanne.objects.filter(konto=k, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                    SK = nvl(DS,0) - nvl(KS,0)
                    tot.append({'osa':k.osa,'konto': k.nimetus, 'summa': round(float(SK),2), 'pk':k.kontonumber})
                    MA = MA + SK
            if round(float(MA),2) != 0:
                vtx.append({'osa':mk.osa,'konto': mk.nimetus, 'summa': round(float(MA),2), 'pk': mk.kontonumber})
    rva = []
    mem = {}
    for r in sk:
        r_sum = 0
        for s in vtx:
            x = s['pk'] 
            if x in r[3:]:
                r_sum += s['summa'] * (-1 if s['osa']=='K' else 1)
        for s in tot:
            x = s['pk'] 
            if x in r[3:]:
                r_sum += s['summa'] * (-1 if s['osa']=='K' else 1)
        for s in r[3:]:
            if s[0] == '?': # function
                if s == '?OstSum':
                    tt = Tehingutyyp.objects.get(kirjeldus=u'Väärtpaberi ostmine')
                    for kn in ('1132','115'):
                        kt = Konto.objects.get(pk=kn)
                        ks = Kanne.objects.all().filter(konto=kt, tehing__tehingutyyp=tt, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                        r_sum += float(nvl(ks, 0) * (-1 if kt.osa in ('A', 'K') else 1))
                elif s == '?MyykSum':
                    tt = Tehingutyyp.objects.get(kirjeldus=u'Väärtpaberi müümine')
                    for kn in ('1132','115'):
                        kt = Konto.objects.get(pk=kn)
                        ks = Kanne.objects.all().filter(konto=kt, tehing__tehingutyyp=tt, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                        r_sum += float(nvl(ks, 0) * (1 if kt.osa in ('A', 'K') else -1))
                elif s[1] == 'K':
                    kt = Konto.objects.get(pk=s[2:])
                    ks = Kanne.objects.all().filter(konto=kt, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=False).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                    r_sum += float(nvl(ks, 0) * (-1 if kt.osa in ('A', 'K') else 1))
                elif s[1] == 'D':
                    kt = Konto.objects.get(pk=s[2:])
                    ks = Kanne.objects.all().filter(konto=kt, tehing__maksepaev__gte=akpv, tehing__maksepaev__lte=lkpv, on_deebet=True).exclude(tehing=TX).aggregate(Sum('summa'))['summa__sum']
                    r_sum += float(nvl(ks, 0) * (1 if kt.osa in ('A', 'K') else -1))
                elif s[1] == 'A':
                    kt = Konto.objects.get(pk=s[2:])
                    AD = Algsaldo.objects.filter(pearaamat=pr, konto=kt, on_deebet=True).aggregate(Sum('summa'))['summa__sum']
                    AK = Algsaldo.objects.filter(pearaamat=pr, konto=kt, on_deebet=False).aggregate(Sum('summa'))['summa__sum']
                    SK = float((nvl(AD,0) - nvl(AK,0))* (1 if kt.osa in ('A', 'K') else -1))
                    r_sum += SK
            elif s[0] == ':': # var
                r_sum += mem.get(s[1]) * (-1 if (len(s) == 3 and s[2] == '-') else 1)
        if r[2][0] == '#':
            mem.update({r[2][1]: round(float(r_sum),2)})
        if r_sum != 0:
            rva.append({'konto': r[0], 'Fmt': r[1], 'summa': round(float(r_sum),2)})

    return rva


# Functions for formulas
    
def usd2eur(amount, when):
    c = Currency()    
    return round(c.convert(when, 'USD', 'EUR', amount),2) 

def eur2usd(amount, when):
    c = Currency()    
    return round(c.convert(when, 'EUR', 'USD', amount),2)

def sek2eur(amount, when):
    c = Currency()    
    return round(c.convert(when, 'SEK', 'EUR', amount),2) 

def gbp2eur(amount, when):
    c = Currency()    
    return round(c.convert(when, 'GBP', 'EUR', amount),2) 

def nok2eur(amount, when):
    c = Currency()    
    return round(c.convert(when, 'NOK', 'EUR', amount),2)

def vp(ss):
    vh = VaraHaldur()
    vp_id = vh.identify(ss)
    return vp_id

def cls(vp_id):
    vp = Vara.objects.get(id=vp_id)
    vp_cls = vp.vp_tyyp
    return vp_cls

def cnt(text): # leiab vara koguse tekstist
    vp_cnt = 0
    if re.search('(\+|-).+@', text):
        ss = text.split()
        for s in ss:
            if re.search('(\+|-).+@', s):
                t = s
                break
        ss = t.split('@')
        vp_cnt = round(float(ss[0]),6)
    return vp_cnt

def amt(vp_id, kpv): # leiab vara maksumuse muutuse
    vh = VaraHaldur()
    vp_sum = vh.getTHDiff(vp_id, kpv)
    return float(vp_sum)

def getReservD(vp_id, deebet, kpv):
    vh = VaraHaldur()
    l_val = float(vh.getReservDiff(vp_id, kpv))
    if deebet == 'K' and l_val < 0 or deebet == 'D' and l_val > 0:
        l_val = 0
    if deebet == 'D' and l_val < 0:
        l_val = -1 * l_val
    return l_val

def getReserv(vp_id, kpv):
    vh = VaraHaldur()
    l_val = vh.getReservDiff(vp_id, kpv)
    return float(l_val)

class Calc(object):
    '''
    Klass valemite interpreteerimiseks. 
    '''
    formulas = []
    locvars = {}
    recvars = {}
    qryvars = {}
    realnames = {"pk": ("pangakonto","c"),
               "r": ("reatyyp","n"),
               "kpv": ("kuupaev","d"),
               "p": ("partner","c"),
               "ss": ("selgitus","c"),
               "s": ("summa","n"),
               "c": ("valuuta","c"),
               "d": ("deebet","c"),
               "a": ("arhiveerimistunnus","c"),
               "t": ("tunnus","c"),
               "v": ("viitenumber","c"),
               "dok": ("dokument","c"),
               "arv": ("arvestatud","c")}
    functions = ('usd2eur', 'eur2usd', 'sek2eur', 'nok2eur', 'gbp2eur', 'vp', 'cls', 'cnt', 'amt', 'getReservD', 'getReserv', 'abs', 'float')

    def __init__(self):
        self.formulas = []
        self.locvars = {}
        self.recvars = {}
        self.qryvars = {}

    def set_vars(self, rec):
        vrs = {"pk": (rec.pangakonto, ),
               "r": (rec.reatyyp, ),
               "kpv": (rec.kuupaev, ),
               "p": (rec.partner, ),
               "ss": (rec.selgitus, ),
               "s": (rec.summa, ),
               "c": (rec.valuuta, ),
               "d": (rec.deebet, ),
               "a": (rec.arhiveerimistunnus, ),
               "t": (rec.tunnus, ),
               "v": (rec.viitenumber, ),
               "dok": (rec.dokument, ),
               "arv": (rec.arvestatud, )}
        return vrs
    
    # Class methods
    
    def add_formula(self, formula):
        self.formulas.extend([(formula, )])
        
    def analyse(self, formula, calculate = False):
        f = {'F': formula, 'ERR': False, 'ERRMSG': '', 'POS': 1, 'SYM': '', 
             'NAME': '', 'VAL': '', 'LEN': 0, 'EXP': '', 'MV': '', 'CND': '', 'CV': ''}
        p = self.omistus(f, calculate)
        #print 'After analyse: ', p
        for frm in self.formulas:
            if frm[0] == formula:
                i = self.formulas.index(frm)
                self.formulas.remove(frm)
                frm = (formula, p['MV'], p['CV']) 
                self.formulas.insert(i, frm)
        return p
    
    def getsym(self, f):
        if f.has_key('LEN'):
            f['POS'] = f['POS'] + f['LEN']
        else:
            f['POS'] = 1
        f['LEN'] = 0
        f['ERR'] = False
        f['ERRMSG'] = ''
        formula = f['F']
        if len(formula) == 0:
            f['SYM'] = 'END'
            return f
        while formula[0] == ' ' and len(formula) > 0:
            formula = formula[1:]
            f['POS'] = f['POS'] + 1
        if formula[0] in ('{','}','(',')','+','-','*','/','=','<','>','&',','):
            f['SYM'] = formula[0]
            f['NAME'] = formula[0]
            f['VAL'] = ''
            f['LEN'] = 1
            f['F'] = formula[1:]
        elif formula[0].isdigit():
            i = 1
            while len(formula) > i and formula[i].isdigit():
                i += 1
            if len(formula) > i and formula[i] == '.':
                i += 1
                while len(formula) > i and formula[i].isdigit():
                    i += 1
            if len(formula) <= i:
                v = formula
            else:
                v = formula[:i]
            f['NAME'] = v
            f['VAL'] = float(v)
            f['LEN'] = i
            f['SYM'] = 'NUM'
            if len(formula) > i+1: 
                f['F'] = formula[i:]
            else:
                f['F'] = ''
        elif formula[0] == '\'':
            i = 1
            while len(formula) > i and formula[i] != '\'':
                i += 1
            f['SYM'] = 'STR'
            f['NAME'] = formula[1:i]
            f['VAL'] = ''
            f['LEN'] = i+1
            if len(formula) > i+2: 
                f['F'] = formula[i+1:]
            else:
                f['F'] = ''
        elif formula[0] in (':','@','#','_'):
            t = formula[0]
            i = 1
            while len(formula) > i and formula[i].isalnum():
                i += 1
            f['NAME'] = formula[1:i]
            f['VAL'] = ''
            f['LEN'] = i
            if len(formula) >= i+1: 
                f['F'] = formula[i:]
            else:
                f['F'] = ''
            if t == ':':
                f['SYM'] = 'LOC'
                if self.locvars.has_key(f['NAME']):
                    f['VAL'] = self.locvars[f['NAME']][0]
                else:
                    self.locvars.setdefault(f['NAME'],('?',))
                # add dependencies
                if f['MV'] != '':
                    if t+f['NAME'] not in self.locvars[f['MV']]:
                        self.locvars[f['MV']] = self.locvars[f['MV']] + (t+f['NAME'],)
                        #print 'Deps: ', self.locvars[f['MV']]
            elif t == '@':
                f['SYM'] = 'REC'
                if not self.realnames.has_key(f['NAME']):
                    f['ERR'] = True
                    f['ERRMSG'] = 'Unknown record variable name: '+t+f['NAME']
                else:
                    if self.recvars.has_key(f['NAME']):
                        if self.realnames[f['NAME']][1] == 'c':
                            f['VAL'] = '\'' + self.recvars[f['NAME']][0] + '\''
                        elif self.realnames[f['NAME']][1] == 'n':
                            f['VAL'] = self.recvars[f['NAME']][0]
                        elif self.realnames[f['NAME']][1] == 'd':
                            d = self.recvars[f['NAME']][0]
                            f['VAL'] = 'date('+smart_unicode(d.year)+','+smart_unicode(d.month)+','+smart_unicode(d.day)+')'
            elif t == '#':
                f['SYM'] = 'ALT'
                if not self.realnames.has_key(f['NAME']):
                    f['ERR'] = True
                    f['ERRMSG'] = 'Unknown alternate variable name: '+t+f['NAME']
                else:
                    if self.qryvars.has_key(f['NAME']):
                        if self.realnames[f['NAME']][1] == 'c':
                            f['VAL'] = '\'' + self.qryvars[f['NAME']][0] + '\''
                        elif self.realnames[f['NAME']][1] == 'n':
                            f['VAL'] = self.qryvars[f['NAME']][0]
                        elif self.realnames[f['NAME']][1] == 'd':
                            d = self.qryvars[f['NAME']][0]
                            f['VAL'] = 'date('+smart_unicode(d.year)+','+smart_unicode(d.month)+','+smart_unicode(d.day)+')'
                    else:
                        f['VAL'] = t + self.realnames[f['NAME']][0]
            elif t == '_':
                f['SYM'] = 'FN'
                if f['NAME'] not in self.functions:
                    f['ERR'] = True
                    f['ERRMSG'] = 'Unknown function name: '+t+f['NAME']
        return f

    def omistus(self, f, calculate):
        p = self.getsym(f)
        p['MV'] = ''
        if p['SYM'] == '{':
            p['SYM'] = ''
            p = self.tv_exp(p, calculate)
            p['CND'] = p['EXP']
            if p['ERR']:
                return p
            if p['SYM'] == '':
                p = self.getsym(p)
            if p['SYM'] != '}':
                p['ERR'] = True
                p['ERRMSG'] = 'Syntax error (omistus): } was expected in position '+smart_unicode(p['POS'])
                return p
            else:
                p = self.getsym(p)
        if calculate:
            try:
                print ' !# Trying to find: ', p['CND'] 
                if p['CND'] == '':
                    p['CV'] = True
                else:
                    p['CV'] = eval(p['CND'])
                    print '   -> ', p['CV']
            except:
                print ' !# Cant calculate ', p['CND'] 
                p['CV'] = ''
        # tv_exp is ok
        if p['SYM'] != 'LOC':
            p['ERR'] = True
            p['ERRMSG'] = 'Syntax error (omistus): local variable was expected in position '+smart_unicode(p['POS'])
            return p
        else:
            l_locvar = p['NAME'] 
            p['MV'] = l_locvar
            p = self.getsym(p)
        # locvar is ok
        if p['SYM'] != '=':
            p['ERR'] = True
            p['ERRMSG'] = 'Syntax error (omistus): = was expected in position '+smart_unicode(p['POS'])
        else:
            # assign is ok
            p['SYM'] = ''
            p = self.exp(p, calculate)
            if not p['ERR'] and calculate and p['CV'] == True:
                l_value = ''
                try:
                    l_value = eval(p['EXP'])
                except:
                    print ' Viga arvutamisel: ', p['EXP']
                    pass
                if l_value != '':
                    p['VAL'] = l_value
                    if self.locvars.has_key(l_locvar):
                        l_loc =  len(self.locvars[l_locvar])
                        if l_loc == 1:
                            self.locvars[l_locvar] = (l_value, )
                        elif l_loc > 1:
                            self.locvars[l_locvar] = (l_value, ) + self.locvars[l_locvar][1:]
            else:
                #print ' # ',p
                pass
            if p['SYM'] == '':
                p = self.getsym(p)
            if p['SYM'] != 'END':
                p['ERR'] = True
                p['ERRMSG'] = 'Syntax error (omistus): unexpected symbol ' +p['SYM']+ ' in position '+smart_unicode(p['POS'])
        return p
    
    def tv_exp(self, p, calculate):
        p = self.exp(p, calculate)
        if p['ERR']:
            return p
        l_e1 = p['EXP']
        if p['SYM'] == '':
            p = self.getsym(p)
        if p['SYM'] not in ('<','>','='):
            p['ERR'] = True
            p['ERRMSG'] = 'Syntax error (tv_exp): logic operator was expected in position '+smart_unicode(p['POS'])
            return p
        l_op = p['SYM']
        if l_op == '=':
            l_op = '=='
        p['SYM'] = ''
        p = self.exp(p, calculate)
        if p['ERR']:
            return p
        l_e2 = p['EXP']
        l_tv = l_e1+l_op+l_e2
        if p['SYM'] == '':
            p = self.getsym(p)
        if p['SYM'] == '&':
            p['SYM'] = ''
            p = self.tv_exp(p, calculate)
            if p['ERR']:
                return p
            l_tv = l_tv + ' and ' + p['EXP']
        p['EXP'] = l_tv
        print ' ?# ', p['EXP']
        if calculate:
            try:
                p['VAL'] = eval(p['EXP'])
                print ' ## ', p['VAL']
            except:
                pass
        return p
    
    def exp(self, p, calculate):
        p = self.add(p, calculate)
        if p['ERR']:
            return p
        l_exp = p['EXP']
        while p['SYM'] in ('+','-'):
            l_op = p['SYM']
            p['SYM'] = ''
            p = self.add(p, calculate)
            if p['ERR']:
                return p
            l_exp = l_exp + l_op + p['EXP']
            if p['SYM'] == '':
                p = self.getsym(p)
        p['EXP'] = l_exp
        if calculate:
            try:
                p['VAL'] = eval(p['EXP'])
                # print '  eval:', p['EXP'],'->',p['VAL']
            except:
                pass
        return p
    
    def add(self, p, calculate):
        p = self.term(p, calculate)
        if p['ERR']:
            return p
        l_exp = p['EXP']
        p = self.getsym(p)
        while p['SYM'] in ('*','/'):
            l_op = p['SYM']
            p['SYM'] = ''
            p = self.term(p, calculate)
            if p['ERR']:
                return p
            l_exp = l_exp + l_op + p['EXP']
            if p['SYM'] == '':
                p = self.getsym(p)
        p['EXP'] = l_exp
        if calculate:
            try:
                p['VAL'] = eval(p['EXP'])
            except:
                pass
        return p

    def params(self, p, calculate):
        p = self.exp(p, calculate)
        if p['ERR']:
            return p
        l_exp = p['EXP']
        while p['SYM'] == ',':
            l_op = p['SYM']
            p['SYM'] = ''
            p = self.exp(p, calculate)
            if p['ERR']:
                return p
            l_exp = l_exp + l_op + p['EXP']
            if p['SYM'] == '':
                p = self.getsym(p)

        p['EXP'] = l_exp
        return p

    def term(self, p, calculate):
        l_exp = ''
        if not p.has_key('SYM') or p['SYM'] == '':
            p = self.getsym(p)
        if p['SYM'] == '(':
            p = self.exp(p, calculate)
            if p['ERR']:
                return p
            if p['SYM'] != ')':
                p['ERR'] = True
                p['ERRMSG'] = 'Syntax error (term): ) was expected in position '+smart_unicode(p['POS'])
                return p
            l_exp = '(' + p['EXP'] + ')'
        elif p['SYM'] == 'FN':
            l_fn = p['NAME']
            p = self.getsym(p)
            if p['SYM'] != '(':
                p['ERR'] = True
                p['ERRMSG'] = 'Syntax error (term): ( was expected in position '+smart_unicode(p['POS'])
                return p
            p['SYM'] = ''
            p = self.params(p, calculate)
            if p['ERR']:
                return p
            if p['SYM'] == '':
                p = self.getsym(p)
            if p['SYM'] != ')':
                p['ERR'] = True
                p['ERRMSG'] = 'Syntax error (term-fn): ) was expected in position '+smart_unicode(p['POS'])+ ', found '+smart_unicode(p['SYM'])
                return p
            l_exp = l_fn + '(' + p['EXP'] + ')'
        elif p['SYM'] == 'LOC':
            l_exp = smart_unicode(p['VAL'])
        elif p['SYM'] == 'REC':
            l_exp = smart_unicode(p['VAL'])
        elif p['SYM'] == 'ALT':
            l_exp = smart_unicode(p['VAL'])
        elif p['SYM'] == 'NUM':
            l_exp = smart_unicode(p['VAL'])
        elif p['SYM'] == 'STR':
            l_exp = '\'' + p['NAME'] + '\''
        else:
            p['ERR'] = True
            p['ERRMSG'] = 'Unexpected symbol in term: '+ smart_unicode(p['SYM'])
        p['EXP'] = l_exp
        p['SYM'] = ''
        if calculate:
            try:
                p['VAL'] = eval(p['EXP'])
            except:
                pass
            
        return p
                
class Deals(object):
    '''
    Klass kandekirjete tegemiseks.
    '''
    qryrec = ''
    model = Calc()
    logger = None
    
    def __init__(self, logger = None):
        self.model = Calc()
        self.logger = logger
        if self.logger != None:
            print 'Got logger',  self.logger.filename, not self.logger.file.closed 

    def error(self, text):
        if self.logger != None:
            self.logger.error(text)
        return
        
    def warning(self, text):
        if self.logger != None:
            self.logger.warning(text)
        return
        
    def info(self, text):
        if self.logger != None:
            self.logger.info(text)
        return
        
    '''
      Valemi süntaks:
      
      prefixid: 
          ':' - lokaalne muutuja; --> { asendada väärtusega } arvutada = asendada väärtusega
          '@' - aktiivse kirje väli; --> asendada väärtusega
          '#' - tingimustele vastava kirje väli --> { asendada nimega } = asendada väärtusega
      omistus ::- [ '{' tv_exp '}' ] locvar '=' exp . 
      exp ::- add { ('+'|'-') add } .
      add ::- term { ('*'|'/') term } .
      term ::- var | '(' exp ')' | func | numval | charval .
      var ::- locvar | recvar | qryvar .
      locvar ::- ':' id .
      recvar ::- '@' id .
      qryvar ::- '#' id .
      func ::- '_' id '(' [ params ] ')' .
      params ::- exp { ',' exp } .
      numval ::- intval [ '.' intval ] .
      intval ::- '0'..'9' { '0'..'9' } .
      charval ::- '\'' string '\'' .
      tv_exp ::- exp ('<'|'>'|'=') exp {'&' tv_exp}.
    '''
    def find_alternate(self, condition):
        print ' !! Otsin kirjet, kus ', condition
        if condition.find('#') >= 0 and self.qryrec == '':
            c = condition.replace('#','row.').replace("=='","==u'")
            print '   !! --> ',[c]
            rows = Pangakirje.objects.all().filter(arvestatud='N').order_by('kuupaev', 'reatyyp', 'arhiveerimistunnus')
            for row in rows:
                print '   !!! ',row, [row.selgitus], type(row.selgitus)
                if eval(c):
                    self.model.qryvars = self.model.set_vars(row)
                    self.qryrec = row
                    return True
                else:
                    cc = c.split(' and ')
                    for q in cc:
                        print '     > ',[q],eval(q), type(q)
                    
        return False
    
    def parse(self, formula):
        #print 'Vaja arvutada ', formula
        self.model.add_formula(formula)
        p = self.model.analyse(formula)
        if p['ERR']:
            self.error(p['ERRMSG'])
            self.debug(p)
            return
        if p.has_key('CND') and p['CND'] != '' and len(self.model.qryvars) == 0:
            self.find_alternate(p['CND'])
        return

    def calculate(self):
        results = False
        counter = 10
        while not results and counter > 0:
            results = True
            for formula in self.model.formulas:
                p = self.model.analyse(formula[0], True)
                # print ' * ', formula
                if p['ERR']:
                    self.error(p['ERRMSG'])
                    self.debug()
                    return
                if len(formula) == 3 and formula[2] == True:
                    var = formula[1]
                    if var != '':
                        # print var, '=', self.model.locvars[var][0]
                        if self.model.locvars[var][0] == '?':
                            results = False
                    else:
                        results = False
                elif len(formula) == 3 and formula[2] == '':
                    results = False
                # print '  _',results
            counter -= 1
            # print results,'_',counter
            # self.debug()
        for formula in self.model.formulas:
            if formula[2] == '':
                self.error('Can not calculate '+formula[0])
                self.debug()
                results = False
        return results

    @transaction.commit_on_success
    def create(self, row, items, rule):
        created = 0
        self.model.recvars = self.model.set_vars(row)
        l_qry = False
        l_loc = False
        #self.debug()
        for item in items:
            l_qry = l_qry or item.valem.find('#') >= 0
            l_loc = l_loc or item.valem.find(':') >= 0
            self.parse(item.valem)
        #self.debug()
        if l_qry and len(self.model.qryvars) == 0:
            self.error('data missing for alternate record')
            self.debug()
            return created
        if l_qry and cmp(self.model.recvars, self.model.qryvars) == 0:
            self.info('same row, skipping')
            return created
        if l_loc and len(self.model.locvars) == 0:
            self.error('data missing for local variables')
            return created
        if not self.calculate():
            self.error('Can not calculate formulas')
            #self.debug()
            return 99
        # creating records for Tehing and Kanne
        #self.debug()
        try:
            PR = Pearaamat.objects.get(aasta=row.kuupaev.year)
        except:
            PR = Pearaamat()
            PR.aasta = row.kuupaev.year
            PR.save(True)
        T = Tehing()
        T.pearaamat = PR
        T.pangakirje = row
        T.tehingutyyp = rule
        T.sisu = rule.kirjeldus
        T.tehingupaev = row.kuupaev
        T.maksepaev = row.kuupaev
        T.on_manual = False
        T.save(True)
        kcnt = 0
        for item in items:
            for formula in self.model.formulas:
                if item.valem == formula[0] and formula[2] == True:
                    K = Kanne()
                    K.tehing = T
                    K.konto = item.konto
                    K.on_deebet = item.on_deebet
                    K.summa = round(self.model.locvars[formula[1]][0],2)
                    K.on_manual = False
                    K.save(True)
                    kcnt += 1
        if kcnt > 0:
            row.arvestatud = 'J'
            row.tehing = T
            row.save()
            created += 1
            if self.qryrec != '':
                self.qryrec.arvestatud = 'J'
                self.qryrec.tehing = T
                self.qryrec.save()
                created += 1
        else:
            T.delete()
        return created
    
    def debug(self, p = ''):
        self.info('Formulas are '+ smart_unicode(self.model.formulas))
        self.info('LOC variables are '+ smart_unicode(self.model.locvars))
        self.info('REC variables are '+ smart_unicode(self.model.recvars))
        self.info('ALT variables are '+ smart_unicode(self.model.qryvars))
        if p != '':
            self.info( p )
        return
