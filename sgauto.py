#coding=utf8
import os, sys, zipfile, time, json, datetime
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from os.path import basename

__DEBUG__=True

#import sgauto_ui
#class SGAuto(QtWidgets.QDialog, sgauto_ui.Ui_Dialog):

FORM_CLASS, WID_CLASS = uic.loadUiType(os.path.join(
            os.path.dirname(__file__),'sgauto.ui'))
class SGAuto(WID_CLASS, FORM_CLASS):
    def __init__(self, parent=None):
        super(SGAuto, self).__init__(parent)
        self.setupUi(self)
        self.uspath=os.path.expanduser('~')
        self.inipath=os.path.join(self.uspath,'sgauto.cfg')
        inimsg=self.loadSet(self.inipath)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.SET['Interval'])
        self.sbInter.setValue(self.SET['Interval']/1000)
        self.timer.timeout.connect(self.timer_timeout)
        self.already_processing=False
        self.force_proc=False
        self.logst('Application initialized. %s' % inimsg)
        self.logst('Any changes will NOT be saved until Start is pressed!')
    
    def loadSet(self,path):
        try:
            setfile=open(path,'r')
            self.SET=json.load(setfile)
            self.logst('Found config file at: %s. Loading last settings.' % path)
        except IOError:
            self.logst('Config file %s not found. Using default settings' % path)
            self.SET={'SvPaths':{},'BakPath':'','Interval':2000,'LastTS':0, 'AddFilesLast':''}
            return 'Select files to backup and storage folder. Press Start to begin monitoring.'
        except ValueError:
            self.logst('Config file %s is malformed. Using default settings' % path)
            self.SET={'SvPaths':{},'BakPath':'','Interval':2000,'LastTS':0, 'AddFilesLast':''}
            return 'Add new files to backup and choose storage folder. Press Start to begin monitoring.'
        else:
            print("loadSet:", self.SET)
            while (self.lwSGPaths.count()): self.lwSGPaths.takeItem(0)  #clear monitor file list
            self.populate_lwSGPaths(self.SET['SvPaths'].keys(), init=True)
            self.populate_tabFList(self.SET['BakPath'])
            return 'Press Start to begin monitoring current files.'

    def saveSet(self,path):
            try:
                setfile=open(path,'w')
            except IOError:
                self.logst('Can\'t write settings file at %s' % path)
                self.logst('Program may still work fine, but current settings will not be saved.')
            else:
                json.dump(self.SET, setfile)
                setfile.close()
                self.logst('Current settings saved at: %s' % path)

    def yesno(self):
        return QMessageBox.Yes == QMessageBox.question(self, "Confirm","Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
       
    def logst(self,string=''):
        dt=str(time.strftime('%y/%m/%d %H:%M'))
        self.lwStatus.addItem('%s- %s' % (dt,string))
        self.lwStatus.scrollToBottom()
        
    def process_files(self,sgfList,bakPath):
        #print("process_files got:", sgfList, bakPath)
        if self.already_processing==True:
            self.logst('Already processing files. Skipping this cycle. Consider setting longer interval.')
        else:
            tstamp=time.time()
            #curdate=time.strftime('%c')
            curdate=datetime.datetime.fromtimestamp(int(tstamp))
            self.already_processing=True
            print(tstamp, curdate)
            zipfname='sg'+str(tstamp)+'.sgauto.zip'
            with zipfile.ZipFile(bakPath+'/'+zipfname,'w') as myzip:
                for file in sgfList.keys():
                    print('Adding '+file)
                    try:
                        myzip.write(file)
                    except IOError:
                        self.logst('Can\'t open {}. Skipping.'.format(file))
            self.already_processing=False
            return zipfname, tstamp, curdate

    def timer_timeout(self):
        for plik in self.SET['SvPaths'].keys():
            try:
                pmtime=os.path.getmtime(plik)
            except Exception as e:
                self.logst('Got exception from mtime {}.'.format(str(e)))
                self.logst('System error on {} modify time! Skipping this turn.'.format(basename(plik)))
                return False
            if pmtime > self.SET['LastTS'] or self.force_proc:
                if self.force_proc:
                    self.logst('Forcing processing with new files added...')
                else:  
                    self.logst('File %s changed. Processing...' % basename(plik))
                pf = self.process_files(self.SET['SvPaths'],self.SET['BakPath'])
                #print("process files returned ", pf)
                fname, tstamp, curdate = pf
                self.SET['LastTS']=tstamp
                self.leTStamp.setText(str(tstamp))
                self.leDate.setText(str(curdate))
                self.add_tabFList(tstamp,curdate,fname)
                self.force_proc=False
    
    def enableWidgets(self,enable):
        for w in [ self.bAddFiles, self.bRemove, self.bClear, self.bBakPath, self.sbInter, self.bLoadSet, self.bSaveSet ]:
            w.setEnabled(enable)
            
    @QtCore.pyqtSlot()
    def on_bRemove_clicked(self):
        lob=self.lwSGPaths
        try:
            entry, row = lob.currentItem().text() , lob.currentRow()
        except AttributeError:
            self.logst('Select valid list entry first!!!')
        else:
            self.logst('Removing %s from list.' % entry)
            lob.takeItem(row)
            self.SET['SvPaths'].pop(entry)
            print(self.SET['SvPaths'])
        
    def populate_lwSGPaths(self,paths, init=False):
        print('populate_lwSGPaths got:', paths)
        count=0
        plist=list(paths)
        for path in plist:
            if path not in self.SET['SvPaths'].keys() or init:
                try:
                    mtime=os.path.getmtime(path)
                except FileNotFoundError:
                    self.logst('%s not found. Removing from list.' % path)
                    self.SET['SvPaths'].pop(path)
                else:
                    self.SET['SvPaths'][path]=mtime
                    self.lwSGPaths.addItem(path)
                    count=count+1

        if count:
            self.logst('Added %i new file(s).' % count)
            self.force_proc=True
        print('SvPaths after populate',self.SET['SvPaths'])    
            
    @QtCore.pyqtSlot()
    def on_bAddFiles_clicked(self):
        try:
            paths=QtWidgets.QFileDialog.getOpenFileNames(self, 'Select files to backup', self.SET['AddFilesLast'])[0]
        except KeyError:
            paths=QtWidgets.QFileDialog.getOpenFileNames(self,'Select files to backup')[0]
        if len(paths)>0:
            self.SET['AddFilesLast']=os.path.dirname(paths[0])
            self.populate_lwSGPaths(paths)
    
    def add_tabFList(self, ts, dt, file):
        tab, wI = self.tabFList, QtWidgets.QTableWidgetItem
        tab.insertRow(tab.rowCount())
        tab.setItem(tab.rowCount()-1,0,wI('%.0f' % ts)) #Timestamp
        tab.setItem(tab.rowCount()-1,1,wI(str(dt))) #Date
        tab.setItem(tab.rowCount()-1,2,wI(file)) #Filename
        tab.resizeColumnsToContents()
        tab.scrollToBottom()

    def populate_tabFList(self, bp):
        while (self.tabFList.rowCount()): self.tabFList.removeRow(0)
        self.leBakPath.setText(bp)
        for _,_,bakfiles in os.walk(bp):
            for file in bakfiles:
               if file.rfind('.sgauto.zip')>0:
                 ts=os.path.getmtime(bp+'/'+file)
                 #dt=time.ctime(ts)
                 dt=datetime.datetime.fromtimestamp(int(ts))
                 self.add_tabFList(ts,dt,file)
                 self.leTStamp.setText(str(ts))
    
    @QtCore.pyqtSlot()
    def on_bBakPath_clicked(self):
        prevbp=self.SET['BakPath']
        try:
            bp=QtWidgets.QFileDialog.getExistingDirectory(self,'Select backup folder for your files.',str(self.SET['BakPath']))
        except:
            bp=QtWidgets.QFileDialog.getExistingDirectory(self)
        if len(bp)>0:
            self.SET['BakPath']=bp
            self.populate_tabFList(self.SET['BakPath'])
            if bp!=prevbp:
                self.force_proc=True
    
    @QtCore.pyqtSlot()
    def on_bStart_clicked(self):
        if self.bStart.isChecked():
            self.bStartStyle=self.bStart.styleSheet()
            self.bStart.setStyleSheet('background-color: red')
            self.saveSet(self.inipath)
            self.timer.start()
            self.logst('Monitoring selected files every %d seconds.' % int(self.SET['Interval']/1000))
            self.bStart.setText('Stop')
            self.enableWidgets(False)
        else:
            self.bStart.setStyleSheet(self.bStartStyle)
            self.timer.stop()
            self.bStart.setText('Start')
            self.enableWidgets(True)
            
    @QtCore.pyqtSlot()
    def on_bClear_clicked(self):
        if self.yesno():
            while (self.lwSGPaths.count()): self.lwSGPaths.takeItem(0)

    @QtCore.pyqtSlot()
    def on_bLoadSet_clicked(self):
        filter='SGAuto Config File (*.sgauto.cfg)'
        try:
            path=QtWidgets.QFileDialog.getOpenFileName(self, 'Select settings file', self.SET['BakPath'],filter)[0]
        except KeyError:
            path=QtWidgets.QFileDialog.getOpenFileName(self,'Select settings file','',filter)[0]
        if len(path)>0:
            self.loadSet(path)

    @QtCore.pyqtSlot()
    def on_bSaveSet_clicked(self):
        filter='SGAuto Config File (*.sgauto.cfg)'
        try:
            path=QtWidgets.QFileDialog.getSaveFileName(self, 'Select settings file', self.SET['BakPath'],filter)[0]
        except KeyError:
            path=QtWidgets.QFileDialog.getSaveFileName(self,'Select settings file','',filter)[0]
        if len(path)>0:
            self.saveSet(path)
    
    @QtCore.pyqtSlot(int)
    def on_sbInter_valueChanged(self, interval):
        #print('Interval changed:', interval)
        self.SET['Interval'] = interval*1000
        self.timer.setInterval(self.SET['Interval'])
            
    def closeEvent(self, ev):
        if QMessageBox.Yes == QMessageBox.question(self, 'Are you sure?', 
                     'Are you sure?', QMessageBox.Yes, QMessageBox.No):
            super(SGAuto, self).closeEvent(ev)
        else:
            ev.ignore()
    def keyPressEvent(self, k):
        print('Key pressed {}'.format(k.key()))
        

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    myapp = SGAuto()
    myapp.show()
    sys.exit(app.exec_())
