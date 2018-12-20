import sys
try:
    sys.path.remove('/opt/ros/kinetic/lib/python2.7/dist-packages')
except:
    pass
import cv2
import time
import numpy as np
sys.path.append("./monitor/")
sys.path.append("./voice/")
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
        QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QProgressBar, QPushButton, QRadioButton,
        QVBoxLayout, QWidget)
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QThread, QObject, pyqtSignal
from wrapper_for import ModuleWrapper, wrapper_args
from wrapper_det import ModuleWrapperDet, wrapper_args_det
from voice import voice_class

class RDGgui(QDialog):

    stop_signal = pyqtSignal()

    def __init__(self, parent=None):
        super(RDGgui, self).__init__(parent)

        self.mode_dict = {
            "infinite forward": (ModuleWrapper, wrapper_args),
            "object detection": (ModuleWrapperDet, wrapper_args_det)
        }

        modeComboBox = QComboBox()
        modeComboBox.addItems(self.mode_dict.keys())
        modeLabel = QLabel("&Mode:")
        modeLabel.setBuddy(modeComboBox)
        modeComboBox.activated[str].connect(self.changeMode)
        startButton = QPushButton("Start", self)
        startButton.clicked.connect(self.startRun)
        self.stopButton = QPushButton("Stop", self)
        self.stopButton.clicked.connect(self.stop_thread)
        #self.stopButton.clicked.connect(self.stopRun)
        monitorCheckBox = QCheckBox("Monitor", self)
        monitorCheckBox.stateChanged.connect(self.checkMonitor)
        voiceCheckBox = QCheckBox("Voice", self)
        voiceCheckBox.stateChanged.connect(self.checkVoice)
        bagCheckBox = QCheckBox("Bagfile", self)
        bagCheckBox.stateChanged.connect(self.checkBag)
        
        self.progLabel = QLabel("Choose a function.")

        self.rgbLabel = QLabel(self)
        self.depLabel = QLabel(self)
        self.mapLabel = QLabel(self)
        self.dirLabel = QLabel(self)

        topLayout = QHBoxLayout()
        topLayout.addWidget(modeLabel)
        topLayout.addWidget(modeComboBox)
        topLayout.addWidget(startButton)
        topLayout.addWidget(self.stopButton)
        topLayout.addWidget(monitorCheckBox)
        topLayout.addWidget(voiceCheckBox)
        topLayout.addWidget(bagCheckBox)

        topLeftLayout = QHBoxLayout()
        topLeftLayout.addWidget(self.rgbLabel)

        topRightLayout = QHBoxLayout()
        topRightLayout.addWidget(self.depLabel)

        botLeftLayout = QHBoxLayout()
        botLeftLayout.addWidget(self.mapLabel)

        botRightLayout = QHBoxLayout()
        botRightLayout.addWidget(self.dirLabel)

        botLayout = QHBoxLayout()
        botLayout.addWidget(self.progLabel)

        mainLayout = QGridLayout()
        mainLayout.addLayout(topLayout, 0, 0, 1, 2)
        mainLayout.addLayout(topLeftLayout, 1, 0)
        mainLayout.addLayout(topRightLayout, 1, 1)
        mainLayout.addLayout(botLeftLayout, 2, 0)
        mainLayout.addLayout(botRightLayout, 2, 1)
        mainLayout.addLayout(botLayout, 3, 0, 1, 2)

        self.setLayout(mainLayout)

        self.run_flag = False
        self.pause_flag = False
        self.monitor_flag = False
        self.voice_flag = False
        self.bag_flag = False

        self.funcName = None


    def changeMode(self, funcName):
        self.funcName = funcName
        self.progLabel.setText(" use " + funcName)

    def startRun(self):
        self.progLabel.setText("start running!")
        try:
            wrapper, arg_func = self.mode_dict[self.funcName]
        except:
            return
        args = arg_func()
        args.bagfile = self.bag_flag
        args.generator = True
        args.voice = False
        args.monitor = self.monitor_flag
        args.time = True
        gen = wrapper(args)
        self.run_flag = True

        self.thread = QThread()
        self.worker = Worker(gen, 
                             self.rgbLabel, self.mapLabel, self.dirLabel, self.depLabel,
                             self.voice_flag)
        self.stop_signal.connect(self.worker.stop)
        self.worker.moveToThread(self.thread)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.started.connect(self.worker.do_work)
        self.thread.finished.connect(self.worker.stop)
        self.stopButton.clicked.connect(self.stop_thread)
        self.thread.start()

        return

    def stopRun(self):
        self.progLabel.setText("stop running!")
        self.run_flag = False

    def stop_thread(self):
        self.stop_signal.emit()  # emit the finished signal on stop


    def setImage(self, label, image):
        height, width, byteValue = image.shape
        byteValue = byteValue * width
		
        qimage = QtGui.QImage(image, width, height, byteValue, QtGui.QImage.Format_RGB888)
        qpix = QtGui.QPixmap(qimage)
        label.setPixmap(qpix)

    def checkMonitor(self, state):
        if state == QtCore.Qt.Checked:
            self.monitor_flag = True
        else:
            self.monitor_flag = False

    def checkVoice(self, state):
        if state == QtCore.Qt.Checked:
            self.voice_flag = True
        else:
            self.voice_flag = False

    def checkBag(self, state):
        if state == QtCore.Qt.Checked:
            self.bag_flag = True
        else:
            self.bag_flag = False

class Worker(QObject):

    finished = pyqtSignal()

    def __init__(self,
                gen, rgbLabel, mapLabel, dirLabel, depLabel,
                use_voice,
                parent=None):
                
        QObject.__init__(self, parent=parent)
        self.continue_run = True

        self.gen = gen
        self.rgbLabel = rgbLabel
        self.mapLabel = mapLabel
        self.dirLabel = dirLabel
        self.depLabel = depLabel

        self.inter = voice_class.VoiceInterface(
            straight_file ='sounds/guitar.wav',
            turnleft_file = 'sounds/left.wav',
            turnright_file = 'sounds/right.wav',
            hardleft_file = 'voice/hardleft.mp3',
            hardright_file = 'voice/hardright.mp3',
            STOP_file = 'voice/STOP.mp3',
            noway_file = 'voice/STOP.mp3',
            wait_file = 'voice/WAIT.mp3'
        )

        self.use_voice = use_voice

    def do_work(self):

        prev_direc = None

        while(self.continue_run):
            
            disp_col, disp_dep, disp_map, disp_sgn, direc = next(self.gen)
            
            if (direc != prev_direc) and self.use_voice:
                self.thread = QThread()
                self.worker = SoundWorker(direc, self.inter)
                self.worker.moveToThread(self.thread)

                self.worker.finished.connect(self.thread.quit)
                self.worker.finished.connect(self.worker.deleteLater)
                self.thread.finished.connect(self.thread.deleteLater)

                self.thread.started.connect(self.worker.do_work)
                self.thread.start()
            prev_direc = direc

            disp_dep = np.asanyarray(disp_dep / np.amax(disp_dep) * 255.0).astype(np.uint8)
            disp_dep = cv2.applyColorMap(disp_dep, cv2.COLORMAP_JET)
            disp_dict = {
                self.rgbLabel: disp_col,
                self.mapLabel: disp_map,
                self.dirLabel: disp_sgn,
                self.depLabel: disp_dep
            }
            for lb, img in disp_dict.items():
                rz_img = cv2.resize(img, (240, 160))
                rgb_img = cv2.cvtColor(rz_img, cv2.COLOR_BGR2RGB)
                self.setImage(lb, rgb_img)

        self.finished.emit()

    def setImage(self, label, image):
        height, width, byteValue = image.shape
        byteValue = byteValue * width
		
        qimage = QtGui.QImage(image, width, height, byteValue, QtGui.QImage.Format_RGB888)
        qpix = QtGui.QPixmap(qimage)
        label.setPixmap(qpix)

    def stop(self):
        self.continue_run = False

class SoundWorker(QObject):

    finished = pyqtSignal()

    def __init__(self,
                direc, inter,
                parent=None):
        QObject.__init__(self, parent=parent)
        self.direc = direc
        self.inter = inter

    def do_work(self):
        self.inter.play_on_edge(self.direc)
        self.finished.emit()

if __name__ == "__main__":
    app = QApplication([])

    gui = RDGgui()
    gui.show()

    sys.exit(app.exec_())