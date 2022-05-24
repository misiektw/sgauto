#!/bin/python3
'''
    SGAuto (https://github.com/misiektw)
    copyright (c) 2016 Misiek Twardowski

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

#coding=utf8
import os, sys, zipfile, time, json, datetime
fromts = datetime.datetime.fromtimestamp
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox # pylint: disable=no-name-in-module
from PyQt5.QtCore import pyqtSlot
from os.path import basename


__DEBUG__ = False
__VERSION__ = '1.0a'

FORM_CLASS, WND_CLASS = uic.loadUiType(os.path.join(
            os.path.dirname(__file__),'sgauto.ui'))

class SGAuto(WND_CLASS, FORM_CLASS):
    def __init__(self, parent=None):
        super(SGAuto, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('SGAuto {} {} (C) misiektw(at)gmail.com'.format(__VERSION__,' '*50))
        self.uspath=os.path.expanduser('~')
        self.inipath=os.path.join(self.uspath,'sgauto.cfg')
        inimsg=self.loadSet(self.inipath)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.SET['Interval'])
        self.sbInter.setValue(int(self.SET['Interval']/1000))
        self.timer.timeout.connect(self.timer_timeout)
        self.already_processing=False
        self.force_proc=False
        self.logst('Application initialized. %s' % inimsg)
        self.logst('You can Add Files to monitor, and select Backup folder.')
        self.logst('Any changes will NOT be saved until Start button is pressed!')
    

    def updateLabels(self):
        self.lbTrash.setText('Trash: {} MB'.format(round(self.trashsize/1024/1024)))
        self.lbSize.setText('Size: {} MB'.format(round(self.bksize/1024/1024)))
        self.leTStamp.setText(str(self.SET['LastTS']))
        self.leDate.setText(str(fromts(self.SET['LastTS'])))

    def loadSet(self, path):
        self.bksize = 0
        self.trashsize = 0
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
            self.populate_lwSGPaths(self.SET['SvPaths'].keys(), init=True)
            self.populate_tabFList(self.SET['BakPath'])
            os.chdir(self.SET['BakPath'])
            self.trashsize = sum(os.path.getsize('.trash/'+f) for f in os.listdir('.trash'))
            self.updateLabels()
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

    def yesno(self, message='Are you sure?'):
        return QMessageBox.Yes == QMessageBox.question(self, "Confirm", message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
       
    def logst(self,string=''):
        dt=str(time.strftime('%y/%m/%d %H:%M'))
        self.lwStatus.addItem('%s- %s' % (dt,string))
        self.lwStatus.scrollToBottom()
        
    def process_files(self,sgfList,bakPath):
        if self.already_processing==True:
            self.logst('Already processing files. Skipping this cycle. Consider setting longer interval.')
        else:
            tstamp=round(time.time())
            self.already_processing=True
            print(tstamp)
            zipfname='sg'+str(tstamp)+'.sgauto.zip'
            with zipfile.ZipFile(bakPath+'/'+zipfname,'w', compression=zipfile.ZIP_DEFLATED) as myzip:
                for file in sgfList.keys():
                    print('Adding '+file)
                    try:
                        myzip.write(file)
                    except IOError:
                        self.logst('Can\'t open {}. Skipping.'.format(file))
            self.already_processing=False
            return zipfname, tstamp

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
                fname, tstamp = self.process_files(self.SET['SvPaths'],self.SET['BakPath'])
                self.SET['LastTS']=tstamp
                self.add_tabFList(tstamp, fname)
                self.bksize = self.bksize + os.path.getsize(fname)
                self.updateLabels()
                self.force_proc=False
    
    def enableWidgets(self,enable):
        for w in [ self.bAddFiles, self.bRemove, self.bClear, self.bBakPath, self.sbInter, self.bLoadSet, self.bSaveSet ]:
            w.setEnabled(enable)
    
    def on_tabFList_cellChanged(self, row, col):
        if self.tabFList.item(row,3):
            name = self.tabFList.item(row,2).text()
            comment = self.tabFList.item(row,3).text()
            path = self.SET['BakPath']
            if len(comment)>0:
                with open(os.path.join(path,name[:-4]+'.comm.txt'), 'w') as comfile:
                    comfile.write(comment)

    @pyqtSlot()
    def on_bRemove_clicked(self):
        try:
            entry, row = self.lwSGPaths.currentItem().text() , self.lwSGPaths.currentRow()
        except AttributeError:
            self.logst('Select valid list entry first!!!')
        else:
            self.logst('Removing %s from list.' % entry)
            self.lwSGPaths.takeItem(row)
            self.SET['SvPaths'].pop(entry)
            print(self.SET['SvPaths'])
        
    def populate_lwSGPaths(self, paths, init=False):
        if init:
            while (self.lwSGPaths.count()): self.lwSGPaths.takeItem(0)  #clear monitor file list
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
            
    @pyqtSlot()
    def on_bAddFiles_clicked(self):
        try:
            paths=QtWidgets.QFileDialog.getOpenFileNames(self, 'Select files to backup', self.SET['AddFilesLast'])[0]
        except KeyError:
            paths=QtWidgets.QFileDialog.getOpenFileNames(self,'Select files to backup')[0]
        if len(paths)>0:
            self.SET['AddFilesLast']=os.path.dirname(paths[0])
            self.populate_lwSGPaths(paths)
    
    def add_tabFList(self, ts, fname, comment=''):
        tab, wI = self.tabFList, QtWidgets.QTableWidgetItem
        tab.insertRow(tab.rowCount())
        ts = round(ts)
        tab.setItem(tab.rowCount()-1, 0, wI('%.0f' % ts)) #Timestamp
        tab.setItem(tab.rowCount()-1, 1, wI(str(fromts(ts)))) #Date
        tab.setItem(tab.rowCount()-1, 2, wI(fname)) #Filename
        tab.setItem(tab.rowCount()-1, 3, wI(comment)) #Comment
        #[ tab.resizeColumnToContents(c) for c in range(3) ]
        tab.resizeColumnsToContents()
        tab.scrollToBottom()

    def populate_tabFList(self, bp):
        while (self.tabFList.rowCount()): self.tabFList.removeRow(0)
        self.tabFList.blockSignals(True)
        self.leBakPath.setText(bp)
        
        for fname in sorted(os.listdir(bp)):
            if fname.endswith('.sgauto.zip'):
                ts=os.path.getmtime(bp+'/'+fname)
                dt=datetime.datetime.fromtimestamp(int(ts))
                try:
                   with open(os.path.join(bp, fname[:-4]+'.comm.txt')) as comfile: 
                       comment= comfile.read()
                except FileNotFoundError: 
                       comment = ''
                self.add_tabFList(ts, fname, comment)
                self.leTStamp.setText(str(ts))
                self.bksize = self.bksize + os.path.getsize(os.path.join(bp, fname))
        self.tabFList.blockSignals(False)
        self.updateLabels()

    @pyqtSlot()
    def on_bBakPath_clicked(self):
        prevbp=self.SET.get('BakPath', None)
        bp = QtWidgets.QFileDialog.getExistingDirectory(self,'Select backup folder for your files.',str(self.SET['BakPath']))
        if len(bp) > 0:
            self.SET['BakPath']=bp
            self.populate_tabFList(self.SET['BakPath'])
            if bp != prevbp:
                self.force_proc=True
            os.chdir(self.SET['BakPath'])
    
    @pyqtSlot()
    def on_bStart_clicked(self):
        if self.bStart.isChecked():
            self.bStartStyle=self.bStart.styleSheet()
            self.bStart.setStyleSheet('background-color: red')
            self.saveSet(self.inipath)
            self.logst('Monitoring selected files every %d seconds.' % int(self.SET['Interval']/1000))
            self.bStart.setText('Stop')
            self.enableWidgets(False)
            self.timer.start()
        else:
            self.timer.stop()
            self.bStart.setStyleSheet(self.bStartStyle)
            self.bStart.setText('Start')
            self.enableWidgets(True)
            
    @pyqtSlot()
    def on_bClear_clicked(self):
        if self.yesno():
            while (self.lwSGPaths.count()): self.lwSGPaths.takeItem(0)
            self.SET['SvPaths'].clear()

    @pyqtSlot()
    def on_bLoadSet_clicked(self):
        filter='SGAuto Config File (*.sgauto.cfg)'
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select settings file', self.SET['BakPath'],filter)
        if len(path)>0:
            self.loadSet(path)

    @pyqtSlot()
    def on_bSaveSet_clicked(self):
        filter='SGAuto Config File (*.sgauto.cfg)'
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Select settings file', self.SET['BakPath'],filter)
        if len(path) > 0:
            if path.endswith('.sgauto.cfg'):
                self.saveSet(path)
            else:
                self.saveSet(path+'.sgauto.cfg')
    
    @pyqtSlot()
    def on_pbRestore_clicked(self):
        selected = self.tabFList.selectedItems()
        if len(selected) < 4:
            self.logst('Select at least one save.')
            return False
        elif len(selected) > 4:
            self.logst('Too many selected saves. Check only one.')
            return False
        else:
            ts, date, fname, comm = [ v.text() for v in  selected]
            print('Restore', fname)
            os.chdir(self.SET['BakPath'])
            with zipfile.ZipFile(fname) as myzip:
                try:
                    myzip.extractall('tmpzipout')
                except PermissionError:
                    self.logst('Cannot extract files. Maybe other program is blocking it...')
                    return False
                else:
                    self.logst('Extracted backup from {}'.format(fname))
            return True


    @pyqtSlot()
    def on_pbDelete_clicked(self):
        tab = self.tabFList
        selected = tab.selectionModel().selectedRows()
        os.chdir(self.SET['BakPath'])
        try: os.mkdir('.trash')
        except FileExistsError: pass
        for id in [ v.row() for v in  selected]:
            ts = tab.item(id, 0).text()
            fname = tab.item(id, 2).text()
            print('Delete:', id, ts, fname, fname[:-4]+'.comm.txt')
            self.trashsize = self.trashsize + os.path.getsize(fname)
            self.bksize = self.bksize - os.path.getsize(fname)
            self.updateLabels()
            os.rename(fname, '.trash/'+fname)
            try:
                os.rename(fname[:-4]+'.comm.txt', '.trash/'+fname[:-4]+'.comm.txt')
            except FileNotFoundError: pass
            tab.removeRow(id)

    @pyqtSlot()
    def on_pbRollback_clicked(self):
        tab = self.tabFList
        if self.on_pbRestore_clicked():
            selected = tab.selectionModel().selectedRows()
            for row in range(tab.rowCount()-1, selected[0].row(), -1):
                tab.selectRow(row)
                self.on_pbDelete_clicked()

    @QtCore.pyqtSlot(int)
    def on_sbInter_valueChanged(self, interval):
        self.SET['Interval'] = interval*1000
        self.timer.setInterval(self.SET['Interval'])
            
    def closeEvent(self, ev):
        if self.yesno('Program will quit.\nAre you sure?'):
            super(SGAuto, self).closeEvent(ev)
        else:
            ev.ignore()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    myapp = SGAuto()
    myapp.show()
    sys.exit(app.exec())
