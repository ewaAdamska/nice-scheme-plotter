import numpy as np
import pandas as pd
from database_reader import Database
# import matplotlib
#
# matplotlib.rcParams['text.usetex'] = True
# matplotlib.rcParams['text.latex.unicode'] = True

import matplotlib.pyplot as plt

class Level():
    highlighted = False

    def __init__(self, energy, spinValue='', parity=''):
        self.energy = energy
        self.spinValue = spinValue
        self.parity = parity
        self.level_linewidth = 0.5
        self.color = 'black' #RGB codes

    def highlight(self, linewidth=4, color='red'):
        self.color= color
        self.highlight_linewidth = linewidth
        self.highlighted = True

class Transition():

    def __init__(self, gammaEnergy, from_lvl, to_lvl, gammaEnergy_err=None, intensity=None, instensity_err=None):
        self.gammaEnergy = gammaEnergy
        self.from_lvl = from_lvl
        self.to_lvl = to_lvl
        self.gammaEnergy_err = gammaEnergy_err
        self.intensity = intensity
        self.intensity_err = instensity_err
        
        self.transition_linewidth = 1
        self.color = 'black'


class Scheme():

    # publics:
    figureWidth = 12
    scalingHeightFactor = 0.6 # 0.7 for A4

    schemeWidth = 1000
    schemeHeight = 7000

    fontSize = 10

    spinAnnotationWidthFactor = 0.04
    energyAnnotationWidthFactor = 0.04
    levelLineWidthFactor = 0.9

    transtitionsSpacingFactor = 0.02

    #privs:
    _spinAnnotationStartingPoint = 0

    _lastAnnotationPointHeight = 0
    _annotationBoxHeight = 200          #TODO: this might be scalled automatically with font size



    def __init__(self, *args, **kwargs):

        self._spinAnnotationStartingPoint = 0
        self._spinAnnotationEndingPoint = self.schemeWidth*self.spinAnnotationWidthFactor
        self._spinAnnotationWidth_value = self._spinAnnotationEndingPoint - self._spinAnnotationStartingPoint
        self._spinAnnotationTextPoint = self._spinAnnotationWidth_value / 2


        self._energyAnnotationStartingPoint = self.schemeWidth * (1 - self.energyAnnotationWidthFactor)
        self._energyAnnotationEndingPoint = self.schemeWidth
        self._energyAnnotationWidth_value = self._energyAnnotationEndingPoint - self._energyAnnotationStartingPoint
        self._energyAnnotationTextPoint = self.schemeWidth - self._energyAnnotationWidth_value / 2


        self._levelLineStartingPoint = 0.5*self.schemeWidth*(1 - self.levelLineWidthFactor)
        self._levelLineEndingPoint = self.schemeWidth*(1-0.5*(1 - self.levelLineWidthFactor))
        self._levelLineWidth_value = self._levelLineEndingPoint - self._levelLineStartingPoint

        self._nextArrowPoint_x = self._levelLineEndingPoint-0.01*self.schemeWidth
        self._transitionsSpacingValue = self._levelLineWidth_value * self.transtitionsSpacingFactor


        self.__prepareCanvas()


    def __prepareCanvas(self):
        fig, ax = plt.subplots(figsize=(self.figureWidth, self.scalingHeightFactor * self.figureWidth))
        plt.subplots_adjust(left=0.01, right=0.99)
        plt.rcParams.update({'font.size': self.fontSize}) # setting up font for all labels


        plt.axis('off')
        plt.ylim(-10, self.schemeHeight)
        plt.xlim(0, self.schemeWidth)


    def addLevel(self, Level_object):
        #### TODO: this part can be improved

        self.annotationLvl = Level_object.energy
        while self.annotationLvl < self._lastAnnotationPointHeight:
            self.annotationLvl += self._annotationBoxHeight

        self._lastAnnotationPointHeight = self.annotationLvl + self._annotationBoxHeight

        ########

        def addLevelLine(energy):
            if Level_object.highlighted == False:
                plt.plot([self._levelLineStartingPoint, self._levelLineEndingPoint], [energy, energy], 'k-', lw=Level_object.level_linewidth, color=Level_object.color)
            else:
                plt.plot([self._levelLineStartingPoint, self._levelLineEndingPoint], [energy, energy], 'k-',
                         lw=Level_object.highlight_linewidth, color=Level_object.color)
        def addSpin(spinValue, energy, h):
            # h is additional height of splitted part of level line
            #TODO: annotation width should be scalled by using self.energyAnnotationStartingPoint etc. (!!!)

            plt.plot([self._spinAnnotationStartingPoint,self._spinAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._spinAnnotationStartingPoint,self._spinAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._spinAnnotationEndingPoint,self._levelLineStartingPoint], [self.annotationLvl, energy], 'k-', lw=Level_object.level_linewidth)
            plt.text(x=self._spinAnnotationTextPoint, y=(self.annotationLvl)+0.01*self.schemeHeight, s=spinValue, size=self.fontSize, horizontalalignment='center')

        def addEnergy(energyValue, energy, h):
            # h is additional height of splitted part of level line
            plt.plot([self._energyAnnotationStartingPoint, self._energyAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._levelLineEndingPoint,self._energyAnnotationStartingPoint], [energy, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.text(x=self._energyAnnotationTextPoint, y=self.annotationLvl+0.01*self.schemeHeight, s=energyValue, size=self.fontSize, horizontalalignment='center')

        addLevelLine(energy=Level_object.energy)
        addSpin(spinValue=Level_object.spinValue, energy=Level_object.energy, h=self._annotationBoxHeight)
        addEnergy(energyValue=str(Level_object.energy), energy=Level_object.energy, h=self._annotationBoxHeight)

        # print(self.annotationLvl)

    def addTransition(self, Transition_object):
        plt.arrow(x=self._nextArrowPoint_x , y=Transition_object.from_lvl, dx=0, dy=-1*Transition_object.gammaEnergy,\
                  head_width=0.005*self._levelLineWidth_value, head_length=0.1*self._levelLineWidth_value,
                    length_includes_head=True)


        box = dict(boxstyle='square', facecolor='white', color='white', alpha=1)
        plt.text(x=self._nextArrowPoint_x, y=Transition_object.from_lvl+self.schemeHeight*0.01, s=str(Transition_object.gammaEnergy),\
                 fontsize = 10, rotation=60, horizontalalignment='center', verticalalignment='bottom',\
                 bbox=box)


        self._nextArrowPoint_x -= self._transitionsSpacingValue





    def plot(self):
        # temp solution

        plt.text(0.48, 0.05, r'$^{63}$Ni', fontsize=20, transform=plt.gcf().transFigure)
        plt.savefig('scheme.svg')
        plt.show()



scheme = Scheme()


data = Database(lvlFileName='DATABASE_LVLS', transitionsFileName='DATABASE_TRANS')
print(data.levels)

#TODO: maybe its better to omitt this step with dict (???) lets see what will be more useful
#creating a dictionary {"energy value string" : Level object}
levels_dictionary = {}
for index, row in data.levels.iterrows():
    if row.lvl_energy == 4331.00:
        levels_dictionary['4331.00'] = Level(energy=row.lvl_energy, spinValue=row.spin, parity=row.parity)
        levels_dictionary['4331.00'].highlight(linewidth=2)

    else:
        levels_dictionary[str(row.lvl_energy)] = Level(energy=row.lvl_energy, spinValue=row.spin, parity=row.parity)



for key in levels_dictionary.keys():
    scheme.addLevel(levels_dictionary[key])


########### Transitions
trans_1 = Transition(gammaEnergy=1001.1, from_lvl=1001.1, to_lvl=0)
trans_2 = Transition(gammaEnergy=845.1, from_lvl=1001.1, to_lvl=155.57)
trans_3 = Transition(gammaEnergy=483.1, from_lvl=1001.1, to_lvl=517.6)


scheme.addTransition(trans_3)
scheme.addTransition(trans_2)
scheme.addTransition(trans_1)

scheme.plot()

