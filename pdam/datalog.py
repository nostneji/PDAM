# coding: utf-8
'''
Created on 02.07.2012

@author: Indrek
'''
from datetime import datetime, time

class Datalog(object):
    '''
    Loger
    '''
    filename = ''
    file = None
    log = []

    def __init__(self, fname):
        '''
        Constructor
        '''
        print 'Datalog failinimi = ', fname
        self.filename = fname
        if self.filename != '':
            self.file = open(self.filename, 'a')
    
    def add(self, typ, text):
        t = datetime.now()
        s = str(t.hour)+':'+str(t.minute)+':'+str(t.second)+'.'+str(t.microsecond)
        self.log.append((s, typ, text))
        if self.file != None:
            self.file.write(s+';'+typ+';'+text+'\n')
            self.file.flush()
        return
        
    def info(self, text):
        try:
            self.add('I', text)
        except:
            pass
        return

    def error(self, text):
        try:
            self.add('E', text)
        except:
            pass
        return
    
    def warning(self, text):
        try:
            self.add('W', text)
        except:
            pass
        return        
    
    def html(self):
        result = '<table id=\"log\">'
        for l in self.log:
            result = result + '<tr><td>' + l[0] + '</td><td>' + l[1] + '</td><td>' + l[2] + '</td></tr>'
        result = result + '</table>'
        return result
    
    def end(self):
        if self.file != None:
            self.file.close()
        self.log = []
        return
    
