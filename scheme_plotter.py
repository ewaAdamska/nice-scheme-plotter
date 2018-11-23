import numpy as np
import pandas as pd
from database_reader import Database
# import matplotlib
#
# matplotlib.rcParams['text.usetex'] = True
# matplotlib.rcParams['text.latex.unicode'] = True
from collections import OrderedDict
import matplotlib.pyplot as plt

class Level():
    highlighted = False

    def __init__(self, energy, spinValue='', parity=''):
        self.energy = energy
        self.spinValue = spinValue
        self.parity = parity
        self.level_linewidth = 0.5
        self.color = 'black' #RGB codes
        self.linestyle = 'solid'


    def highlight(self, linewidth=4, color='red'):
        self.color= color
        self.highlight_linewidth = linewidth
        self.highlighted = True


    def _linestyle(self):
        if self.linestyle=='dashed':
            return (1, (5, 10))





class Transition():

    def __init__(self, gammaEnergy, from_lvl, to_lvl, gammaEnergy_err=None, intensity=None, instensity_err=None):
        self.gammaEnergy = gammaEnergy
        self.from_lvl = from_lvl
        self.to_lvl = to_lvl
        self.gammaEnergy_err = gammaEnergy_err
        self.intensity = intensity
        self.intensity_err = instensity_err
        
        self.transition_linewidth = 0.001
        self.color = 'black'
        self.linestyle='solid'

    def _linestyle(self):
        if self.linestyle=='dashed':
            return (1, (5, 10))


    def transitionDescription(self):

        transitionDescription = ''
        if self.gammaEnergy:
            transitionDescription += '{}'.format(self.gammaEnergy)
            if self.gammaEnergy_err:
                transitionDescription += '({})'.format(self.gammaEnergy_err)
        if self.intensity:
            transitionDescription += ' {}'.format(self.intensity)
            if self.intensity_err:
                transitionDescription += '({})'.format(self.intensity_err)

        return transitionDescription

############################################################################################################################################################
############################################################################################################################################################



def levelsPackage(database):
    # TODO: maybe its better to omitt this step with dict (???) lets see what will be more useful
    # creating a dictionary {"energy value string" : Level object}
    levels_dictionary = OrderedDict()
    for index, row in database.levels.iterrows():
        levels_dictionary[str(row.lvl_energy)] = Level(energy=row.lvl_energy, spinValue=row.spin, parity=row.parity)
    return levels_dictionary


def transitionsPackage(database):
    # TODO: maybe its better to omitt this step with dict (???) lets see what will be more useful
    # creating a dictionary {"energy value string" : Transition object}
    transitions_dictionary = OrderedDict()
    for index, row in database.transitions.iterrows():
        transitions_dictionary[str(row.g_energy)] = Transition(gammaEnergy=row.g_energy, from_lvl=row.from_lvl, to_lvl=row.to_lvl,\
                                                    intensity=row.I, instensity_err=row.dI, gammaEnergy_err=row.g_energy_err)
    return transitions_dictionary


############################################################################################################################################################
############################################################################################################################################################


class Scheme():
    # These attributes must be Class-Attributes, because when we create many instances of Scheme class,
    # we want them to be identically set up. For example: if we split our decay scheme for many pages
    # we create separated instances of Scheme class for each page. If we decide to change font size
    # or any other scheme's geometry property we want to change it for all Scheme objects.


    # publics:
    figureWidth = 12
    scalingHeightFactor = 0.6 # 0.7 for A4

    # bug! zmiana tych wartosci wszystko psuje
    schemeWidth = 1000
    schemeHeight = 7000

    fontSize = 10
    transition_fontSize = 8

    spinAnnotationWidthFactor = 0.04
    energyAnnotationWidthFactor = 0.04
    levelLineWidthFactor = 0.9

    transtitionsSpacingFactor = 0.021


    # private Class instances:
    _number_of_schemes = 0


    def __init__(self, **kwargs):

        if kwargs is not None:
            for key, value in kwargs.items():
                if key in Scheme.__dict__.keys(): #this is checking if we are not creating new, not necessary atributes
                    setattr(self, key, value)


        # These attributes must be Instance-attributes because they are specified for each Scheme instance
        # object, separately. They are also private attributes, its not good to change them from outside
        # of class code.
        # privs:
        self._spinAnnotationStartingPoint = 0

        self._lastAnnotationPointHeight = 0
        self._annotationBoxHeight = 200  # TODO: this might be scalled automatically with font size

        self.__setPlotParameters()
        self.__prepareCanvas()


        #updating Class Atribute:
        #counting number of Scheme instances
        Scheme._number_of_schemes += 1

    #TODO: add 'set' functions for all important atributes

    def __setPlotParameters(self):

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



        ######## TODO ^^^

        def addLevelLine(energy):
            if Level_object.highlighted == False:
                plt.plot([self._levelLineStartingPoint, self._levelLineEndingPoint], [energy, energy], 'k-', lw=Level_object.level_linewidth, color=Level_object.color, linestyle=Level_object._linestyle())
            else:
                plt.plot([self._levelLineStartingPoint, self._levelLineEndingPoint], [energy, energy], 'k-',
                         lw=Level_object.highlight_linewidth, color=Level_object.color)

        def addSpin(spinValue, parityValue, energy):
            # h is additional height of splitted part of level line
            #TODO: annotation width should be scalled by using self.energyAnnotationStartingPoint etc. (!!!)

            if parityValue=='-' or parityValue=='+':
                spinAnnotationString = r'${}^{}$'.format(spinValue, parityValue)
            else:
                spinAnnotationString = ''

            plt.plot([self._spinAnnotationStartingPoint,self._spinAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._spinAnnotationStartingPoint,self._spinAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._spinAnnotationEndingPoint,self._levelLineStartingPoint], [self.annotationLvl, energy], 'k-', lw=Level_object.level_linewidth)
            plt.text(x=self._spinAnnotationTextPoint, y=(self.annotationLvl)+0.01*self.schemeHeight, s=spinAnnotationString, size=self.fontSize, horizontalalignment='center')


        def addEnergy(energyValue, energy):
            # h is additional height of splitted part of level line
            plt.plot([self._energyAnnotationStartingPoint, self._energyAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._levelLineEndingPoint,self._energyAnnotationStartingPoint], [energy, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.text(x=self._energyAnnotationTextPoint, y=self.annotationLvl+0.01*self.schemeHeight, s=energyValue, size=self.fontSize, horizontalalignment='center')

        addLevelLine(energy=Level_object.energy)
        addSpin(spinValue=Level_object.spinValue, parityValue=Level_object.parity, energy=Level_object.energy)
        addEnergy(energyValue=str(Level_object.energy), energy=Level_object.energy)


    def addTransition(self, Transition_object):



        plt.arrow(x=self._nextArrowPoint_x , y=Transition_object.from_lvl, dx=0, dy=-1*Transition_object.gammaEnergy,\
                  head_width=0.005*self._levelLineWidth_value, head_length=0.1*self._levelLineWidth_value,
                    length_includes_head=True, facecolor=Transition_object.color, color=Transition_object.color,\
                    width=Transition_object.transition_linewidth, alpha=1, linestyle=Transition_object._linestyle())

        # TODO: maybe its better to use ax.annotate
        # plt.annotate("Annotation",
        #             xy=(0, 1), xycoords='data',
        #             xytext=(1, 2), textcoords='offset points',
        #             )
        #



        box = dict(boxstyle='square', facecolor='white', color='white', alpha=1, pad=0) #udalo sie zmienic rozmiar white box za pomoca parametru pad
        plt.text(x=self._nextArrowPoint_x, y=Transition_object.from_lvl+self.schemeHeight*0.01, s=Transition_object.transitionDescription(),\
                 fontsize = self.transition_fontSize, rotation=60, horizontalalignment='left', verticalalignment='bottom',\
                 bbox=box)

        self._nextArrowPoint_x -= self._transitionsSpacingValue


    def addLevelsPackage(self, levelsPackage):
        for key in levelsPackage.keys():
            self.addLevel(levelsPackage[key])

    def addTransitionsPackage(self, transitionsPackage):
        # -1 means reversed sorting
        for key in [t[0] for t in sorted(transitionsPackage.items(), key=lambda x: (x[1].from_lvl, -1 * x[1].to_lvl))]:
            self.addTransition(transitionsPackage[key])

    def addNucleiName(self, nucleiName=r'$^{63}$Ni'):
        plt.text(0.48, 0.05, nucleiName, fontsize=20, transform=plt.gcf().transFigure)

    def save(self, fileName=None):
        if fileName:
            pass
        else:
            fileName = 'scheme_part_{}.svg'.format(self._number_of_schemes)

        print('Scheme saved to the file {}'.format(fileName))
        plt.savefig(fileName)

    def show(self):
        plt.show()




scheme = Scheme()


levels = levelsPackage(database=Database(lvlFileName='DATABASE_LVLS', transitionsFileName='DATABASE_TRANS'))
transitions = transitionsPackage(database=Database(lvlFileName='DATABASE_LVLS', transitionsFileName='DATABASE_TRANS'))

levels['4055.0'].highlight(linewidth=2, color='red')
levels['1324.01'].linestyle='dashed'

transitions['3900.0'].linestyle = 'dashed'
transitions['2379.2'].color='blue'
transitions['805.8'].color='green'
transitions['805.8'].transition_linewidth=2


scheme.addLevelsPackage(levelsPackage = levels)
scheme.addTransitionsPackage(transitionsPackage = transitions)

scheme.addNucleiName(r'$^{63}$Ni')
scheme.show()


# scheme.save()
#
# scheme_2 = Scheme()
# scheme_2.addLevelsPackage(levelsPackage = levels)
# scheme_2.addTransitionsPackage(transitionsPackage = transitions)
# scheme_2.show()
# scheme_2.save()