import numpy as np
import pandas as pd
from database_reader import Database

dat = Database()
# print(dat.transitions['g_energy'])

import matplotlib.pyplot as plt

class Level():
    boxHeight = 200
    def __init__(self, energy, spinValue='', parity=''):
        self.energy = energy
        self.spinValue = spinValue
        self.parity = parity
        self.level_line_width = 1



class Scheme():

    # publics:
    figureWidth = 12
    scalingHeightFactor = 0.6 # 0.7 for A4

    schemeWidth = 1000
    schemeHeight = 7000

    fontSize = 14

    spinAnnotationWidthFactor = 0.1
    energyAnnotationWidthFactor = 0.1

    _spinAnnotationStartingPoint = 0

    lvlAnnotationSeparationAdditionalBox = 10

    #privs:

    _lastAnnotationPointHeight = 0

    def __init__(self, *args, **kwargs):

        self._spinAnnotationStartingPoint = self.schemeWidth * self.spinAnnotationWidthFactor
        self._spinAnnotationEndingPoint = self.schemeWidth*self.spinAnnotationWidthFactor
        self._spinAnnotationWidth_value = self._spinAnnotationEndingPoint - self._spinAnnotationStartingPoint

        self._energyAnnotationStartingPoint = self.schemeWidth * (1 - self.energyAnnotationWidthFactor)
        self._energyAnnotationEndingPoint = self.schemeWidth


        self.__prepareCanvas()


    def __prepareCanvas(self):
        fig, ax = plt.subplots(figsize=(self.figureWidth, self.scalingHeightFactor * self.figureWidth))
        plt.subplots_adjust(left=0.01, right=0.99)

        plt.axis('off')
        plt.ylim(0, self.schemeHeight)
        plt.xlim(0, self.schemeWidth)


    def addLevel(self, Level_object):
        #### TODO: this part can be improved

        self.annotationLvl = Level_object.energy
        while self.annotationLvl < self._lastAnnotationPointHeight:
            self.annotationLvl += Level_object.boxHeight

        self._lastAnnotationPointHeight = self.annotationLvl + Level_object.boxHeight

        ########

        def addLevelLine(energy):
            plt.plot([100, 900], [energy, energy], 'k-', lw=Level_object.level_line_width)

        def addSpin(spinValue, energy, h):
            # h is additional height of splitted part of level line


            plt.plot([25,75], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_line_width)
            plt.plot([75,100], [self.annotationLvl, energy], 'k-', lw=Level_object.level_line_width)
            plt.text(x=40, y=(self.annotationLvl)+10, s=spinValue, size=self.fontSize)

        def addEnergy(energyValue, energy, h):
            # h is additional height of splitted part of level line
            plt.plot([925,1000], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_line_width)
            plt.plot([900,925], [energy, self.annotationLvl], 'k-', lw=Level_object.level_line_width)
            plt.text(x=930, y=self.annotationLvl+10, s=energyValue, size=self.fontSize)

        addLevelLine(energy=Level_object.energy)
        addSpin(spinValue=Level_object.spinValue, energy=Level_object.energy, h=Level_object.boxHeight)
        addEnergy(energyValue=str(Level_object.energy), energy=Level_object.energy, h=Level_object.boxHeight)

        # print(self.annotationLvl)


scheme = Scheme()


level_155 = Level(energy=155, spinValue='1/2')
level_157 = Level(energy=160, spinValue='1/2')
level_158 = Level(energy=190, spinValue='1/2')
level_250 = Level(energy=2500, spinValue='3/2')

scheme.addLevel(level_155)
scheme.addLevel(level_157)
scheme.addLevel(level_158)
scheme.addLevel(level_250)



# plt.xlabel('Ni', fontsize=30)
#
# addLevelLine(energy=100)
# addSpin(spinValue='1/2', energy=100, h=0)
# addEnergy(energyValue='100.5', energy=100, h=0)
#
# addLevelLine(energy=150)
# addSpin(spinValue='1/2', energy=150, h=150)
# addEnergy(energyValue='150.5', energy=150, h=20)
#
# addLevelLine(energy=170)
# addSpin(spinValue='1/2', energy=170, h=150)
# addEnergy(energyValue='150.5', energy=170, h=40)

plt.text(0.5, 0.05, 'Ni-63', fontsize=14, transform=plt.gcf().transFigure)

plt.show()