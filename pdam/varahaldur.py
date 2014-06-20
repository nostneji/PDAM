# coding: utf-8

'''
Created on 26.06.2012

@author: Indrek
'''
from models import Vara, VaraMall, Varatehing, Pearaamat, date2str, Tehing, Kanne, Konto, Pangakirje 
import re
from currencies import Currency
from decimal import *
from datetime import date
from django.utils.encoding import smart_unicode


class VaraHaldur(object):
    '''
    Klass varatehingute tegemise jaoks.
    '''
    def __init__(self):
        '''
        Constructor
        '''
        pass
    
    def getLyhend(self, text):
        lyh = ''
        if re.search('(\+|-).+@', text):
            ss = text.split()
            if ss[0] in ('T:','K:'):
                lyh = ss[1]
            else:
                lyh = ss[0]
        elif re.search('^[^:]*Fundorder.+\+', text):
            ss = text.split()
            lyh = ss[len(ss)-1]
        return lyh
        
    def identify(self, text):
        lyh = self.getLyhend(text)
        vs = Vara.objects.all()
        for v in vs:
            if v.lyhend != '' and v.lyhend != '?' and v.lyhend == lyh:
                print text,'1->',lyh,'->',v.lyhend
                return v.id
        for v in vs:
            if v.lyhend != '' and v.lyhend != '?' and re.search(v.lyhend, text):
                print text,'2->',v.lyhend
                return v.id
        vms = VaraMall.objects.all()
        for vm in vms:
            if re.search(vm.mall, text):
                return vm.vara.id
        # tekitame uue vara
        '''
        if re.search('(\+|-).+@', text):
            ss = text.split()
            if ss[0] in ('T:','K:'):
                v = Vara.objects.create(nimetus=ss[1], tyyp='A', lyhend=ss[1])
            else:
                v = Vara.objects.create(nimetus=ss[0], tyyp='A', lyhend=ss[0])
            return v.id
        '''
        return None
    
    def cnt(self, text): # leiab vara koguse pangakirje tekstist
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
    
    def analyse(self):
        print u'+++ Lühendite analüüs +++'
        # otsime lühenditeta varadele lühendeid
        vs = Vara.objects.all().filter(lyhend='?')
        for v in vs:
            print '? ' + v.nimetus
            ts = Varatehing.objects.all().filter(vara=v).order_by('vaartuspaev')
            for t in ts:
                ps = Pangakirje.objects.all().filter(kuupaev=t.vaartuspaev)
                for p in ps:
                    vk = self.cnt(p.selgitus)
                    print ' > ' + p.selgitus + ' > ', float(vk), float(t.kogus), p.summa, p.valuuta, t.summa, t.valuuta 
                    if float(vk) == float(t.kogus) and p.valuuta == t.valuuta and float(p.summa) == float(t.summa):
                        l = self.getLyhend(p.selgitus)
                        print ' ! ' + l
                        if l != '' and v.lyhend == '?':
                            v.lyhend = l
                            v.save()
                            print 'Loodud seos: ' + v.nimetus + '<-->' + v.lyhend
        return
    
    def buy(self, vara_id, tkpv, vkpv, kogus, summa, valuuta): # ost
        v = Vara.objects.get(id=vara_id)
        ts = Varatehing.objects.all().filter(vara=v, tyyp='O', vaartuspaev=vkpv, valuuta=valuuta)
        chk = 0
        for t in ts:
            if kogus == float(t.kogus) and summa==float(t.summa):
                chk += 1
        if chk == 0:
            vts = Varatehing.objects.all().filter(vara=v, vaartuspaev__lte=vkpv).order_by('vaartuspaev','-tyyp','-kogus')
            l_vt = ''
            for vt in vts:
                l_vt = vt
            e_sum = summa
            if valuuta != 'EUR':
                c = Currency()
                e_sum = c.convert(vkpv, valuuta, 'EUR', summa)
            yk = Decimal(kogus)
            sh = Decimal(e_sum)
            th = Decimal(e_sum)
            rs = Decimal(0)
            if l_vt != '':
                yk = yk + l_vt.yldkogus
                sh = sh + l_vt.soetushind
                if e_sum != 0:
                    th = Decimal(e_sum) * yk / Decimal(kogus)
                else:
                    th = sh
                rs = th - sh
            Varatehing.objects.create(vara=v, tyyp='O', tehingupaev=tkpv, vaartuspaev=vkpv, 
                                      kogus=kogus, summa=summa, valuuta=valuuta,
                                      eur_summa=e_sum, yldkogus=yk, soetushind=sh, 
                                      turuhind=th, reserv=rs)
        return 0

    def sell(self, vara_id, tkpv, vkpv, kogus, summa, valuuta): # müük
        dr = 0
        v = Vara.objects.get(id=vara_id)
        ts = Varatehing.objects.all().filter(vara=v, tyyp='M', vaartuspaev=vkpv, valuuta=valuuta)
        chk = 0
        for t in ts:
            if abs(kogus) == float(t.kogus) and summa==float(t.summa):
                chk += 1
        if chk == 0:
            vts = Varatehing.objects.all().filter(vara=v, vaartuspaev__lte=vkpv).order_by('vaartuspaev','-tyyp','-kogus')
            l_vt = ''
            for vt in vts:
                l_vt = vt
            e_sum = summa
            if valuuta != 'EUR':
                c = Currency()
                e_sum = c.convert(vkpv, valuuta, 'EUR', summa)
            yk = 0
            sh = 0 
            th = 0
            rs = 0
            if l_vt != '':
                if float(l_vt.yldkogus) - abs(kogus) < 0 and abs(float(l_vt.yldkogus) - abs(kogus)) > 0.000001:
                    print '>>> Error: Trying to sell more than we have!', abs(float(l_vt.yldkogus) - abs(kogus)), v
                    return 0
                yk = l_vt.yldkogus - Decimal(abs(kogus))
                if float(yk) < 0:
                    yk = Decimal(0)
                sh = l_vt.soetushind * Decimal(yk) / l_vt.yldkogus
                th = Decimal(e_sum) * yk / Decimal(abs(kogus))
                rs = th - sh
                dr = rs - l_vt.reserv
            else:
                print '>>> Error: Trying to sell, but we have not any!', v
                return 0
            Varatehing.objects.create(vara=v, tyyp='M', tehingupaev=tkpv, vaartuspaev=vkpv, 
                                      kogus=abs(kogus), summa=summa, valuuta=valuuta,
                                      eur_summa=e_sum, yldkogus=yk, soetushind=sh, 
                                      turuhind=th, reserv=rs)
        return dr

    def reprize(self, vara_id, vkpv, kogus, summa, valuuta): # ümbrhindlus
        dr = 0
        v = Vara.objects.get(id=vara_id)
        ts = Varatehing.objects.all().filter(vara=v, tyyp='H', vaartuspaev=vkpv, valuuta=valuuta)
        chk = 0
        for t in ts:
            if kogus == float(t.kogus) and summa==float(t.summa):
                chk += 1
        if chk == 0:
            vts = Varatehing.objects.all().filter(vara=v, vaartuspaev__lte=vkpv).order_by('vaartuspaev','-tyyp','-kogus')
            l_vt = ''
            for vt in vts:
                l_vt = vt
            e_sum = summa
            if valuuta != 'EUR':
                c = Currency()
                e_sum = c.convert(vkpv, valuuta, 'EUR', summa)
            if l_vt != '':
                if kogus != float(l_vt.yldkogus):
                    print '>>> Error: Not the same amount!', v
                    return 0
                yk = l_vt.yldkogus
                sh = l_vt.soetushind
                th = Decimal(e_sum)
                rs = th - sh 
                dr = rs - l_vt.reserv
            else:
                print '>>> Error: Nothing to reprize!', v
                return 0
            Varatehing.objects.create(vara=v, tyyp='H', tehingupaev=vkpv, vaartuspaev=vkpv, 
                                      kogus=kogus, summa=summa, valuuta=valuuta,
                                      eur_summa=e_sum, yldkogus=yk, soetushind=sh, 
                                      turuhind=th, reserv=rs)
        return dr
        
    def getReservDiff(self, vara_id, kpv):
        rs = 0
        v = Vara.objects.get(id=vara_id)
        vts = Varatehing.objects.all().filter(vara=v, vaartuspaev__lte=kpv).order_by('vaartuspaev','-tyyp','-kogus')
        l_vte = '' 
        l_vt = ''
        for vt in vts:
            l_vte = l_vt
            l_vt = vt
        if l_vt != '':
            rs = l_vt.reserv
            if l_vte != '':
                rs = rs - l_vte.reserv
        return rs
    
    def getTHDiff(self, vara_id, kpv):
        rs = 0
        v = Vara.objects.get(id=vara_id)
        vts = Varatehing.objects.all().filter(vara=v, vaartuspaev__lte=kpv).order_by('vaartuspaev','-tyyp','-kogus')
        l_vte = '' 
        l_vt = ''
        for vt in vts:
            l_vte = l_vt
            l_vt = vt
        if l_vt != '' and l_vte != '':
            rs = l_vt.turuhind - l_vte.turuhind
        return rs
        
    def recalc(self, vara_id):
        v = Vara.objects.get(id=vara_id)
        vts = Varatehing.objects.all().filter(vara=v).order_by('vaartuspaev','-tyyp','-kogus')
        l_vt = ''
        for vt in vts:
            yk = Decimal(vt.kogus)
            sh = Decimal(vt.eur_summa)
            th = Decimal(vt.eur_summa)
            rs = Decimal(0)
            if l_vt != '':
                if vt.tyyp == 'O':
                    yk = yk + l_vt.yldkogus
                    sh = sh + l_vt.soetushind
                    if float(vt.eur_summa) != 0:
                        th = Decimal(vt.eur_summa) * yk / Decimal(vt.kogus)
                    else:
                        th = sh
                elif vt.tyyp == 'M':
                    yk = l_vt.yldkogus - yk
                    sh = l_vt.soetushind * Decimal(yk) / l_vt.yldkogus
                    th = Decimal(vt.eur_summa) * yk / Decimal(vt.kogus)
                elif vt.tyyp == 'H':
                    if float(yk) != float(l_vt.yldkogus):
                        print 'WARNING: Asset amount for reprize is different from actual!', v.nimetus, yk, l_vt.yldkogus
                        yk = l_vt.yldkogus
                    sh = l_vt.soetushind
                    th = Decimal(vt.eur_summa)
                rs = th - sh
            vt.yldkogus = yk
            vt.soetushind = sh
            vt.turuhind = th
            vt.reserv = rs
            # linking with Tehing
            tt = Tehing.objects.all().filter(tehingupaev=vt.vaartuspaev)
            for t in tt:
                tks = Kanne.objects.all().filter(tehing=t, konto__kontonumber='264')
                if len(tks) > 0:
                    tx = []
                    pks = Pangakirje.objects.all().filter(tehing=t)
                    for pk in pks:
                        tv_id = self.identify(pk.selgitus)
                        tv_k = self.cnt(pk.selgitus)
                        if tv_id == v.id:
                            tx.append((t.id, abs(tv_k), abs(vt.kogus)))
                            print '...', vt.vaartuspaev, pk.selgitus, tv_id, v.id, abs(tv_k), abs(vt.kogus)
                    if len(tx) == 1:
                        vt.tehing_id = tx[0][0]
                        print '......', vt.tehing_id
                    elif len(tx) > 1:
                        for ks in tx:
                            if ks[1] == ks[2]:
                                vt.tehing_id = ks[0]
                                print '.....:', vt.tehing_id
            vt.save()
            l_vt = vt
        return
    
    def getEndCount(self, vara_id):
        res = 0.0
        v = Vara.objects.get(id=vara_id)
        if v:
            vts = Varatehing.objects.all().filter(vara=v).order_by('-vaartuspaev','tyyp','kogus')
            if len(vts) > 0:
                res = float(vts[0].yldkogus)
        return res

    def getLastDealYear(self, vara_id):
        res = 0
        v = Vara.objects.get(id=vara_id)
        if v:
            vts = Varatehing.objects.all().filter(vara=v).order_by('-vaartuspaev')
            if len(vts) > 0:
                res = vts[0].vaartuspaev.year
        return res

    def statusReport(self, kpv):
        vs = Vara.objects.all()
        SH = {'A':0, 'V':0, 'I':0}
        TH = {'A':0, 'V':0, 'I':0}
        RS = {'A':0, 'V':0, 'I':0}
        for v in vs:
            vts = Varatehing.objects.all().filter(vara=v, vaartuspaev__lte=kpv).order_by('vaartuspaev','-tyyp','-kogus')
            l_vt = ''
            for vt in vts:
                l_vt = vt
            if l_vt != '':
                if float(l_vt.yldkogus) > 0:
                    v = l_vt.vara
                    SH.update({v.vp_tyyp: SH.get(v.vp_tyyp) + float(l_vt.soetushind)})
                    TH.update({v.vp_tyyp: TH.get(v.vp_tyyp) + float(l_vt.turuhind)})
                    RS.update({v.vp_tyyp: RS.get(v.vp_tyyp) + float(l_vt.reserv)})
        return ({'Kpv': date2str(kpv)}, 
                [{'tyyp':'Aktsiad', 'sh':SH.get('A'), 'th':TH.get('A'), 'rs':RS.get('A')},
                       {'tyyp':u'Võlakirjad', 'sh':SH.get('V'), 'th':TH.get('V'), 'rs':RS.get('V')},
                       {'tyyp':'Alt.investeeringud', 'sh':SH.get('I'), 'th':TH.get('I'), 'rs':RS.get('I')},
                       {'tyyp':'KOKKU', 'sh':SH.get('A')+SH.get('V')+SH.get('I'), 
                        'th':TH.get('A')+TH.get('V')+TH.get('I'), 'rs':RS.get('A')+RS.get('V')+RS.get('I')}]
                )
    
    def getActivePR(self):
        prs = Pearaamat.objects.all().order_by('aasta')
        pr = prs.reverse()[:1][0]
        return pr
    
    def reservMovementReport(self, pr):
        t_Res = 0
        v_Res = 0
        ts = Tehing.objects.all().filter(pearaamat=pr).order_by('maksepaev')
        kres = Konto.objects.get(pk='264')
        data = []
        for t in ts:
            # vara otsing
            vts = Varatehing.objects.all().filter(vaartuspaev=t.maksepaev)
            l_v = None
            l_v_res = 0
            l_info = ''
            for vt in vts:
                brs = Pangakirje.objects.all().filter(tehing=t)
                for br in brs:
                    if self.identify(br.selgitus) == vt.vara.id:
                        if l_v != None:
                            # print 'Mitu sobivat kirjet? '+ l_info + '|' + t.tehingutyyp.kirjeldus+':'+br.selgitus
                            pass
                        l_v = vt.vara.id
                        l_v_res = self.getReservDiff(l_v, t.maksepaev)
                        l_info = t.sisu+':'+br.selgitus+ ' (' + vt.vara.vp_tyyp + ')'
                if l_v == None and vt.tyyp == 'H' and re.search('.*mberhindamine', t.sisu):
                    ss = t.sisu.split('(')
                    if len(ss) > 1:
                        s = ss[1].rstrip(')')
                        vs = Vara.objects.all().filter(nimetus=s)
                        for v in vs:
                            l_v = v.id
                            l_v_res = self.getReservDiff(l_v, t.maksepaev)
                            l_info = t.sisu + ' (' + v.vp_tyyp + ')'
                            break
                        if l_v == None:
                            print ' ? Ei leia ', s
                            pass
            # konto 264 otsing
            ks = Kanne.objects.all().filter(tehing=t, konto=kres)
            l_k = None
            l_t_res = 0
            for k in ks:
                l_t_res = l_t_res + (-1 if k.on_deebet else 1) * k.summa
                l_k = k
            abi = ''
            if l_k != None:
                ks = Kanne.objects.all().filter(tehing=t).exclude(konto=kres)
                for k in ks:
                    abi = abi + (',' if abi != '' else '') + k.konto.kontonumber 
            if l_v != None and l_k != None:
                t_Res += l_t_res
                v_Res += l_v_res    
                data.append({'kpv':date2str(t.maksepaev), 'tehing':l_info + ' - ' +abi, 'dk':l_t_res, 'dv':l_v_res, 'k':t_Res, 'v':v_Res, 't':t.id})
            elif l_v == None and l_k != None:
                print ' >>!v> ',t,l_k,l_t_res
            elif l_v != None and l_v_res != 0 and l_k == None:
                print ' >>!k> ',t,l_info,l_v_res
        return data
    
    def assetReport(self, pr):
        kpv = date(pr.aasta, 12, 31)
        vs = Vara.objects.all().order_by('nimetus')
        data = []
        SH = {'A':0, 'V':0, 'I':0}
        TH = {'A':0, 'V':0, 'I':0}
        RS = {'A':0, 'V':0, 'I':0}
        for v in vs:
            vts = Varatehing.objects.all().filter(vara=v, vaartuspaev__lte=kpv).order_by('vaartuspaev','-tyyp','-kogus')
            l_vt = ''
            for vt in vts:
                l_vt = vt
            if l_vt != '' and (float(l_vt.yldkogus) > 0 or float(l_vt.reserv != 0)):
                data.append({'nimetus':v.nimetus+'('+l_vt.tyyp+')', 'tyyp':v.vp_tyyp, 'kogus':l_vt.yldkogus, 
                             'sh':l_vt.soetushind, 'th':l_vt.turuhind, 'rs':l_vt.reserv})
                SH.update({v.vp_tyyp: SH.get(v.vp_tyyp) + float(l_vt.soetushind)})
                TH.update({v.vp_tyyp: TH.get(v.vp_tyyp) + float(l_vt.turuhind)})
                RS.update({v.vp_tyyp: RS.get(v.vp_tyyp) + float(l_vt.reserv)})
        return (data, [{'tyyp':'Aktsiad', 'sh':SH.get('A'), 'th':TH.get('A'), 'rs':RS.get('A')},
                       {'tyyp':u'Võlakirjad', 'sh':SH.get('V'), 'th':TH.get('V'), 'rs':RS.get('V')},
                       {'tyyp':'Alt.investeeringud', 'sh':SH.get('I'), 'th':TH.get('I'), 'rs':RS.get('I')},
                       {'tyyp':'KOKKU', 'sh':SH.get('A')+SH.get('V')+SH.get('I'), 
                        'th':TH.get('A')+TH.get('V')+TH.get('I'), 'rs':RS.get('A')+RS.get('V')+RS.get('I')},
                       ])
        
    